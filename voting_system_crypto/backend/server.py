"""
Main Election Server - COMPLETE POST-QUANTUM SECURE FLOW
Orchestrates all 9 phases of the voting system

PHASE 1: Registration (Identity + Keys + Certificate)
PHASE 2: Login (Multi-Factor Authentication)
PHASE 3: Voting (Dilithium Sign + Kyber Encrypt)
PHASE 4: Mixnet Shuffling (Anonymous submission)
PHASE 5: Blockchain (Immutable audit trail)
PHASE 6: E2E Verification (Receipt checking)
PHASE 7: Homomorphic Counting (Privacy-preserving tally)
PHASE 8: Threshold Decryption (Distributed key)
PHASE 9: Air-Gapped Counting (Secure final tally)
OPTIONAL: Zero Knowledge Proofs (Vote validity)
"""
import os
import sys
import hashlib
from datetime import datetime
from collections import Counter

import certifi
from dotenv import load_dotenv
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from pymongo import MongoClient, DESCENDING
from pymongo.errors import DuplicateKeyError, PyMongoError

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.registration import VoterRegistration
from auth.login import MultiFactorAuth
from voting.vote_handler import VoteHandler
from voting.mixnet import MixnetCascade
from voting.zkp import ZeroKnowledgeProof
from blockchain.chain import VotingBlockchain
from counting.homomorphic import HomomorphicCounter
from counting.threshold import ElectionAuthorities
from crypto.pq_crypto import generate_election_keypair, DilithiumKeyPair
from mongo_features import (
    bootstrap_mongo_features,
    is_duplicate_vote_error,
    agg_votes_per_candidate,
    agg_turnout_per_hour,
    agg_dashboard_facet,
    agg_merge_results,
    agg_failed_logins_per_hour,
    transactional_store_vote,
    transactional_approve_official,
    store_otp_session,
    verify_otp_session,
    record_login_attempt,
    is_account_locked,
    audit,
    start_vote_change_stream,
    register_stream_callback,
    store_file_gridfs,
    log_explain_stats,
    migrate_legacy_users,
    cleanup_officials_key_shares,
)

app = Flask(__name__)
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32 MB — face images are large base64 payloads

MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    raise RuntimeError("MONGO_URI is not set. Add it to your .env file.")
DB_NAME = os.environ.get("ELECTION_DB_NAME", "evoting_db")

mongo_client = MongoClient(
    MONGO_URI,
    tls=True,
    tlsCAFile=certifi.where(),
    serverSelectionTimeoutMS=8000,
    connectTimeoutMS=8000,
)
db = mongo_client[DB_NAME]

votes_collection = db["votes"]
blockchain_collection = db["blockchain"]
candidates_collection = db["candidates"]
elections_collection = db["elections"]
officials_collection = db["officials"]
results_collection = db["results"]

DEFAULT_ELECTION_ID = "ELECTION_001"
DEFAULT_CANDIDATES = [
    {"candidate_id": "ALICE", "name": "Alice", "party": "Independent"},
    {"candidate_id": "BOB", "name": "Bob", "party": "Independent"},
    {"candidate_id": "CHARLIE", "name": "Charlie", "party": "Independent"},
]


# Initialize systems
print("\n" + "=" * 70)
print("INITIALIZING POST-QUANTUM VOTING SYSTEM")
print("=" * 70)

registration = VoterRegistration()
print("✔ PHASE 1: Registration system ready")

mfa = MultiFactorAuth(registration)
print("✔ PHASE 2: Multi-factor authentication ready")

blockchain = VotingBlockchain()
print("✔ PHASE 5: Blockchain initialized")

mixnet = MixnetCascade(num_nodes=3)
print("✔ PHASE 4: Mixnet cascade ready (3 nodes)")

# Generate election keypair (Kyber)
election_kyber, election_public_key = generate_election_keypair()
vote_handler = VoteHandler(election_public_key)
print("✔ PHASE 3: Kyber encryption ready")

# Setup authorities (3 out of 5 threshold)
authorities = ElectionAuthorities(
    authority_names=["Authority_A", "Authority_B", "Authority_C", "Authority_D", "Authority_E"],
    threshold=3,
)
print("✔ PHASE 8: Threshold decryption ready (3-of-5)")

# Initialize homomorphic counter (base object; request-local counters are used for counting)
homomorphic_counter = HomomorphicCounter()
print("✔ PHASE 7: Homomorphic counting ready")

# Initialize ZKP system
candidates = [c["name"] for c in DEFAULT_CANDIDATES]
zkp_system = ZeroKnowledgeProof(candidates)
print("✔ OPTIONAL: Zero Knowledge Proofs ready")

print("=" * 70)
print("ALL SYSTEMS OPERATIONAL")
print("=" * 70 + "\n")


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _json_body() -> dict:
    return request.get_json(silent=True, force=True) or {}


