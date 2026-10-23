from flask import Flask, render_template, request, redirect, session, url_for, Response, stream_with_context
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
import bcrypt
import os
import sys
import shutil
import tempfile
from dotenv import load_dotenv

load_dotenv()
from datetime import datetime
import numpy as np
import base64
from PIL import Image
import io
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import random
import requests
import certifi
import re
import secrets
from functools import wraps
from bson import ObjectId
from scipy.spatial.distance import cosine

# Add backend to path so we can import mongo_features
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "voting_system_crypto", "backend"))

from mongo_features import (
    store_otp_session,
    verify_otp_session,
    record_login_attempt,
    is_account_locked,
    audit,
    store_file_gridfs,
    retrieve_file_gridfs,
    list_voter_files_gridfs,
    transactional_approve_official,
)

try:
    import pytesseract
    from pytesseract import TesseractNotFoundError
except ImportError:
    pytesseract = None
    TesseractNotFoundError = Exception


def _configure_tesseract():
    """Point pytesseract at tesseract.exe. Windows installers often skip PATH."""
    if pytesseract is None:
        return None

    candidates = [
        os.environ.get("TESSERACT_CMD"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
        shutil.which("tesseract"),
    ]
    for cmd in candidates:
        if not cmd:
            continue
        cmd = os.path.abspath(cmd)
        if os.path.isfile(cmd):
            tess_dir = os.path.dirname(cmd)
            os.environ["PATH"] = tess_dir + os.pathsep + os.environ.get("PATH", "")
            pytesseract.pytesseract.tesseract_cmd = cmd
            tessdata = os.path.join(tess_dir, "tessdata")
            if os.path.isdir(tessdata):
                os.environ["TESSDATA_PREFIX"] = tessdata
            return cmd
    return None


TESSERACT_EXE = _configure_tesseract()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("FLASK_SECRET_KEY is not set. Add it to your .env file.")
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB uploads


@app.errorhandler(413)
def request_entity_too_large(_error):
    return (
        "Upload is too large. Please use a smaller Aadhaar image and recapture face photo, then try again.",
        413,
    )

# ---------------- CONFIG ----------------
MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    raise RuntimeError("MONGO_URI is not set. Add it to your .env file.")
ELECTION_API_URL = os.environ.get("ELECTION_API_URL", "http://localhost:5000")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")

# ---------------- DATABASE ----------------
client = MongoClient(
    MONGO_URI,
    tls=True,
    tlsCAFile=certifi.where(),
    serverSelectionTimeoutMS=8000,
    connectTimeoutMS=8000,
)
db = client["evoting_db"]
users = db["users"]  # legacy mixed collection (read-only fallback)
voter_users = db["voter_users"]
admin_users = db["admin_users"]
official_auth_users = db["official_auth_users"]
officials = db["officials"]
official_requests = db["official_requests"]
mongo_ok = True
mongo_error = None


def ensure_mongo_connection() -> bool:
    """Ping MongoDB and keep connection status fresh for each request."""
    global mongo_ok, mongo_error
    try:
        client.admin.command("ping")
        mongo_ok = True
        mongo_error = None
        return True
    except ServerSelectionTimeoutError as e:
        mongo_ok = False
        mongo_error = str(e)
        return False
    except Exception as e:
        mongo_ok = False
        mongo_error = str(e)
        return False


ensure_mongo_connection()

# ---------------- UTILITIES ----------------

def normalize_device_fingerprint(user_agent: str) -> str:
    """Create a stable device fingerprint that survives browser version updates."""
    ua = (user_agent or "").strip().lower()
    if not ua:
        return "unknown|unknown|unknown"

    if "windows" in ua:
        platform = "windows"
    elif "android" in ua:
        platform = "android"
    elif "iphone" in ua or "ipad" in ua or "ios" in ua:
        platform = "ios"
    elif "mac os" in ua or "macintosh" in ua:
        platform = "macos"
    elif "linux" in ua:
        platform = "linux"
    else:
        platform = "other"

    # Order matters: Chromium-based browsers include "safari" too.
    if "edg/" in ua or "edge/" in ua:
        browser = "edge"
    elif "opr/" in ua or "opera" in ua:
        browser = "opera"
    elif "chrome/" in ua and "chromium" not in ua:
        browser = "chrome"
    elif "firefox/" in ua:
        browser = "firefox"
    elif "safari/" in ua:
        browser = "safari"
    elif "chromium" in ua:
        browser = "chromium"
    else:
        browser = "other"

    device_class = "mobile" if any(token in ua for token in ("mobile", "android", "iphone", "ipad")) else "desktop"

    return f"{platform}|{browser}|{device_class}"

def validate_aadhaar(aadhaar):
    return aadhaar.isdigit() and len(aadhaar) == 12


def require_role(required_role: str):
    """Simple session-based RBAC for admin/official dashboards."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get("authenticated"):
                if required_role == "admin":
                    return redirect(url_for("admin_login"))
                if required_role == "official":
                    return redirect(url_for("official_login"))
                return redirect(url_for("login"))

            role = session.get("role", "voter")
            if role != required_role:
                return redirect(url_for("home"))

            return fn(*args, **kwargs)

        return wrapper

    return decorator


def generate_official_key_share() -> str:
    """Generate a random key share token for official profile and threshold simulation."""
    return secrets.token_hex(32)


def find_existing_account_by_aadhaar(aadhaar: str):
    """Find existing account in separated collections (legacy fallback included)."""
    return (
        voter_users.find_one({"aadhaar": aadhaar})
        or admin_users.find_one({"aadhaar": aadhaar})
        or official_auth_users.find_one({"aadhaar": aadhaar})
        or users.find_one({"aadhaar": aadhaar})
    )


def get_voter_account(aadhaar: str):
    """Resolve voter account from new collection with fallback to legacy users."""
    account = voter_users.find_one({"aadhaar": aadhaar})
    if account:
        return account

    legacy = users.find_one({"aadhaar": aadhaar})
    if legacy and legacy.get("role", "voter") == "voter":
        return legacy
    return None


def get_admin_account(aadhaar: str):
    """Resolve admin account from new collection with fallback to legacy users."""
    account = admin_users.find_one({"aadhaar": aadhaar})
    if account:
        return account

    legacy = users.find_one({"aadhaar": aadhaar, "role": "admin"})
    return legacy


def get_official_auth_account(aadhaar: str):
    """Resolve official auth account from new collection with fallback to legacy users."""
    account = official_auth_users.find_one({"aadhaar": aadhaar})
    if account:
        return account

    legacy = users.find_one({"aadhaar": aadhaar, "role": "official"})
    return legacy

def is_eligible(dob):
    birth_date = datetime.strptime(dob, "%Y-%m-%d")
    age = (datetime.today() - birth_date).days // 365
    return age >= 18

def extract_face_encoding(base64_image):
    """Extract a Facenet embedding with DeepFace (no dlib / face_recognition)."""
    if not base64_image:
        return None

    payload = base64_image.strip()
    if "," in payload:
        payload = payload.split(",", 1)[1]
    payload += "=" * (-len(payload) % 4)

    try:
        image_data = base64.b64decode(payload)
    except Exception:
        return None

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(image_data)
            tmp_path = tmp.name

        from deepface import DeepFace

        embedding_objs = DeepFace.represent(
            img_path=tmp_path,
            model_name="Facenet",
            enforce_detection=True,
            detector_backend="opencv",
        )
        if not embedding_objs:
            return None
        return embedding_objs[0]["embedding"]
    except Exception:
        return None
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

def compare_faces(stored, captured):
    """Compare Facenet embeddings with cosine distance."""
    stored = np.array(stored, dtype=float)
    captured = np.array(captured, dtype=float)
    if stored.size == 0 or captured.size == 0 or stored.shape != captured.shape:
        return False
    return cosine(stored, captured) < 0.5

def send_otp_email(receiver_email, otp):
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        raise RuntimeError("SENDER_EMAIL and SENDER_PASSWORD must be set in the .env file.")

    msg = MIMEMultipart()
    msg["Subject"] = "EVoting Login OTP"
    msg["From"] = SENDER_EMAIL
    msg["To"] = receiver_email
    msg.attach(MIMEText(f"Your OTP for EVoting login is: {otp}\n\nThis OTP is valid for 10 minutes.", "plain"))

    server = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)
    try:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
    except smtplib.SMTPAuthenticationError as e:
        raise RuntimeError("Email authentication failed. Check SENDER_EMAIL and the Gmail app password.") from e
    finally:
        try:
            server.quit()
        except Exception:
            pass


def _allowed_aadhaar_upload(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in {"png", "jpg", "jpeg", "webp"}


def _normalize_dob_str(dob_str: str) -> str | None:
    if not dob_str:
        return None
    s = dob_str.strip().replace("-", "/")
    parts = [p for p in s.split("/") if p]
    if len(parts) != 3:
        return None
    # yyyy/mm/dd
    if len(parts[0]) == 4:
        yyyy, mm, dd = parts[0], parts[1], parts[2]
    else:
        # dd/mm/yyyy
        dd, mm, yyyy = parts[0], parts[1], parts[2]
    if len(yyyy) != 4:
        return None
    return f"{yyyy}-{mm.zfill(2)}-{dd.zfill(2)}"


def extract_aadhaar_details_from_image(file_storage):
    """
    Extract Aadhaar Number + DOB from uploaded Aadhaar card image using OCR.

    Requirements:
    - `pytesseract` installed
    - Tesseract OCR installed on the machine
    """
    if pytesseract is None:
        raise RuntimeError("OCR not available. Install pytesseract in the same Python environment.")

    exe = TESSERACT_EXE or _configure_tesseract()
    if not exe:
        raise RuntimeError(
            "Tesseract OCR is installed but Python cannot find tesseract.exe. "
            "Restart the Flask app after installing, or set TESSERACT_CMD to the full path."
        )

    raw = file_storage.read()
    if not raw:
        raise ValueError("Empty file upload.")

    img = Image.open(io.BytesIO(raw)).convert("RGB")
    # Light preprocessing: grayscale helps OCR on many cards
    img = img.convert("L")

    try:
        text = pytesseract.image_to_string(img)
    except TesseractNotFoundError as e:
        raise RuntimeError(
            f"Tesseract OCR not found. Expected at: {pytesseract.pytesseract.tesseract_cmd}"
        ) from e

    # Aadhaar number patterns: "1234 5678 9012" or "123456789012"
    aadhaar_match = re.search(r"\b(\d{4}\s\d{4}\s\d{4})\b", text)
    if aadhaar_match:
        aadhaar_num = aadhaar_match.group(1).replace(" ", "")
    else:
        aadhaar_match = re.search(r"\b(\d{12})\b", text)
        aadhaar_num = aadhaar_match.group(1) if aadhaar_match else None

    # DOB patterns: "DOB: dd/mm/yyyy" or "dd-mm-yyyy" or ISO
    dob_match = re.search(r"\bDOB[:\s]*([0-3]?\d[/-][01]?\d[/-]\d{4})\b", text, re.IGNORECASE)
    dob = _normalize_dob_str(dob_match.group(1)) if dob_match else None

    # Fallback: any standalone dd/mm/yyyy or dd-mm-yyyy (handles cards where date is shown without "DOB")
    if dob is None:
        generic_date = re.search(r"\b([0-3]?\d[/-][01]?\d[/-]\d{4})\b", text)
        if generic_date:
            dob = _normalize_dob_str(generic_date.group(1))

    # If only Year of Birth is present, capture it for partial match
    yob_match = re.search(r"\bYear\s*of\s*Birth[:\s]*([12]\d{3})\b", text, re.IGNORECASE)
    yob = yob_match.group(1) if yob_match else None

    return {
        "raw_text": text,
        "aadhaar": aadhaar_num,
        "dob": dob,
        "yob": yob,
    }

# ---------------- ROUTES ----------------

@app.route("/")
def home():
    return render_template("home.html")

# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        if not ensure_mongo_connection():
            return (
                "MongoDB connection failed. Fix MONGO_URI / TLS certificates, then restart the server.\n\n"
                f"Details: {mongo_error}",
                500,
            )

        aadhaar = request.form["aadhaar"]
        name = request.form["name"]
        dob = request.form["dob"]
        gender = request.form["gender"]
        mobile = request.form["mobile"]
        email = request.form["email"]
        address = request.form["address"]
        password = request.form["password"]
        face_image = request.form["face_image"]

        if not validate_aadhaar(aadhaar):
            return render_template("register.html", error="Invalid Aadhaar. It must be a 12-digit number.")

        if not is_eligible(dob):
            return render_template("register.html", error="You must be 18+ to register.")

        if find_existing_account_by_aadhaar(aadhaar):
            return render_template("register.html", error="User already registered with this Aadhaar.")

        face_encoding = extract_face_encoding(face_image)
        if face_encoding is None:
            return render_template("register.html", error="No face detected. Please capture a clearer image.")

        hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

        # Task 8: store face photo in GridFS
        face_grid_id = None
        try:
            face_bytes = base64.b64decode(
                face_image.split(",", 1)[1] if "," in face_image else face_image
            )
            face_grid_id = store_file_gridfs(
                db, face_bytes,
                filename=f"face_{aadhaar}.jpg",
                metadata={"aadhaar": aadhaar, "type": "registration_face"}
            )
        except Exception:
            pass  # GridFS is supplementary; don't block registration

        voter_users.insert_one({
            "aadhaar": aadhaar,
            "name": name,
            "dob": dob,
            "gender": gender,
            "mobile": mobile,
            "email": email,
            "address": address,
            "role": "voter",
            "password": hashed_password,
            "face_encoding": face_encoding.tolist() if hasattr(face_encoding, 'tolist') else face_encoding,
            "face_grid_id": face_grid_id,   # Task 8: GridFS reference
            "registered_at": datetime.utcnow(),
        })

        # Task 7: audit registration
        audit(db, "voter_registered", aadhaar=aadhaar, success=True)

        # Also register the voter with the post-quantum election server
        private_key = None
        try:
            api_payload = {
                "voter_id": aadhaar,
                "password": password,
                "aadhaar": {
                    "name": name,
                    "dob": dob,
                    "address": address,
                },
                "face_image": face_image,
            }
            resp = requests.post(f"{ELECTION_API_URL}/register", json=api_payload, timeout=10)
            if resp.status_code == 200:
                reg_result = resp.json()
                private_key = reg_result.get("private_key")
            else:
                print(f"[Register] Backend returned {resp.status_code}: {resp.text}")
        except Exception as e:
            print(f"[Register] Backend call failed: {e}")
            private_key = None

        return render_template("register_success.html", name=name, private_key=private_key)

    return render_template("register.html", error=None)

# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        if not ensure_mongo_connection():
            return (
                "MongoDB connection failed. Fix MONGO_URI / TLS certificates, then restart the server.\n\n"
                f"Details: {mongo_error}",
                500,
            )

        aadhaar = request.form["aadhaar"]
        entered_dob = request.form.get("dob", "").strip()
        password = request.form["password"]
        aadhaar_card = request.files.get("aadhaar_card")

        if not validate_aadhaar(aadhaar):
            return render_template("login.html", error="Invalid Aadhaar. It must be a 12-digit number.")

        if not entered_dob:
            return render_template("login.html", error="DOB is required.")

        if not aadhaar_card or not aadhaar_card.filename:
            return render_template("login.html", error="Please upload your Aadhaar card image.")

        if not _allowed_aadhaar_upload(aadhaar_card.filename):
            return render_template("login.html", error="Unsupported Aadhaar upload. Please upload PNG/JPG/JPEG/WEBP.")

        # Task 5: lockout after 5 failed attempts in 15-min window
        if is_account_locked(db, aadhaar):
            audit(db, "login_locked", aadhaar=aadhaar, success=False)
            return render_template("login.html", error="Account temporarily locked due to too many failed attempts. Try again in 15 minutes.")

        user = get_voter_account(aadhaar)
        if not user:
            record_login_attempt(db, aadhaar, success=False)
            return render_template("login.html", error="User not found. Please register first.")

        # Ensure entered DOB matches the stored DOB from registration
        stored_dob = (user.get("dob") or "").strip()
        if stored_dob and stored_dob != entered_dob:
            return render_template("login.html", error="DOB does not match the registered record.")

        if not bcrypt.checkpw(password.encode(), user["password"]):
            record_login_attempt(db, aadhaar, success=False)
            audit(db, "login_attempt", aadhaar=aadhaar, success=False, details={"reason": "wrong_password"})
            return render_template("login.html", error="Wrong password.")

        # OCR Aadhaar card and verify Aadhaar + DOB match the uploaded card
        try:
            # Task 8: store Aadhaar card image in GridFS before reading it
            aadhaar_card.seek(0)
            card_bytes = aadhaar_card.read()
            store_file_gridfs(
                db, card_bytes,
                filename=f"aadhaar_{aadhaar}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.jpg",
                metadata={"aadhaar": aadhaar, "type": "login_aadhaar_card"}
            )
            aadhaar_card.seek(0)  # rewind for OCR
            ocr = extract_aadhaar_details_from_image(aadhaar_card)
        except Exception as e:
            return render_template("login.html", error=f"Aadhaar OCR failed: {str(e)}")

        if not ocr.get("aadhaar"):
            return render_template("login.html", error="Could not read Aadhaar number from the uploaded card. Please upload a clearer image.")

        if ocr["aadhaar"] != aadhaar:
            return render_template("login.html", error="Aadhaar number does not match the uploaded Aadhaar card.")

        if ocr.get("dob"):
            ocr_dob = (ocr["dob"] or "").strip()
            if ocr_dob and ocr_dob != entered_dob:
                return render_template(
                    "login.html",
                    error=f"DOB does not match the uploaded Aadhaar card. (Card: {ocr_dob}, Entered: {entered_dob})",
                )
        elif ocr.get("yob"):
            if entered_dob[:4] != ocr["yob"]:
                return render_template("login.html", error="Year of birth does not match the uploaded Aadhaar card.")
        # If OCR could not extract DOB, rely on the stored registration DOB check above.

        # Remember which user is in the MFA flow
        session["aadhaar"] = aadhaar
        session["face_verified"] = False

        # Next step: face verification (requested order: Aadhaar card -> Face -> OTP)
        return render_template("face_verify.html", aadhaar=aadhaar, error=None, action_url="/verify_face_login")

    return render_template("login.html", error=None)


@app.route("/verify_face_login", methods=["POST"])
def verify_face_login():

    if not ensure_mongo_connection():
        return (
            "MongoDB connection failed. Fix MONGO_URI / TLS certificates, then restart the server.\n\n"
            f"Details: {mongo_error}",
            500,
        )

    aadhaar = request.form["aadhaar"]
    face_image = request.form.get("face_image", "")

    if not face_image:
        return render_template("face_verify.html", aadhaar=aadhaar, error="Face image missing. Please capture your face and try again.", action_url="/verify_face_login")

    user = get_voter_account(aadhaar)
    if not user:
        return render_template("login.html", error="User not found. Please register first.")

    captured_encoding = extract_face_encoding(face_image)

    if captured_encoding is None:
        return render_template("face_verify.html", aadhaar=aadhaar, error="Face not detected. Please capture again.", action_url="/verify_face_login")

    if not compare_faces(user["face_encoding"], captured_encoding):
        audit(db, "face_verify_failure", aadhaar=aadhaar, success=False)
        return render_template("face_verify.html", aadhaar=aadhaar, error="Face mismatch. Please try again in good lighting.", action_url="/verify_face_login")

    # Face verified — store OTP in TTL collection (Task 5: hashed, auto-expires in 5 min)
    otp = str(random.randint(100000, 999999))
    store_otp_session(db, aadhaar, otp)
    # Audit: face verification success (Task 7)
    audit(db, "face_verify_success", aadhaar=aadhaar, success=True)
    try:
        send_otp_email(user["email"], otp)
    except Exception as e:
        return render_template(
            "face_verify.html",
            aadhaar=aadhaar,
            error=f"Failed to send OTP email: {str(e)}",
            action_url="/verify_face_login",
        )

    session["aadhaar"] = aadhaar
    session["face_verified"] = True

    return render_template("verify_otp.html", aadhaar=aadhaar, error=None)

# ---------------- OTP ----------------

@app.route("/verify_otp", methods=["POST"])
def verify_otp():

    if not ensure_mongo_connection():
        return (
            "MongoDB connection failed. Fix MONGO_URI / TLS certificates, then restart the server.\n\n"
            f"Details: {mongo_error}",
            500,
        )

    aadhaar = request.form["aadhaar"]
    entered_otp = request.form["otp"]

    # Task 5: verify against TTL-backed hashed OTP session
    ok, reason = verify_otp_session(db, aadhaar, entered_otp)
    if not ok:
        audit(db, "otp_failure", aadhaar=aadhaar, success=False, details={"reason": reason})
        return render_template("verify_otp.html", aadhaar=aadhaar, error=reason)

    audit(db, "otp_success", aadhaar=aadhaar, success=True)

    user = get_voter_account(aadhaar)

    current_user_agent = request.headers.get("User-Agent", "")
    current_device_id = normalize_device_fingerprint(current_user_agent)

    if "device_id" not in user:
        voter_users.update_one(
            {"aadhaar": aadhaar},
            {"$set": {"device_id": current_device_id, "device_ua_last": current_user_agent}},
        )
        users.update_one(
            {"aadhaar": aadhaar},
            {"$set": {"device_id": current_device_id, "device_ua_last": current_user_agent}},
        )
    else:
        stored_device_id = user.get("device_id", "")
        stored_normalized = normalize_device_fingerprint(stored_device_id)

        is_same_device = (
            stored_device_id == current_device_id
            or stored_normalized == current_device_id
        )

        if not is_same_device:
            if session.get("face_verified") and session.get("aadhaar") == aadhaar:
                voter_users.update_one(
                    {"aadhaar": aadhaar},
                    {
                        "$set": {"device_id": current_device_id, "device_ua_last": current_user_agent},
                        "$push": {"device_id_history": {"$each": [stored_device_id], "$slice": -5}},
                    },
                )
                users.update_one(
                    {"aadhaar": aadhaar},
                    {
                        "$set": {"device_id": current_device_id, "device_ua_last": current_user_agent},
                        "$push": {"device_id_history": {"$each": [stored_device_id], "$slice": -5}},
                    },
                )
            else:
                audit(db, "device_mismatch", aadhaar=aadhaar, success=False)
                return render_template("verify_otp.html", aadhaar=aadhaar, error="Unauthorized device. Please login from your registered device/browser.")

    session["aadhaar"] = aadhaar
    session["role"] = user.get("role", "voter")

    if session.get("face_verified"):
        session["authenticated"] = True
        audit(db, "login_success", aadhaar=aadhaar, success=True)
        return redirect(url_for("vote"))

    return render_template("face_verify.html", aadhaar=aadhaar, error=None, action_url="/verify_face")

# ---------------- FACE MATCH ----------------

@app.route("/verify_face", methods=["POST"])
def verify_face():

    if not ensure_mongo_connection():
        return (
            "MongoDB connection failed. Fix MONGO_URI / TLS certificates, then restart the server.\n\n"
            f"Details: {mongo_error}",
            500,
        )

    aadhaar = request.form["aadhaar"]
    face_image = request.form.get("face_image", "")

    if not face_image:
        return render_template("face_verify.html", aadhaar=aadhaar, error="Face image missing. Please capture your face and try again.", action_url="/verify_face")

    user = get_voter_account(aadhaar)

    captured_encoding = extract_face_encoding(face_image)

    if captured_encoding is None:
        return render_template("face_verify.html", aadhaar=aadhaar, error="Face not detected. Please capture again.", action_url="/verify_face")

    if not compare_faces(user["face_encoding"], captured_encoding):
        return render_template("face_verify.html", aadhaar=aadhaar, error="Face mismatch. Please try again in good lighting.", action_url="/verify_face")

    # All MFA steps passed – mark user as authenticated for voting
    session["aadhaar"] = aadhaar
    session["authenticated"] = True

    return redirect(url_for("vote"))


# ---------------- VOTING (PQ BACKEND INTEGRATION) ----------------

@app.route("/vote", methods=["GET", "POST"])
def vote():
    if not session.get("authenticated") or "aadhaar" not in session:
        return redirect(url_for("login"))

    if session.get("role", "voter") != "voter":
        return redirect(url_for("home"))

    aadhaar = session["aadhaar"]

    if request.method == "GET":
        # Fetch candidate list from the PQ election server
        candidates = []
        try:
            resp = requests.get(f"{ELECTION_API_URL}/status", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
        except Exception:
            candidates = ["Alice", "Bob", "Charlie"]

        return render_template("vote.html", aadhaar=aadhaar, candidates=candidates, error=None)

    # POST: cast vote
    candidate = request.form.get("candidate")
    private_key = request.form.get("private_key")

    if not candidate or not private_key:
        # Re-render with error
        candidates = ["Alice", "Bob", "Charlie"]
        return render_template(
            "vote.html",
            aadhaar=aadhaar,
            candidates=candidates,
            error="Candidate and private key are required.",
        )

    payload = {
        "voter_id": aadhaar,
        "candidate_id": candidate,
        "private_key": private_key,
    }

    try:
        resp = requests.post(f"{ELECTION_API_URL}/vote", json=payload, timeout=10)
        if resp.status_code != 200:
            error_msg = resp.json().get("error", "Failed to submit vote.")
            candidates = ["Alice", "Bob", "Charlie"]
            return render_template(
                "vote.html",
                aadhaar=aadhaar,
                candidates=candidates,
                error=error_msg,
            )

        result = resp.json()
    except Exception as e:
        candidates = ["Alice", "Bob", "Charlie"]
        return render_template(
            "vote.html",
            aadhaar=aadhaar,
            candidates=candidates,
            error=f"Could not reach election server: {str(e)}",
        )

    return render_template(
        "receipt.html",
        vote_id=result.get("vote_id"),
        receipt_hash=result.get("receipt_hash"),
    )


# ---------------- ADMIN RBAC + DASHBOARD ----------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":
        if not ensure_mongo_connection():
            return (
                "MongoDB connection failed. Fix MONGO_URI / TLS certificates, then restart the server.\n\n"
                f"Details: {mongo_error}",
                500,
            )

        aadhaar = request.form.get("aadhaar", "").strip()
        password = request.form.get("password", "")

        user = get_admin_account(aadhaar)
        if not user:
            return render_template("admin_login.html", error="Admin account not found.")

        if not bcrypt.checkpw(password.encode(), user["password"]):
            return render_template("admin_login.html", error="Invalid password.")

        session["authenticated"] = True
        session["role"] = "admin"
        session["aadhaar"] = aadhaar
        return redirect(url_for("admin_dashboard"))

    return render_template("admin_login.html", error=None)


@app.route("/admin/register", methods=["GET", "POST"])
def admin_register():

    if request.method == "POST":
        if not ensure_mongo_connection():
            return (
                "MongoDB connection failed. Fix MONGO_URI / TLS certificates, then restart the server.\n\n"
                f"Details: {mongo_error}",
                500,
            )

        aadhaar = request.form.get("aadhaar", "").strip()
        name = request.form.get("name", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not validate_aadhaar(aadhaar):
            return render_template("admin_register.html", error="Invalid Aadhaar. It must be a 12-digit number.", success=None)

        if len(password) < 6:
            return render_template("admin_register.html", error="Password must be at least 6 characters.", success=None)

        if password != confirm_password:
            return render_template("admin_register.html", error="Passwords do not match.", success=None)

        if find_existing_account_by_aadhaar(aadhaar):
            return render_template("admin_register.html", error="User already exists with this Aadhaar.", success=None)

        admin_users.insert_one(
            {
                "aadhaar": aadhaar,
                "name": name or "Admin User",
                "password": bcrypt.hashpw(password.encode(), bcrypt.gensalt()),
                "role": "admin",
                "created_at": datetime.utcnow(),
            }
        )

        return render_template("admin_register.html", error=None, success="Admin account created successfully. You can login now.")

    return render_template("admin_register.html", error=None, success=None)


@app.route("/admin/dashboard", methods=["GET", "POST"])
@require_role("admin")
def admin_dashboard():
    message = None
    error = None
    encrypted_count = None
    count_results = {}
    winner = None
    extra_details = {}

    if request.method == "POST":
        try:
            count_resp = requests.post(
                f"{ELECTION_API_URL}/count-votes",
                json={"triggered_by": "admin", "run_crypto_pipeline": False},
                timeout=45,
            )
            # Guard against empty or non-JSON responses
            try:
                data = count_resp.json()
            except Exception:
                data = {}
                error = f"Backend returned status {count_resp.status_code} with non-JSON body: {count_resp.text[:300]}"

            if not error:
                if count_resp.status_code == 200:
                    encrypted_count = data.get("encrypted_result")
                    count_results = data.get("results") or {}
                    winner = data.get("winner")
                    extra_details = {
                        "election_id": data.get("election_id"),
                        "total_votes": data.get("total_votes"),
                        "result_ready": data.get("result_ready"),
                        "approved_officials": data.get("threshold_approved_count"),
                        "phases_completed": data.get("phases_completed"),
                    }
                    message = "Counting completed successfully."
                else:
                    error = data.get("error", f"Backend error (HTTP {count_resp.status_code})")
        except Exception as e:
            error = f"Could not reach backend: {str(e)}"

    dashboard_data = {}
    status_data = {}
    try:
        d_resp = requests.get(f"{ELECTION_API_URL}/admin/dashboard-data", timeout=10)
        if d_resp.status_code == 200:
            dashboard_data = d_resp.json()
    except Exception:
        dashboard_data = {}

    try:
        s_resp = requests.get(f"{ELECTION_API_URL}/status", timeout=8)
        if s_resp.status_code == 200:
            status_data = s_resp.json()
    except Exception:
        status_data = {}

    return render_template(
        "admin_dashboard.html",
        message=message,
        error=error,
        encrypted_count=encrypted_count,
        count_results=count_results,
        winner=winner,
        extra_details=extra_details,
        dashboard=dashboard_data,
        status=status_data,
    )


@app.route("/admin/manage-officials", methods=["GET", "POST"])
@require_role("admin")
def admin_manage_officials():
    message = None
    error = None

    if not ensure_mongo_connection():
        return (
            "MongoDB connection failed. Fix MONGO_URI / TLS certificates, then restart the server.\n\n"
            f"Details: {mongo_error}",
            500,
        )

    if request.method == "POST":
        action = request.form.get("action", "").strip().lower()
        request_id = request.form.get("request_id", "").strip()
        user_aadhaar = request.form.get("user_aadhaar", "").strip()

        try:
            if action == "approve_request":
                if not request_id:
                    raise ValueError("Request ID is required for approval.")

                req = official_requests.find_one({"_id": ObjectId(request_id), "status": "pending"})
                if not req:
                    raise ValueError("Pending request not found.")

                if find_existing_account_by_aadhaar(req["aadhaar"]):
                    raise ValueError("A user already exists with this Aadhaar.")

                auth_user_doc = {
                    "aadhaar": req["aadhaar"],
                    "name": req.get("name") or req.get("official_id"),
                    "password": req["password_hash"],
                    "role": "official",
                    "official_id": req["official_id"],
                    "created_at": datetime.utcnow(),
                }
                official_doc = {
                    "official_id": req["official_id"],
                    "name": req.get("name") or req.get("official_id"),
                    "key_share": req.get("secret_key"),
                    "secret_key": req.get("secret_key"),
                    "has_approved": False,
                    "approved_at": None,
                    "election_id": "ELECTION_001",
                }

                # Task 3: single ACID transaction — request + auth_user + official
                transactional_approve_official(client, db, request_id, auth_user_doc, official_doc)

                # Task 7: audit
                audit(db, "official_approved", aadhaar=req["aadhaar"], success=True,
                      details={"official_id": req["official_id"],
                               "reviewed_by": session.get("aadhaar")})
                message = f"Official request approved for {req['official_id']}."

            elif action == "reject_request":
                if not request_id:
                    raise ValueError("Request ID is required for rejection.")

                updated = official_requests.update_one(
                    {"_id": ObjectId(request_id), "status": "pending"},
                    {
                        "$set": {
                            "status": "rejected",
                            "reviewed_at": datetime.utcnow(),
                            "reviewed_by": session.get("aadhaar"),
                        }
                    },
                )
                if updated.matched_count == 0:
                    raise ValueError("Pending request not found.")
                message = "Official request rejected."

            elif action == "delete_official":
                if not user_aadhaar:
                    raise ValueError("Aadhaar is required to delete an official account.")

                deleted = official_auth_users.delete_one({"aadhaar": user_aadhaar})
                if deleted.deleted_count == 0:
                    raise ValueError("Official user not found.")
                message = f"Official account deleted for Aadhaar {user_aadhaar}."
            else:
                raise ValueError("Invalid action.")
        except Exception as e:
            error = str(e)

    pending_requests = list(
        official_requests.find({"status": "pending"}, {"password_hash": 0}).sort("requested_at", 1)
    )
    for req in pending_requests:
        req["request_id"] = str(req["_id"])

    registered_officials = list(
        official_auth_users.find(
            {},
            {"_id": 0, "aadhaar": 1, "name": 1, "official_id": 1, "created_at": 1},
        ).sort("created_at", -1)
    )

    return render_template(
        "admin_manage_officials.html",
        message=message,
        error=error,
        pending_requests=pending_requests,
        registered_officials=registered_officials,
    )


@app.route("/admin/reset-election", methods=["POST"])
@require_role("admin")
def admin_reset_election():
    """Reset election: clear votes, approvals, and results."""
    if not ensure_mongo_connection():
        return render_template(
            "admin_dashboard.html",
            error="MongoDB connection failed.",
            message=None,
            encrypted_count=None,
            count_results={},
            winner=None,
            extra_details={},
            dashboard={},
            status={},
        ), 500

    password = request.form.get("reset_password", "").strip()
    admin_aadhaar = session.get("aadhaar")

    if not password:
        return render_template(
            "admin_dashboard.html",
            error="Admin password is required for reset.",
            message=None,
            encrypted_count=None,
            count_results={},
            winner=None,
            extra_details={},
            dashboard={},
            status={},
        )

    # Verify admin password using same helper as login
    admin_doc = get_admin_account(admin_aadhaar)
    if not admin_doc:
        return render_template(
            "admin_dashboard.html",
            error="Admin account not found. Reset cancelled.",
            message=None,
            encrypted_count=None,
            count_results={},
            winner=None,
            extra_details={},
            dashboard={},
            status={},
        )
    
    # Handle both bytes and string password formats from MongoDB
    stored_password = admin_doc.get("password")
    if isinstance(stored_password, str):
        stored_password = stored_password.encode()
    
    if not bcrypt.checkpw(password.encode(), stored_password):
        return render_template(
            "admin_dashboard.html",
            error="Invalid admin password. Reset cancelled.",
            message=None,
            encrypted_count=None,
            count_results={},
            winner=None,
            extra_details={},
            dashboard={},
            status={},
        )

    try:
        # Get active election
        active_election = db["elections"].find_one({"status": "active"})
        if active_election:
            election_id = active_election["election_id"]
        else:
            election_id = "ELECTION_001"

        # Clear votes
        db["votes"].delete_many({"election_id": election_id})

        # Reset official approvals
        db["officials"].update_many(
            {"election_id": election_id},
            {"$set": {"has_approved": False, "approved_at": None}}
        )

        # Reset election result
        db["elections"].update_one(
            {"election_id": election_id},
            {"$set": {
                "status": "active",
                "final_result_ready": False,
                "aggregated_encrypted_result": None,
                "updated_at": datetime.utcnow().isoformat()
            }}
        )

        # Clear blockchain and results for this election
        db["blockchain"].delete_many({"election_id": election_id})
        db["results"].delete_many({"election_id": election_id})

        message = f"Election {election_id} has been reset successfully. All votes, approvals, and results cleared."

    except Exception as e:
        message = None
        return render_template(
            "admin_dashboard.html",
            error=f"Reset failed: {str(e)}",
            message=None,
            encrypted_count=None,
            count_results={},
            winner=None,
            extra_details={},
            dashboard={},
            status={},
        )

    return render_template(
        "admin_dashboard.html",
        message=message,
        error=None,
        encrypted_count=None,
        count_results={},
        winner=None,
        extra_details={},
        dashboard={},
        status={},
    )


@app.route("/admin/add-candidate", methods=["GET", "POST"])
@require_role("admin")
def admin_add_candidate():
    message = None
    error = None

    if request.method == "POST":
        action = request.form.get("action", "add")
        payload = {
            "action": action,
            "candidate_id": request.form.get("candidate_id", "").strip(),
            "name": request.form.get("name", "").strip(),
            "party": request.form.get("party", "").strip(),
            "election_id": request.form.get("election_id", "").strip() or None,
        }
        try:
            resp = requests.post(f"{ELECTION_API_URL}/admin/add-candidate", json=payload, timeout=10)
            data = resp.json()
            if resp.status_code == 200:
                message = f"Candidate action '{action}' completed successfully."
            else:
                error = data.get("error", "Candidate operation failed")
        except Exception as e:
            error = f"Could not reach backend: {str(e)}"

    return render_template("admin_add_candidate.html", message=message, error=error)


@app.route("/admin/start-election", methods=["POST"])
@require_role("admin")
def admin_start_election():
    payload = {
        "election_id": request.form.get("election_id", "").strip() or None,
        "title": request.form.get("title", "").strip() or "General Election",
    }
    try:
        requests.post(f"{ELECTION_API_URL}/admin/start-election", json=payload, timeout=10)
    except Exception:
        pass
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/end-election", methods=["POST"])
@require_role("admin")
def admin_end_election():
    payload = {
        "election_id": request.form.get("election_id", "").strip() or None,
    }
    try:
        requests.post(f"{ELECTION_API_URL}/admin/end-election", json=payload, timeout=10)
    except Exception:
        pass
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/view-blockchain", methods=["GET"])
@require_role("admin")
def admin_view_blockchain():
    blocks = []
    error = None
    page = max(1, int(request.args.get("page", 1)))
    per_page = 10
    total = 0
    try:
        resp = requests.get(
            f"{ELECTION_API_URL}/admin/view-blockchain",
            params={"page": page, "per_page": per_page},
            timeout=10,
        )
        data = resp.json()
        if resp.status_code == 200:
            blocks = data.get("blocks", [])
            total = data.get("count", len(blocks))
        else:
            error = data.get("error", "Could not fetch blockchain")
    except Exception as e:
        error = f"Could not reach backend: {str(e)}"

    total_pages = max(1, (total + per_page - 1) // per_page)
    return render_template(
        "admin_blockchain.html",
        blocks=blocks, error=error,
        page=page, per_page=per_page,
        total=total, total_pages=total_pages,
    )


@app.route("/admin/view-encrypted-votes", methods=["GET"])
@require_role("admin")
def admin_view_encrypted_votes():
    votes_data = []
    error = None
    page = max(1, int(request.args.get("page", 1)))
    per_page = 20
    total = 0
    try:
        resp = requests.get(
            f"{ELECTION_API_URL}/admin/view-encrypted-votes",
            params={"page": page, "per_page": per_page},
            timeout=10,
        )
        data = resp.json()
        if resp.status_code == 200:
            votes_data = data.get("votes", [])
            total = data.get("count", len(votes_data))
        else:
            error = data.get("error", "Could not fetch encrypted votes")
    except Exception as e:
        error = f"Could not reach backend: {str(e)}"

    total_pages = max(1, (total + per_page - 1) // per_page)
    return render_template(
        "admin_encrypted_votes.html",
        votes=votes_data, error=error,
        page=page, per_page=per_page,
        total=total, total_pages=total_pages,
    )


# Task 7: Audit log UI — fetches from backend aggregation endpoint
@app.route("/admin/audit-logs-ui", methods=["GET"])
@require_role("admin")
def admin_audit_logs_ui():
    logs = []
    failed_per_hour = []
    try:
        resp = requests.get(f"{ELECTION_API_URL}/admin/audit-logs", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            logs = data.get("logs", [])
            failed_per_hour = data.get("failed_logins_per_hour", [])
    except Exception:
        pass
    return render_template("admin_audit_logs.html", logs=logs, failed_per_hour=failed_per_hour)


# Task 8: Admin GridFS image management UI
@app.route("/admin/gridfs-images", methods=["GET"])
@require_role("admin")
def admin_gridfs_images():
    """Admin UI to search and view GridFS images by voter aadhaar."""
    aadhaar = request.args.get("aadhaar", "").strip()
    files = []
    error = None
    
    if aadhaar:
        if not ensure_mongo_connection():
            error = f"MongoDB connection failed: {mongo_error}"
        else:
            try:
                from voting_system_crypto.backend.mongo_features import list_voter_files_gridfs
                files = list_voter_files_gridfs(mongo_db, aadhaar)
                if not files:
                    error = f"No files found for Aadhaar: {aadhaar}"
            except Exception as e:
                error = f"Error retrieving files: {str(e)}"
    
    return render_template("admin_gridfs_images.html", aadhaar=aadhaar, files=files, error=error)


@app.route("/admin/gridfs-image/<file_id>", methods=["GET"])
@require_role("admin")
def admin_retrieve_gridfs_image(file_id):
    """Download/view a specific GridFS file by file_id."""
    if not ensure_mongo_connection():
        return f"MongoDB connection failed: {mongo_error}", 500
    
    try:
        from voting_system_crypto.backend.mongo_features import retrieve_file_gridfs
        from bson import ObjectId
        
        file_data = retrieve_file_gridfs(mongo_db, ObjectId(file_id))
        if not file_data:
            return "File not found", 404
        
        # Get file metadata for MIME type
        file_doc = mongo_db["fs.files"].find_one({"_id": ObjectId(file_id)})
        if not file_doc:
            return "File metadata not found", 404
        
        filename = file_doc.get("filename", "image.jpg")
        file_type = file_doc.get("metadata", {}).get("type", "image/jpeg")
        
        from flask import send_file
        from io import BytesIO
        
        return send_file(
            BytesIO(file_data),
            mimetype=file_type,
            as_attachment=False,
            download_name=filename
        )
    except Exception as e:
        return f"Error retrieving file: {str(e)}", 500


# ---------------- OFFICIAL RBAC + APPROVAL ----------------

@app.route("/official/login", methods=["GET", "POST"])
def official_login():

    if request.method == "POST":
        if not ensure_mongo_connection():
            return (
                "MongoDB connection failed. Fix MONGO_URI / TLS certificates, then restart the server.\n\n"
                f"Details: {mongo_error}",
                500,
            )

        aadhaar = request.form.get("aadhaar", "").strip()
        password = request.form.get("password", "")
        user = get_official_auth_account(aadhaar)

        if not user:
            return render_template("official_login.html", error="Official account not found.")
        if not bcrypt.checkpw(password.encode(), user["password"]):
            return render_template("official_login.html", error="Invalid password.")

        session["authenticated"] = True
        session["role"] = "official"
        session["aadhaar"] = aadhaar
        session["official_id"] = user.get("official_id") or user.get("name") or aadhaar
        return redirect(url_for("official_dashboard"))

    return render_template("official_login.html", error=None)


@app.route("/official/register", methods=["GET", "POST"])
def official_register():

    if request.method == "POST":
        if not ensure_mongo_connection():
            return (
                "MongoDB connection failed. Fix MONGO_URI / TLS certificates, then restart the server.\n\n"
                f"Details: {mongo_error}",
                500,
            )

        aadhaar = request.form.get("aadhaar", "").strip()
        name = request.form.get("name", "").strip()
        official_id = request.form.get("official_id", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not validate_aadhaar(aadhaar):
            return render_template("official_register.html", error="Invalid Aadhaar. It must be a 12-digit number.", success=None)

        if not official_id:
            return render_template("official_register.html", error="Official ID is required.", success=None)

        if len(password) < 6:
            return render_template("official_register.html", error="Password must be at least 6 characters.", success=None)

        if password != confirm_password:
            return render_template("official_register.html", error="Passwords do not match.", success=None)

        if find_existing_account_by_aadhaar(aadhaar):
            return render_template("official_register.html", error="User already exists with this Aadhaar.", success=None)

        if official_requests.find_one({"aadhaar": aadhaar, "status": "pending"}):
            return render_template("official_register.html", error="A pending request already exists for this Aadhaar.", success=None)

        official_record = officials.find_one({"official_id": official_id})

        if official_auth_users.find_one({"official_id": official_id}):
            return render_template("official_register.html", error="This Official ID is already linked to another account.", success=None)

        if official_requests.find_one({"official_id": official_id, "status": "pending"}):
            return render_template("official_register.html", error="A pending request already exists for this Official ID.", success=None)

        # Generate secret key for official
        secret_key = generate_official_key_share()
        
        official_requests.insert_one(
            {
                "aadhaar": aadhaar,
                "name": name or (official_record.get("name") if official_record else official_id),
                "official_id": official_id,
                "password_hash": bcrypt.hashpw(password.encode(), bcrypt.gensalt()),
                "secret_key": secret_key,
                "status": "pending",
                "requested_at": datetime.utcnow(),
            }
        )

        return render_template(
            "official_register.html",
            error=None,
            success=f"Registration submitted. Save your secret key (required for approval): {secret_key}",
        )

    return render_template("official_register.html", error=None, success=None)


@app.route("/official/dashboard", methods=["GET"])
@require_role("official")
def official_dashboard():
    status_data = {}
    error = None
    key_share = None
    election_id = None
    try:
        resp = requests.get(f"{ELECTION_API_URL}/official/status", timeout=10)
        if resp.status_code == 200:
            status_data = resp.json()
        else:
            status_data = {}
            error = "Could not load official status."
    except Exception as e:
        error = f"Could not reach backend: {str(e)}"

    if ensure_mongo_connection():
        official_doc = officials.find_one({"official_id": session.get("official_id")})
        if official_doc:
            key_share = official_doc.get("key_share")
            election_id = official_doc.get("election_id")

    return render_template(
        "official_dashboard.html",
        status=status_data,
        error=error,
        official_id=session.get("official_id"),
        key_share=key_share,
        election_id=election_id,
    )


@app.route("/official/approve-decryption", methods=["POST"])
@require_role("official")
def official_approve_decryption():
    official_id = request.form.get("official_id") or session.get("official_id")
    secret_key = request.form.get("secret_key", "").strip()
    election_id = request.form.get("election_id") or None
    
    error = None
    if not secret_key:
        error = "Secret key is required for approval."
    else:
        # Verify secret key against stored value
        official_doc = officials.find_one({"official_id": official_id})
        if not official_doc or official_doc.get("secret_key") != secret_key:
            error = "Invalid secret key. Approval denied."
    
    if error:
        return render_template(
            "official_dashboard.html",
            official_id=session.get("official_id"),
            election_id=election_id,
            key_share=session.get("key_share"),
            status={},
            error=error,
        )
    
    payload = {
        "official_id": official_id,
        "election_id": election_id,
    }
    try:
        requests.post(f"{ELECTION_API_URL}/official/approve-decryption", json=payload, timeout=15)
    except Exception:
        pass
    return redirect(url_for("official_dashboard"))


if __name__ == "__main__":
    print(f"Tesseract executable: {TESSERACT_EXE or 'NOT FOUND'}")
    app.run(debug=True, port=8000, use_reloader=False)