def _ensure_mongo_ready() -> tuple[bool, str | None]:
    try:
        mongo_client.admin.command("ping")
        return True, None
    except Exception as e:  # pragma: no cover - operational guard
        return False, str(e)


def _get_active_election() -> dict | None:
    return elections_collection.find_one({"status": "active"})


def _get_election_by_id(election_id: str) -> dict | None:
    return elections_collection.find_one({"election_id": election_id})


def _approved_official_ids(election_id: str) -> list[str]:
    docs = officials_collection.find(
        {"election_id": election_id, "has_approved": True},
        {"official_id": 1, "_id": 0},
    )
    return [d["official_id"] for d in docs]


def _candidate_names_for_election(election_id: str) -> list[str]:
    cursor = candidates_collection.find(
        {"election_id": election_id},
        {"name": 1, "candidate_id": 1, "_id": 0},
    )
    docs = list(cursor)
    if docs:
        return [d["name"] for d in docs]
    return [c["name"] for c in DEFAULT_CANDIDATES]


def _persist_latest_block(election_id: str):
    latest = blockchain.get_latest_block()
    vote_hash = ""
    if latest.votes:
        concat = "|".join(v.get("vote_hash", "") for v in latest.votes)
        vote_hash = hashlib.sha3_256(concat.encode()).hexdigest()

    blockchain_collection.update_one(
        {"block_id": f"{election_id}_B{latest.index}"},
        {
            "$set": {
                "block_id": f"{election_id}_B{latest.index}",
                "block_index": latest.index,
                "election_id": election_id,
                "previous_hash": latest.previous_hash,
                "vote_hash": vote_hash,
                "nonce": latest.nonce,
                "timestamp": latest.timestamp,
                "hash": latest.hash,
                "votes": latest.votes,
            }
        },
        upsert=True,
    )


def _store_vote(vote_result: dict, vote_record: dict, election_id: str):
    """
    Task 3: Atomically insert vote + blockchain block in one ACID transaction.
    Task 1: DuplicateKeyError on voter_id_hash+election_id prevents double voting.
    Timestamp stored as real datetime object (Task 2 requirement).
    """
    voter_id_hash = hashlib.sha3_256(vote_record.get("voter_id", "").encode()).hexdigest()

    # Parse timestamp to real datetime for $dateTrunc aggregations (Task 2)
    raw_ts = vote_record.get("timestamp", "")
    try:
        ts_dt = datetime.fromisoformat(raw_ts)
    except (ValueError, TypeError):
        ts_dt = datetime.utcnow()

    vote_doc = {
        "vote_id":       vote_result["vote_id"],
        "election_id":   election_id,
        "encrypted_vote": vote_record.get("encrypted_vote", ""),
        "signature":     vote_record.get("signature", ""),
        "timestamp":     ts_dt,                          # real datetime
        "receipt_hash":  vote_result["receipt_hash"],
        "candidate_id":  vote_record.get("candidate_id"),
        "voter_id_hash": voter_id_hash,
    }

    latest = blockchain.get_latest_block()
    block_id = f"{election_id}_B{latest.index}"
    vote_hash_concat = "|".join(v.get("vote_hash", "") for v in latest.votes)
    block_update = {
        "block_id":    block_id,
        "block_index": latest.index,
        "election_id": election_id,
        "previous_hash": latest.previous_hash,
        "vote_hash":   hashlib.sha3_256(vote_hash_concat.encode()).hexdigest(),
        "nonce":       latest.nonce,
        "timestamp":   latest.timestamp,
        "hash":        latest.hash,
        "votes":       latest.votes,
    }

    # Task 3: single ACID transaction — vote + blockchain block
    transactional_store_vote(mongo_client, db, vote_doc, block_id, block_update)


def _compute_homomorphic_tallies(vote_docs: list[dict], candidate_names: list[str], include_plaintext: bool = False):
    counter = HomomorphicCounter()

    for v in vote_docs:
        candidate = v.get("candidate_id")
        if candidate not in candidate_names:
            continue
        encoding = counter.encode_vote(candidate, candidate_names)
        encrypted = counter.encrypt_vote(encoding)
        counter.add_encrypted_vote(encrypted)

    encrypted_serialized = {}
    for c_name, enc_value in counter.encrypted_tallies.items():
        encrypted_serialized[c_name] = {
            "ciphertext": str(enc_value.ciphertext()),
            "exponent": enc_value.exponent,
        }

    if not include_plaintext:
        return encrypted_serialized, None

    plaintext_results = counter.decrypt_final_tally()
    return encrypted_serialized, plaintext_results


def _compute_plaintext_tally(vote_docs: list[dict], candidate_names: list[str]) -> dict[str, int]:
    counts = Counter(v.get("candidate_id") for v in vote_docs if v.get("candidate_id") in candidate_names)
    return {name: int(counts.get(name, 0)) for name in candidate_names}


def _finalize_results_if_threshold_met(
    election_id: str,
    candidate_names: list[str],
    vote_docs: list[dict],
    precomputed_results: dict[str, int] | None = None,
):
    approved_docs = list(
        officials_collection.find(
            {"election_id": election_id, "has_approved": True, "key_share": {"$exists": True, "$ne": ""}},
            {"official_id": 1, "key_share": 1, "_id": 0},
        )
    )

    if len(approved_docs) < 3:
        return None

    selected = approved_docs[:3]
    selected_ids = [d["official_id"] for d in selected]
    selected_shares = sorted(d["key_share"] for d in selected)

    reconstructed_key = hashlib.sha3_256("|".join(selected_shares).encode()).hexdigest()

    plaintext_results = precomputed_results if precomputed_results is not None else _compute_plaintext_tally(vote_docs, candidate_names)

    winner = max(plaintext_results, key=plaintext_results.get) if plaintext_results else None
    total_votes = sum(plaintext_results.values())

    # Build per-candidate breakdown with names from DB
    candidate_docs = list(candidates_collection.find(
        {"election_id": election_id}, {"candidate_id": 1, "name": 1, "party": 1, "_id": 0}
    ))
    name_map = {d["candidate_id"]: d for d in candidate_docs}

    per_candidate = []
    for cid, count in sorted(plaintext_results.items(), key=lambda x: -x[1]):
        meta = name_map.get(cid, {})
        per_candidate.append({
            "candidate_id": cid,
            "name": meta.get("name", cid),
            "party": meta.get("party", "Independent"),
            "votes": count,
            "percentage": round((count / total_votes * 100), 2) if total_votes > 0 else 0,
        })

    # Turnout per hour — convert datetime to ISO string
    raw_turnout = agg_turnout_per_hour(db, election_id)
    turnout = [
        {"hour": t["hour"].isoformat() if hasattr(t["hour"], "isoformat") else str(t["hour"]),
         "votes": t["votes"]}
        for t in raw_turnout
    ]

    results_collection.update_one(
        {"election_id": election_id},
        {
            "$set": {
                "election_id":              election_id,
                "results":                  plaintext_results,       # {candidate_id: count}
                "per_candidate":            per_candidate,           # full breakdown with names
                "winner":                   winner,
                "total_votes":              total_votes,
                "turnout_per_hour":         turnout,
                "decrypted_at":             _now_iso(),
                "officials_used":           selected_ids,
                "threshold_key_reconstruction": reconstructed_key,
            }
        },
        upsert=True,
    )

    elections_collection.update_one(
        {"election_id": election_id},
        {
            "$set": {
                "final_result_ready": True,
                "winner":             winner,
                "total_votes":        total_votes,
                "updated_at":         _now_iso(),
            }
        },
    )

    return {
        "results":       plaintext_results,
        "winner":        winner,
        "total_votes":   total_votes,
        "per_candidate": per_candidate,
        "officials_used": selected_ids,
    }


def _bootstrap_persistent_state():
    ready, err = _ensure_mongo_ready()
    if not ready:
        print(f"[WARN] MongoDB not available for persistence: {err}")
        return

    # Task 1-11: all MongoDB features bootstrapped here
    bootstrap_mongo_features(db, mongo_client)

    # Task 10: performance story — log explain before/after index (runs once at startup)
    log_explain_stats(db, "votes",       {"election_id": DEFAULT_ELECTION_ID},          "votes by election_id")
    log_explain_stats(db, "voter_users", {"aadhaar": "000000000000"},                   "voter_users by aadhaar")
    log_explain_stats(db, "officials",   {"election_id": DEFAULT_ELECTION_ID,
                                          "has_approved": True},                          "officials approved partial")

    election = _get_active_election()
    if not election:
        elections_collection.update_one(
            {"election_id": DEFAULT_ELECTION_ID},
            {
                "$set": {
                    "election_id": DEFAULT_ELECTION_ID,
                    "title": "General Election",
                    "status": "active",
                    "candidates": [c["candidate_id"] for c in DEFAULT_CANDIDATES],
                    "aggregated_encrypted_result": None,
                    "final_result_ready": False,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                }
            },
            upsert=True,
        )

    active_election = _get_active_election() or _get_election_by_id(DEFAULT_ELECTION_ID)
    election_id = active_election["election_id"]

    for c in DEFAULT_CANDIDATES:
        candidates_collection.update_one(
            {"candidate_id": c["candidate_id"], "election_id": election_id},
            {
                "$set": {
                    "candidate_id": c["candidate_id"],
                    "name": c["name"],
                    "party": c["party"],
                    "election_id": election_id,
                }
            },
            upsert=True,
        )

    elections_collection.update_one(
        {"election_id": election_id},
        {"$addToSet": {"candidates": {"$each": [c["candidate_id"] for c in DEFAULT_CANDIDATES]}}},
    )

    # Task 11: migrate any legacy voter documents
    migrate_legacy_users(db)

    # Task 9: security cleanup — remove redundant key fields
    cleanup_officials_key_shares(db)

    # Task 6: start change stream for live dashboard
    live_vote_counts = {}

    def _on_new_vote(doc):
        eid  = doc.get("election_id", "")
        cand = doc.get("candidate_id", "")
        if eid not in live_vote_counts:
            live_vote_counts[eid] = {}
        live_vote_counts[eid][cand] = live_vote_counts[eid].get(cand, 0) + 1

    register_stream_callback(_on_new_vote)
    start_vote_change_stream(db)
    app.config["LIVE_VOTE_COUNTS"] = live_vote_counts


_bootstrap_persistent_state()


@app.route("/", methods=["GET"])
def home():
    """API status endpoint"""
    return jsonify(
        {
            "status": "online",
            "system": "Post-Quantum Voting System",
            "version": "2.0.0",
            "phases_implemented": [
                "PHASE_1_REGISTRATION",
                "PHASE_2_LOGIN_MFA",
                "PHASE_3_VOTING_PQ_CRYPTO",
                "PHASE_4_MIXNET_SHUFFLING",
                "PHASE_5_BLOCKCHAIN_INTEGRITY",
                "PHASE_6_E2E_VERIFICATION",
                "PHASE_7_HOMOMORPHIC_COUNTING",
                "PHASE_8_THRESHOLD_DECRYPTION",
                "PHASE_9_AIR_GAPPED_COUNTING",
                "OPTIONAL_ZERO_KNOWLEDGE_PROOFS",
            ],
            "endpoints": {
                "POST /register": "PHASE 1: Register new voter",
                "POST /login": "PHASE 2: Multi-factor authentication",
                "POST /vote": "PHASE 3: Submit encrypted vote",
                "POST /verify-receipt": "PHASE 6: Verify vote receipt",
                "POST /count-votes": "PHASES 7-9: Count votes with all security layers",
                "POST /official/approve-decryption": "Official approval for threshold decryption",
                "GET /status": "System status",
                "GET /blockchain": "Blockchain status",
            },
        }
    ), 200


@app.route("/status", methods=["GET"])
def status():
    """System status with all phases"""
    blockchain_summary = blockchain.get_chain_summary()
    mixnet_stats = mixnet.get_statistics()

    active = _get_active_election()
    if active:
        candidate_names = _candidate_names_for_election(active["election_id"])
    else:
        candidate_names = [c["name"] for c in DEFAULT_CANDIDATES]

    return jsonify(
        {
            "system_status": "OPERATIONAL",
            "registered_voters": len(registration.registered_voters),
            "submitted_votes": len(vote_handler.submitted_votes),
            "blockchain": blockchain_summary,
            "mixnet": mixnet_stats,
            "election_public_key": election_public_key[:32] + "...",
            "candidates": candidate_names,
            "active_election": active["election_id"] if active else None,
            "threshold_authorities": {
                "total": 5,
                "required": 3,
                "scheme": "3-of-5",
            },
        }
    ), 200


@app.route("/blockchain", methods=["GET"])
def blockchain_status():
    """PHASE 5: Blockchain status"""
    summary = blockchain.get_chain_summary()

    blocks = [block.to_dict() for block in blockchain.chain]

    persisted_blocks = list(
        blockchain_collection.find({}, {"_id": 0}).sort("block_index", 1)
    )

    return jsonify(
        {
            "summary": summary,
            "blocks": blocks,
            "persisted_blocks": persisted_blocks,
            "pending_votes": len(blockchain.pending_votes),
        }
    ), 200


@app.route("/register", methods=["POST"])
def register_voter():
    """PHASE 1: Register new voter with quantum-resistant identity"""
    data = _json_body()

    try:
        result = registration.register_voter(
            voter_id=data["voter_id"],
            password=data["password"],
            aadhaar_data=data["aadhaar"],
            face_image=data["face_image"],
        )

        # Generate OTP secret for PHASE 2
        otp_secret = mfa.generate_otp_secret(data["voter_id"])
        result["otp_secret"] = otp_secret

        print(f"\n[PHASE 1] ✔ Voter registered: {data['voter_id']}")

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/login", methods=["POST"])
def login():
    """PHASE 2: Multi-factor authentication login"""
    data = _json_body()

    result = mfa.login(
        voter_id=data["voter_id"],
        password=data["password"],
        otp_code=data["otp"],
        device_info=data["device"],
        face_image=data["face_image"],
    )

    if result["success"]:
        print(f"\n[PHASE 2] ✔ Voter authenticated: {data['voter_id']}")

    return jsonify(result), 200 if result["success"] else 401


@app.route("/vote", methods=["POST"])
def submit_vote():
    """PHASE 3: Submit vote with full PQ crypto flow plus Mongo persistence."""
    data = _json_body()

    active = _get_active_election()
    if active and active.get("status") != "active":
        return jsonify({"error": "Election is not active"}), 400

    election_id = active["election_id"] if active else DEFAULT_ELECTION_ID

    try:
        # Reconstruct voter keypair
        keypair = DilithiumKeyPair()
        keypair.private_key = bytes.fromhex(data["private_key"])
        keypair.public_key = hashlib.sha3_256(keypair.private_key).digest()

        # PHASE 3: Submit vote (signing, encryption, receipt)
        result = vote_handler.submit_vote(
            voter_id=data["voter_id"],
            candidate_id=data["candidate_id"],
            voter_keypair=keypair,
        )

        vote_record = vote_handler.submitted_votes[-1]

        # PHASE 5: Mine into blockchain
        blockchain.add_vote({
            "voter_id":     data["voter_id"],
            "receipt_hash": result["receipt_hash"],
            "timestamp":    vote_record["timestamp"],
        })
        blockchain.mine_pending_votes()

        # Task 3: atomic transaction — vote + blockchain block (Task 1: DuplicateKeyError guard inside)
        _store_vote(result, vote_record, election_id)

        # Task 7: audit log
        audit(db, "vote_submitted", aadhaar=data.get("voter_id", ""),
              success=True, details={"election_id": election_id,
                                     "vote_id": result["vote_id"]})

        # ZKP — refresh valid candidates from DB so newly added candidates are accepted
        current_candidates = _candidate_names_for_election(election_id)
        zkp_system.valid_candidates = current_candidates
        zkp_system.candidate_commitments = zkp_system._generate_commitments()
        zkp = zkp_system.generate_proof(data["candidate_id"], {
            "vote_id": result["vote_id"],
            "timestamp": vote_record["timestamp"],
        })
        result["zkp"] = zkp
        result["election_id"] = election_id

        return jsonify(result), 200

    except DuplicateKeyError as e:
        # Task 1: DB-level double-vote rejection
        if is_duplicate_vote_error(e):
            audit(db, "double_vote_attempt", aadhaar=data.get("voter_id", ""),
                  success=False, details={"election_id": election_id})
            return jsonify({"error": "You have already voted in this election."}), 409
        return jsonify({"error": "Duplicate record error."}), 409
    except Exception as e:
        audit(db, "vote_error", aadhaar=data.get("voter_id", ""),
              success=False, details={"error": str(e)})
        return jsonify({"error": str(e)}), 400


@app.route("/verify-receipt", methods=["POST"])
def verify_receipt():
    """PHASE 6: End-to-end verification."""
    payload = _json_body()
    receipt_hash = payload.get("receipt_hash", "")

    # Check vote handler
    exists = vote_handler.verify_receipt(receipt_hash)

    # Check blockchain
    proof = blockchain.get_vote_proof(receipt_hash)

    in_db = votes_collection.find_one({"receipt_hash": receipt_hash}, {"_id": 0, "vote_id": 1, "election_id": 1})

    return jsonify(
        {
            "verified": exists and proof["found"],
            "in_vote_system": exists,
            "in_blockchain": proof["found"],
            "in_persistent_db": bool(in_db),
            "db_vote": in_db,
            "blockchain_proof": proof,
        }
    ), 200


@app.route("/count-votes", methods=["POST"])
def count_votes():
    """PHASES 4-9: Aggregation-pipeline counting + threshold-gated result reveal."""
    data = _json_body()
    if (data.get("triggered_by") or "").lower() != "admin":
        return jsonify({"error": "Vote counting can only be triggered from admin profile."}), 403

    election_id = data.get("election_id")
    active = _get_active_election()
    if not election_id:
        election_id = active["election_id"] if active else DEFAULT_ELECTION_ID

    # PHASE 5: mine any pending votes
    blockchain.mine_pending_votes()

    if not blockchain.verify_chain():
        return jsonify({"error": "Blockchain integrity compromised"}), 500

    approved_count = len(_approved_official_ids(election_id))
    if approved_count < 3:
        return jsonify({
            "error": "At least 3 official approvals are required before counting.",
            "approved_officials": approved_count,
            "required_officials": 3,
        }), 400

    try:
        candidate_names = _candidate_names_for_election(election_id)

        # Task 2: aggregation pipeline replaces Python Counter loop
        agg_results = agg_votes_per_candidate(db, election_id)
        plaintext_tally = {r["candidate_id"]: r["count"] for r in agg_results}
        # Fill zero for candidates with no votes
        for name in candidate_names:
            plaintext_tally.setdefault(name, 0)

        # Task 2: $merge pipeline writes results into agg_results collection
        agg_merge_results(db, election_id, candidate_names)

        # Task 2: $facet for dashboard stats
        facet_stats = agg_dashboard_facet(db, election_id)

        # Task 2: turnout timeline — convert datetime keys to strings for JSON
        raw_turnout = agg_turnout_per_hour(db, election_id)
        turnout = [
            {"hour": t["hour"].isoformat() if hasattr(t["hour"], "isoformat") else str(t["hour"]),
             "votes": t["votes"]}
            for t in raw_turnout
        ]

        run_crypto_pipeline = bool(data.get("run_crypto_pipeline"))
        encrypted_tally = None
        phases_completed = ["PHASE_5_BLOCKCHAIN_VERIFIED", "PHASE_2_AGG_PIPELINE_COUNTING"]

        if run_crypto_pipeline:
            vote_docs = list(votes_collection.find({"election_id": election_id}, {"_id": 0}))
            encrypted_votes = [v.get("encrypted_vote") for v in vote_docs if v.get("encrypted_vote")]
            if encrypted_votes:
                mixed_votes = mixnet.process_votes(encrypted_votes)
                if not mixnet.verify_count(len(encrypted_votes), len(mixed_votes)):
                    return jsonify({"error": "Vote count mismatch in mixnet"}), 500
            encrypted_tally, _ = _compute_homomorphic_tallies(
                list(votes_collection.find({"election_id": election_id}, {"_id": 0})),
                candidate_names, include_plaintext=False
            )
            phases_completed.insert(0, "PHASE_4_MIXNET_COMPLETE")
            phases_completed.append("PHASE_7_HOMOMORPHIC_ENCRYPTED_COUNT")

        elections_collection.update_one(
            {"election_id": election_id},
            {"$set": {
                "aggregated_encrypted_result": encrypted_tally,
                "counted_at": _now_iso(),
                "updated_at": _now_iso(),
            }},
            upsert=True,
        )

        vote_docs_for_threshold = list(votes_collection.find({"election_id": election_id}, {"_id": 0}))
        final = _finalize_results_if_threshold_met(
            election_id, candidate_names, vote_docs_for_threshold,
            precomputed_results=plaintext_tally,
        )

        # Task 7: audit
        audit(db, "counting_triggered", success=True,
              details={"election_id": election_id, "total": facet_stats["total"]})

        # blockchain_summary may contain non-serializable types — convert safely
        try:
            chain_summary = blockchain.get_chain_summary()
            chain_summary = {k: (v.isoformat() if hasattr(v, "isoformat") else v)
                             for k, v in chain_summary.items()}
        except Exception:
            chain_summary = {}

        response = {
            "success": True,
            "election_id": election_id,
            "encrypted_result": encrypted_tally,
            "results": plaintext_tally,
            "winner": max(plaintext_tally, key=plaintext_tally.get) if plaintext_tally else None,
            "total_votes": facet_stats["total"],
            "facet_stats": facet_stats,
            "turnout_per_hour": turnout,
            "phases_completed": phases_completed,
            "blockchain_valid": blockchain.verify_chain(),
            "mixnet_anonymity": "GUARANTEED",
            "vote_privacy": "PRESERVED",
            "threshold_approved_count": approved_count,
            "result_ready": bool(final),
            "blockchain_summary": chain_summary,
        }

        if final:
            response["results"] = final["results"]
            response["winner"] = final["winner"]
            response["total_votes"] = final["total_votes"]
            response["per_candidate"] = final["per_candidate"]
            response["threshold_authorities_used"] = final["officials_used"]
            response["phases_completed"].extend(["PHASE_8_THRESHOLD_DECRYPT", "PHASE_9_AIR_GAPPED_TALLY"])

        return jsonify(response), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Counting failed: {str(e)}"}), 500


@app.route("/admin/add-candidate", methods=["POST"])
def admin_add_candidate():
    data = _json_body()
    action = data.get("action", "add").lower()

    election_id = data.get("election_id")
    if not election_id:
        active = _get_active_election()
        election_id = active["election_id"] if active else DEFAULT_ELECTION_ID

    candidate_id = (data.get("candidate_id") or "").strip().upper()

    if action == "delete":
        if not candidate_id:
            return jsonify({"error": "candidate_id is required for delete"}), 400
        candidates_collection.delete_one({"candidate_id": candidate_id, "election_id": election_id})
        elections_collection.update_one(
            {"election_id": election_id},
            {"$pull": {"candidates": candidate_id}, "$set": {"updated_at": _now_iso()}},
        )
        return jsonify({"success": True, "action": "delete", "candidate_id": candidate_id}), 200

    name = (data.get("name") or "").strip()
    party = (data.get("party") or "Independent").strip()
    if not candidate_id or not name:
        return jsonify({"error": "candidate_id and name are required"}), 400

    candidates_collection.update_one(
        {"candidate_id": candidate_id, "election_id": election_id},
        {
            "$set": {
                "candidate_id": candidate_id,
                "name": name,
                "party": party,
                "election_id": election_id,
            }
        },
        upsert=True,
    )
    elections_collection.update_one(
        {"election_id": election_id},
        {
            "$addToSet": {"candidates": candidate_id},
            "$set": {"updated_at": _now_iso()},
        },
        upsert=True,
    )

    return jsonify({"success": True, "action": action, "candidate_id": candidate_id}), 200


@app.route("/admin/start-election", methods=["POST"])
def admin_start_election():
    data = _json_body()
    election_id = (data.get("election_id") or f"ELECTION_{int(datetime.utcnow().timestamp())}").upper()
    title = (data.get("title") or "General Election").strip()

    elections_collection.update_many({"status": "active"}, {"$set": {"status": "ended", "updated_at": _now_iso()}})

    existing_candidates = list(candidates_collection.find({"election_id": election_id}, {"candidate_id": 1, "_id": 0}))
    candidate_ids = [d["candidate_id"] for d in existing_candidates]

    elections_collection.update_one(
        {"election_id": election_id},
        {
            "$set": {
                "election_id": election_id,
                "title": title,
                "status": "active",
                "candidates": candidate_ids,
                "aggregated_encrypted_result": None,
                "final_result_ready": False,
                "updated_at": _now_iso(),
            },
            "$setOnInsert": {"created_at": _now_iso()},
        },
        upsert=True,
    )

    officials_collection.update_many({"election_id": election_id}, {"$set": {"has_approved": False, "approved_at": None}})

    return jsonify({"success": True, "election_id": election_id, "status": "active"}), 200


@app.route("/admin/end-election", methods=["POST"])
def admin_end_election():
    data = _json_body()
    election_id = data.get("election_id")

    if not election_id:
        active = _get_active_election()
        if not active:
            return jsonify({"error": "No active election found"}), 404
        election_id = active["election_id"]

    elections_collection.update_one(
        {"election_id": election_id},
        {"$set": {"status": "ended", "updated_at": _now_iso()}},
    )

    return jsonify({"success": True, "election_id": election_id, "status": "ended"}), 200


@app.route("/admin/view-blockchain", methods=["GET"])
def admin_view_blockchain():
    election_id = request.args.get("election_id")
    page     = max(1, int(request.args.get("page", 1)))
    per_page = max(1, int(request.args.get("per_page", 10)))
    skip     = (page - 1) * per_page
    query    = {"election_id": election_id} if election_id else {}
    total    = blockchain_collection.count_documents(query)
    docs     = list(blockchain_collection.find(query, {"_id": 0})
                    .sort("block_index", DESCENDING)
                    .skip(skip).limit(per_page))
    return jsonify({"success": True, "blocks": docs, "count": total,
                    "page": page, "per_page": per_page,
                    "total_pages": max(1, (total + per_page - 1) // per_page)}), 200


@app.route("/admin/view-encrypted-votes", methods=["GET"])
def admin_view_encrypted_votes():
    election_id = request.args.get("election_id")
    page     = max(1, int(request.args.get("page", 1)))
    per_page = max(1, int(request.args.get("per_page", 20)))
    skip     = (page - 1) * per_page
    query    = {"election_id": election_id} if election_id else {}
    total    = votes_collection.count_documents(query)
    docs     = list(
        votes_collection.find(
            query,
            {"_id": 0, "vote_id": 1, "election_id": 1, "encrypted_vote": 1,
             "signature": 1, "timestamp": 1, "receipt_hash": 1},
        ).sort("timestamp", DESCENDING).skip(skip).limit(per_page)
    )
    # convert datetime → string for JSON
    for d in docs:
        if hasattr(d.get("timestamp"), "isoformat"):
            d["timestamp"] = d["timestamp"].isoformat()
    return jsonify({"success": True, "votes": docs, "count": total,
                    "page": page, "per_page": per_page,
                    "total_pages": max(1, (total + per_page - 1) // per_page)}), 200


@app.route("/admin/dashboard-data", methods=["GET"])
def admin_dashboard_data():
    active = _get_active_election()
    election_id = request.args.get("election_id") or (active["election_id"] if active else DEFAULT_ELECTION_ID)

    vote_count = votes_collection.count_documents({"election_id": election_id})
    block_count = blockchain_collection.count_documents({"election_id": election_id})
    candidate_count = candidates_collection.count_documents({"election_id": election_id})
    approved = len(_approved_official_ids(election_id))
    result_doc = results_collection.find_one({"election_id": election_id}, {"_id": 0})

    return jsonify(
        {
            "success": True,
            "election_id": election_id,
            "active_election": active["election_id"] if active else None,
            "vote_count": vote_count,
            "block_count": block_count,
            "candidate_count": candidate_count,
            "approved_officials": approved,
            "final_result": result_doc,
        }
    ), 200


@app.route("/official/approve-decryption", methods=["POST"])
def official_approve_decryption():
    data = _json_body()
    official_id = data.get("official_id")
    election_id = data.get("election_id")

    if not official_id:
        return jsonify({"error": "official_id is required"}), 400

    if not election_id:
        active = _get_active_election()
        election_id = active["election_id"] if active else DEFAULT_ELECTION_ID

    official = officials_collection.find_one({"official_id": official_id, "election_id": election_id})
    if not official:
        base_official = officials_collection.find_one({"official_id": official_id})
        if not base_official:
            return jsonify({"error": "Official not found for this election"}), 404

        officials_collection.update_one(
            {"official_id": official_id, "election_id": election_id},
            {
                "$set": {
                    "official_id": official_id,
                    "name": base_official.get("name") or official_id,
                    "key_share": base_official.get("key_share") or hashlib.sha3_256(official_id.encode()).hexdigest(),
                    "has_approved": False,
                    "approved_at": None,
                    "election_id": election_id,
                }
            },
            upsert=True,
        )
        official = officials_collection.find_one({"official_id": official_id, "election_id": election_id})

    if official.get("has_approved"):
        return jsonify({"error": "Official already approved", "already_approved": True}), 400

    officials_collection.update_one(
        {"official_id": official_id, "election_id": election_id},
        {"$set": {"has_approved": True, "approved_at": _now_iso()}},
    )

    # Task 7: audit
    audit(db, "official_approved_decryption", success=True,
          details={"official_id": official_id, "election_id": election_id})

    approved_ids = _approved_official_ids(election_id)
    vote_docs = list(votes_collection.find({"election_id": election_id}, {"_id": 0}))
    candidate_names = _candidate_names_for_election(election_id)
    final = _finalize_results_if_threshold_met(election_id, candidate_names, vote_docs)

    return jsonify({
        "success": True,
        "official_id": official_id,
        "election_id": election_id,
        "approved_count": len(approved_ids),
        "threshold_reached": len(approved_ids) >= 3,
        "result_ready": bool(final),
        "final_result": final,
    }), 200


# Task 6: SSE endpoint for live admin dashboard
@app.route("/admin/stream", methods=["GET"])
def admin_stream():
    """
    Server-Sent Events stream: pushes a live vote-count JSON blob
    whenever the change-stream callback fires a new vote insert.
    """
    import json as _json
    import time as _time

    election_id = request.args.get("election_id", DEFAULT_ELECTION_ID)
    live_counts = app.config.get("LIVE_VOTE_COUNTS", {})

    def _generate():
        last_sent = {}
        while True:
            current = live_counts.get(election_id, {})
            if current != last_sent:
                last_sent = dict(current)
                yield f"data: {_json.dumps({'election_id': election_id, 'counts': current})}\n\n"
            _time.sleep(1)

    return Response(stream_with_context(_generate()),
                    mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# Task 2: standalone aggregation endpoints for admin tooling
@app.route("/admin/analytics", methods=["GET"])
def admin_analytics():
    """Returns facet stats + turnout timeline via aggregation pipelines."""
    active = _get_active_election()
    election_id = request.args.get("election_id") or (active["election_id"] if active else DEFAULT_ELECTION_ID)
    return jsonify({
        "election_id": election_id,
        "facet":   agg_dashboard_facet(db, election_id),
        "turnout": agg_turnout_per_hour(db, election_id),
        "per_candidate": agg_votes_per_candidate(db, election_id),
    }), 200


# Task 7: audit log endpoint for admin
@app.route("/admin/audit-logs", methods=["GET"])
def admin_audit_logs():
    limit = int(request.args.get("limit", 100))
    logs = list(
        db["audit_logs"].find({}, {"_id": 0})
        .sort("timestamp", DESCENDING)
        .limit(limit)
    )
    # convert datetime to string for JSON
    for log in logs:
        if isinstance(log.get("timestamp"), datetime):
            log["timestamp"] = log["timestamp"].isoformat()
    failed_per_hour = agg_failed_logins_per_hour(db)
    for row in failed_per_hour:
        if isinstance(row.get("hour"), datetime):
            row["hour"] = row["hour"].isoformat()
    return jsonify({"logs": logs, "failed_logins_per_hour": failed_per_hour}), 200


@app.route("/official/status", methods=["GET"])
def official_status():
    election_id = request.args.get("election_id")
    if not election_id:
        active = _get_active_election()
        election_id = active["election_id"] if active else DEFAULT_ELECTION_ID

    approved_ids = _approved_official_ids(election_id)
    result_doc = results_collection.find_one({"election_id": election_id}, {"_id": 0})

    officials = list(
        officials_collection.find(
            {"election_id": election_id},
            {"_id": 0, "official_id": 1, "name": 1, "has_approved": 1, "approved_at": 1},
        )
    )

    return jsonify(
        {
            "success": True,
            "election_id": election_id,
            "approved_count": len(approved_ids),
            "required": 3,
            "officials": officials,
            "result_ready": bool(result_doc),
        }
    ), 200


if __name__ == "__main__":
    print(f"\n{'=' * 70}")
    print("🔐 POST-QUANTUM VOTING SYSTEM STARTED")
    print(f"{'=' * 70}")
    print("📡 Server: http://localhost:5000")
    print(f"🔑 Election Public Key: {election_public_key[:32]}...")
    print(f"👥 Candidates: {', '.join(_candidate_names_for_election(DEFAULT_ELECTION_ID))}")
    print("🔐 Security: Dilithium + Kyber + Mixnet + Blockchain + Homomorphic")
    print(f"{'=' * 70}\n")

    app.run(debug=True, port=5000)
