"""
MongoDB Features Module
Implements: schema validation, indexes, aggregation pipelines,
            ACID transactions, TTL collections, audit logging,
            change streams, GridFS, and performance story.
"""
import hashlib
import threading
from datetime import datetime, timezone

import certifi
import gridfs
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError, CollectionInvalid
from pymongo.write_concern import WriteConcern


# ---------------------------------------------------------------------------
# Schema validators
# ---------------------------------------------------------------------------

VOTER_USERS_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["aadhaar", "name", "dob", "password", "face_encoding", "role"],
        "properties": {
            "aadhaar":        {"bsonType": "string", "pattern": "^[0-9]{12}$",
                               "description": "12-digit Aadhaar number"},
            "name":           {"bsonType": "string", "minLength": 1},
            "dob":            {"bsonType": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"},
            "email":          {"bsonType": "string"},
            "role":           {"enum": ["voter"], "description": "Must be 'voter'"},
            "face_encoding":  {"bsonType": "array", "minItems": 128, "maxItems": 512,
                               "description": "Facenet embedding vector"},
            "registered_at":  {"bsonType": "date"},
        },
    }
}

VOTES_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["vote_id", "election_id", "voter_id_hash", "receipt_hash",
                     "candidate_id", "encrypted_vote", "timestamp"],
        "properties": {
            "vote_id":       {"bsonType": "string"},
            "election_id":   {"bsonType": "string"},
            "voter_id_hash": {"bsonType": "string", "minLength": 64, "maxLength": 64},
            "receipt_hash":  {"bsonType": "string", "minLength": 64, "maxLength": 64},
            "candidate_id":  {"bsonType": "string"},
            "encrypted_vote":{"bsonType": "string"},
            "timestamp":     {"bsonType": ["date", "string"]},
        },
    }
}

ELECTIONS_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["election_id", "status"],
        "properties": {
            "election_id": {"bsonType": "string"},
            "status":      {"enum": ["active", "ended"],
                            "description": "Must be active or ended"},
            "final_result_ready": {"bsonType": "bool"},
        },
    }
}

OFFICIALS_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["official_id", "has_approved"],
        "properties": {
            "official_id":  {"bsonType": "string"},
            "has_approved": {"bsonType": "bool"},
            "key_share":    {"bsonType": "string"},
            "election_id":  {"bsonType": "string"},
        },
    }
}

OFFICIAL_REQUESTS_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["aadhaar", "official_id", "status"],
        "properties": {
            "aadhaar":     {"bsonType": "string", "pattern": "^[0-9]{12}$"},
            "official_id": {"bsonType": "string"},
            "status":      {"enum": ["pending", "approved", "rejected"]},
        },
    }
}

OTP_SESSIONS_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["aadhaar", "otp_hash", "created_at"],
        "properties": {
            "aadhaar":    {"bsonType": "string", "pattern": "^[0-9]{12}$"},
            "otp_hash":   {"bsonType": "string"},
            "created_at": {"bsonType": "date"},
            "attempts":   {"bsonType": "int"},
        },
    }
}

AUDIT_LOGS_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["event", "timestamp"],
        "properties": {
            "event":      {"bsonType": "string"},
            "timestamp":  {"bsonType": "date"},
            "aadhaar":    {"bsonType": "string"},
            "success":    {"bsonType": "bool"},
            "details":    {"bsonType": "object"},
        },
    }
}


# ---------------------------------------------------------------------------
# Helper: create or patch collection with validator
# ---------------------------------------------------------------------------

def _ensure_collection(db, name: str, validator: dict):
    """Create collection with validator if missing, otherwise patch the validator."""
    existing = db.list_collection_names()
    if name not in existing:
        try:
            db.create_collection(name, validator=validator)
            print(f"  ✔ Created collection '{name}' with $jsonSchema validator")
        except CollectionInvalid:
            pass  # race condition - another process created it
    else:
        db.command("collMod", name, validator=validator, validationLevel="moderate")
        print(f"  ✔ Patched validator on '{name}'")


# ---------------------------------------------------------------------------
# Bootstrap: indexes + validators + TTL collections
# ---------------------------------------------------------------------------

def bootstrap_mongo_features(db, mongo_client):
    """
    Called once at server startup.
    Sets up all indexes, validators, and special collections.
    """
    print("\n[MongoDB] Bootstrapping features...")

    # ---- Schema validators ------------------------------------------------
    _ensure_collection(db, "voter_users",        VOTER_USERS_VALIDATOR)
    _ensure_collection(db, "votes",              VOTES_VALIDATOR)
    _ensure_collection(db, "elections",          ELECTIONS_VALIDATOR)
    _ensure_collection(db, "officials",          OFFICIALS_VALIDATOR)
    _ensure_collection(db, "official_requests",  OFFICIAL_REQUESTS_VALIDATOR)
    _ensure_collection(db, "otp_sessions",       OTP_SESSIONS_VALIDATOR)
    _ensure_collection(db, "audit_logs",         AUDIT_LOGS_VALIDATOR)

    # ---- Standard indexes -------------------------------------------------
    db["votes"].create_index("vote_id", unique=True)
    db["votes"].create_index([("election_id", ASCENDING), ("candidate_id", ASCENDING)])

    # Task 1: double-vote prevention — unique compound index
    db["votes"].create_index(
        [("voter_id_hash", ASCENDING), ("election_id", ASCENDING)],
        unique=True,
        name="unique_voter_per_election",
    )
    print("  ✔ [Task 1] Unique compound index voter_id_hash+election_id on votes")

    db["blockchain"].create_index("block_id", unique=True)
    db["candidates"].create_index([("candidate_id", ASCENDING), ("election_id", ASCENDING)], unique=True)
    db["elections"].create_index("election_id", unique=True)
    db["officials"].create_index([("official_id", ASCENDING), ("election_id", ASCENDING)], unique=True)

    # Task 10: additional performance indexes
    db["voter_users"].create_index("aadhaar", unique=True, name="unique_aadhaar")
    # Partial index: only approved officials (saves memory, speeds up threshold queries)
    db["officials"].create_index(
        [("election_id", ASCENDING), ("has_approved", ASCENDING)],
        partialFilterExpression={"has_approved": True},
        name="partial_approved_officials",
    )
    print("  ✔ [Task 10] Unique aadhaar index + partial approved-officials index")

    # ---- Task 5: OTP TTL index (auto-expire after 300 s) ------------------
    db["otp_sessions"].create_index("created_at", expireAfterSeconds=300, name="otp_ttl")
    print("  ✔ [Task 5] OTP TTL index (5-minute expiry)")

    # Failed-login lockout TTL (15 minutes)
    if "login_attempts" not in db.list_collection_names():
        db.create_collection("login_attempts")
    db["login_attempts"].create_index("created_at", expireAfterSeconds=900, name="login_attempts_ttl")
    print("  ✔ [Task 5] Login-attempts TTL index (15-minute window)")

    # Audit logs TTL (keep 90 days)
    db["audit_logs"].create_index("timestamp", expireAfterSeconds=7_776_000, name="audit_ttl")
    print("  ✔ [Task 7] Audit log TTL index (90-day retention)")

    # Task 8: GridFS metadata index for fast per-voter file lookups
    db["fs.files"].create_index("metadata.aadhaar", name="gridfs_aadhaar")
    print("  ✔ [Task 8] GridFS metadata.aadhaar index")

    # Task 2: $merge requires a unique index on the join fields in agg_results
    db["agg_results"].create_index(
        [("election_id", ASCENDING), ("candidate_id", ASCENDING)],
        unique=True,
        name="unique_agg_results",
    )
    print("  ✔ [Task 2] Unique index on agg_results (election_id, candidate_id)")

    print("[MongoDB] Bootstrap complete.\n")


# ---------------------------------------------------------------------------
# Task 1: Double-vote guard (wraps DuplicateKeyError)
# ---------------------------------------------------------------------------

def is_duplicate_vote_error(exc: Exception) -> bool:
    return isinstance(exc, DuplicateKeyError) and "unique_voter_per_election" in str(exc)


# ---------------------------------------------------------------------------
# Task 2: Aggregation pipelines
# ---------------------------------------------------------------------------

def agg_votes_per_candidate(db, election_id: str) -> list[dict]:
    """
    $group votes by candidate_id, $lookup candidate name, $sort descending.
    Returns: [{"candidate_id": "ALICE", "name": "Alice", "count": 12}, ...]
    """
    pipeline = [
        {"$match": {"election_id": election_id}},
        {"$group": {"_id": "$candidate_id", "count": {"$sum": 1}}},
        {
            "$lookup": {
                "from": "candidates",
                "localField": "_id",
                "foreignField": "candidate_id",
                "as": "cand",
            }
        },
        {
            "$project": {
                "candidate_id": "$_id",
                "count": 1,
                "name": {"$ifNull": [{"$arrayElemAt": ["$cand.name", 0]}, "$_id"]},
                "_id": 0,
            }
        },
        {"$sort": {"count": DESCENDING}},
    ]
    return list(db["votes"].aggregate(pipeline))


def agg_turnout_per_hour(db, election_id: str) -> list[dict]:
    """
    Votes per hour using $dateTrunc.
    Handles timestamp stored as either ISODate or string by converting with $toDate.
    Returns: [{"hour": <datetime>, "votes": 5}, ...]
    """
    pipeline = [
        {"$match": {"election_id": election_id}},
        {
            "$group": {
                "_id": {
                    "$dateTrunc": {
                        "date": {"$toDate": "$timestamp"},
                        "unit": "hour",
                    }
                },
                "votes": {"$sum": 1},
            }
        },
        {"$project": {"hour": "$_id", "votes": 1, "_id": 0}},
        {"$sort": {"hour": ASCENDING}},
    ]
    return list(db["votes"].aggregate(pipeline))


def agg_dashboard_facet(db, election_id: str) -> dict:
    """
    Single $facet aggregation returning multiple stats in one round-trip:
    - total votes
    - votes per candidate
    - votes per hour
    - approved official count
    """
    pipeline = [
        {"$match": {"election_id": election_id}},
        {
            "$facet": {
                "total": [{"$count": "n"}],
                "per_candidate": [
                    {"$group": {"_id": "$candidate_id", "count": {"$sum": 1}}},
                    {"$sort": {"count": DESCENDING}},
                ],
                "per_hour": [
                    {
                        "$group": {
                            "_id": {
                                "$dateTrunc": {
                                    "date": {"$toDate": "$timestamp"},
                                    "unit": "hour",
                                }
                            },
                            "votes": {"$sum": 1},
                        }
                    },
                    {"$sort": {"_id": ASCENDING}},
                ],
            }
        },
    ]
    results = list(db["votes"].aggregate(pipeline))
    if not results:
        return {"total": 0, "per_candidate": [], "per_hour": []}
    facet = results[0]
    return {
        "total": facet["total"][0]["n"] if facet["total"] else 0,
        "per_candidate": facet["per_candidate"],
        "per_hour": [
            {"hour": str(b["_id"]), "votes": b["votes"]} for b in facet["per_hour"]
        ],
    }


def agg_merge_results(db, election_id: str, candidate_names: list[str]):
    """
    Use $group + $merge to write aggregated results directly into the
    results collection — no Python counting loop needed.
    """
    pipeline = [
        {"$match": {"election_id": election_id, "candidate_id": {"$in": candidate_names}}},
        {"$group": {"_id": "$candidate_id", "vote_count": {"$sum": 1}}},
        {
            "$project": {
                "_id": 0,
                "election_id": {"$literal": election_id},
                "candidate_id": "$_id",
                "vote_count": 1,
            }
        },
        {
            "$merge": {
                "into": "agg_results",
                "on": ["election_id", "candidate_id"],
                "whenMatched": "replace",
                "whenNotMatched": "insert",
            }
        },
    ]
    db["votes"].aggregate(pipeline)
    return list(db["agg_results"].find({"election_id": election_id}, {"_id": 0}))


def agg_failed_logins_per_hour(db) -> list[dict]:
    """Audit pipeline: failed logins grouped by hour."""
    pipeline = [
        {"$match": {"event": "login_attempt", "success": False}},
        {
            "$group": {
                "_id": {
                    "$dateTrunc": {
                        "date": "$timestamp",
                        "unit": "hour",
                    }
                },
                "failures": {"$sum": 1},
            }
        },
        {"$project": {"hour": "$_id", "failures": 1, "_id": 0}},
        {"$sort": {"hour": ASCENDING}},
    ]
    return list(db["audit_logs"].aggregate(pipeline))


# ---------------------------------------------------------------------------
# Task 3: ACID transactions
# ---------------------------------------------------------------------------

def transactional_store_vote(mongo_client, db, vote_doc: dict, block_id: str, block_update: dict):
    """
    Atomically insert a vote and upsert the blockchain block.
    Uses a multi-document transaction with WriteConcern majority.
    """
    votes_wc = db.get_collection("votes", write_concern=WriteConcern("majority"))
    blockchain_wc = db.get_collection("blockchain", write_concern=WriteConcern("majority"))

    with mongo_client.start_session() as session:
        with session.start_transaction():
            votes_wc.insert_one(vote_doc, session=session)
            blockchain_wc.update_one(
                {"block_id": block_id},
                {"$set": block_update},
                upsert=True,
                session=session,
            )


def transactional_approve_official(mongo_client, db, request_id, auth_user_doc: dict, official_doc: dict):
    """
    Atomically: update official_requests → approved,
                insert into official_auth_users,
                insert/upsert into officials.
    """
    from bson import ObjectId

    requests_wc      = db.get_collection("official_requests",  write_concern=WriteConcern("majority"))
    auth_users_wc    = db.get_collection("official_auth_users", write_concern=WriteConcern("majority"))
    officials_wc     = db.get_collection("officials",           write_concern=WriteConcern("majority"))

    with mongo_client.start_session() as session:
        with session.start_transaction():
            requests_wc.update_one(
                {"_id": ObjectId(request_id)},
                {"$set": {"status": "approved", "reviewed_at": datetime.utcnow()}},
                session=session,
            )
            auth_users_wc.insert_one(auth_user_doc, session=session)
            officials_wc.update_one(
                {"official_id": official_doc["official_id"]},
                {"$setOnInsert": official_doc},
                upsert=True,
                session=session,
            )


# ---------------------------------------------------------------------------
# Task 5: OTP session helpers (hashed, TTL-backed)
# ---------------------------------------------------------------------------

def _hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode()).hexdigest()


def store_otp_session(db, aadhaar: str, otp: str):
    """Store hashed OTP with TTL. Replaces any existing session for this aadhaar."""
    db["otp_sessions"].delete_many({"aadhaar": aadhaar})
    db["otp_sessions"].insert_one({
        "aadhaar": aadhaar,
        "otp_hash": _hash_otp(otp),
        "created_at": datetime.utcnow(),
        "attempts": 0,
    })


def verify_otp_session(db, aadhaar: str, otp: str) -> tuple[bool, str]:
    """
    Returns (ok, reason).
    Increments attempt counter; locks after 5 failures.
    Deletes the session on success.
    """
    doc = db["otp_sessions"].find_one({"aadhaar": aadhaar})
    if not doc:
        return False, "OTP expired or not found"

    if doc.get("attempts", 0) >= 5:
        return False, "Too many attempts. Please log in again."

    if doc["otp_hash"] != _hash_otp(otp):
        db["otp_sessions"].update_one({"aadhaar": aadhaar}, {"$inc": {"attempts": 1}})
        return False, "Invalid OTP"

    db["otp_sessions"].delete_one({"aadhaar": aadhaar})
    return True, "ok"


# ---------------------------------------------------------------------------
# Task 5: Login-attempt lockout helpers
# ---------------------------------------------------------------------------

def record_login_attempt(db, aadhaar: str, success: bool, ip: str = ""):
    db["login_attempts"].insert_one({
        "aadhaar": aadhaar,
        "success": success,
        "ip": ip,
        "created_at": datetime.utcnow(),
    })


def is_account_locked(db, aadhaar: str, max_failures: int = 5) -> bool:
    """True if >=max_failures failed attempts in the TTL window (15 min)."""
    count = db["login_attempts"].count_documents({"aadhaar": aadhaar, "success": False})
    return count >= max_failures


# ---------------------------------------------------------------------------
# Task 7: Audit log helpers
# ---------------------------------------------------------------------------

def audit(db, event: str, aadhaar: str = "", success: bool = True, details: dict = None):
    """Write a structured audit log entry."""
    db["audit_logs"].insert_one({
        "event": event,
        "aadhaar": aadhaar,
        "success": success,
        "details": details or {},
        "timestamp": datetime.utcnow(),
    })


# ---------------------------------------------------------------------------
# Task 6: Change streams
# ---------------------------------------------------------------------------

_stream_callbacks: list = []


def register_stream_callback(fn):
    """Register a function to be called with each new vote document."""
    _stream_callbacks.append(fn)


def start_vote_change_stream(db):
    """
    Background thread watching votes collection for inserts.
    Calls all registered callbacks with the new document.
    """
    def _watch():
        try:
            pipeline = [{"$match": {"operationType": "insert"}}]
            with db["votes"].watch(pipeline, full_document="updateLookup") as stream:
                print("[MongoDB] Change stream watching votes...")
                for change in stream:
                    doc = change.get("fullDocument", {})
                    for cb in _stream_callbacks:
                        try:
                            cb(doc)
                        except Exception:
                            pass
        except Exception as e:
            print(f"[MongoDB] Change stream ended: {e}")

    t = threading.Thread(target=_watch, daemon=True)
    t.start()
    return t


# ---------------------------------------------------------------------------
# Task 8: GridFS helpers
# ---------------------------------------------------------------------------

def store_file_gridfs(db, data: bytes, filename: str, metadata: dict = None):
    """Store bytes in GridFS, return the file_id."""
    fs = gridfs.GridFS(db)
    file_id = fs.put(data, filename=filename, metadata=metadata or {})
    return file_id


def retrieve_file_gridfs(db, file_id) -> bytes | None:
    """Retrieve file bytes from GridFS by file_id."""
    fs = gridfs.GridFS(db)
    try:
        return fs.get(file_id).read()
    except gridfs.errors.NoFile:
        return None


def list_voter_files_gridfs(db, aadhaar: str) -> list[dict]:
    """
    Return all GridFS file metadata for a given aadhaar.
    Searches fs.files by metadata.aadhaar.
    Returns list of dicts: {file_id, filename, length, upload_date, type}
    """
    cursor = db["fs.files"].find(
        {"metadata.aadhaar": aadhaar},
        {"_id": 1, "filename": 1, "length": 1, "uploadDate": 1, "metadata": 1},
    ).sort("uploadDate", DESCENDING)

    results = []
    for doc in cursor:
        results.append({
            "file_id":     str(doc["_id"]),
            "filename":    doc.get("filename", ""),
            "length":      doc.get("length", 0),
            "upload_date": doc["uploadDate"].isoformat() if doc.get("uploadDate") else "",
            "type":        doc.get("metadata", {}).get("type", "unknown"),
        })
    return results


# ---------------------------------------------------------------------------
# Task 10: Performance story — explain helper
# ---------------------------------------------------------------------------

def log_explain_stats(db, collection_name: str, query_filter: dict, label: str = ""):
    """
    Run explain("executionStats") and print COLLSCAN vs IXSCAN summary.
    Call this before and after adding an index to generate the comparison.
    """
    try:
        plan = db[collection_name].find(query_filter).explain("executionStats")
        stats = plan.get("executionStats", {})
        stage = plan.get("queryPlanner", {}).get("winningPlan", {}).get("stage", "UNKNOWN")
        examined = stats.get("totalDocsExamined", "?")
        returned = stats.get("nReturned", "?")
        ms = stats.get("executionTimeMillis", "?")
        print(
            f"  [explain] {label or collection_name} | stage={stage} "
            f"| docsExamined={examined} | returned={returned} | {ms}ms"
        )
        return plan
    except Exception as e:
        print(f"  [explain] Could not run explain on {collection_name}: {e}")
        return {}


# ---------------------------------------------------------------------------
# Task 11: Legacy users → voter_users migration
# ---------------------------------------------------------------------------

def migrate_legacy_users(db):
    """
    One-shot migration: copy voter documents from the legacy `users`
    collection into `voter_users` using $merge (no data loss).
    Skips if legacy collection is empty.
    """
    count = db["users"].count_documents({"role": "voter"})
    if count == 0:
        return

    print(f"[Migration] Migrating {count} legacy voter documents → voter_users")
    pipeline = [
        {"$match": {"role": "voter"}},
        {
            "$merge": {
                "into": "voter_users",
                "on": "aadhaar",
                "whenMatched": "keepExisting",   # don't overwrite newer records
                "whenNotMatched": "insert",
            }
        },
    ]
    db["users"].aggregate(pipeline)
    print("[Migration] Done. Legacy voter_users migrated.")


# ---------------------------------------------------------------------------
# Task 9: Security cleanup — remove redundant key fields
# ---------------------------------------------------------------------------

def cleanup_officials_key_shares(db):
    """
    Remove redundant 'secret_key' field from officials collection.
    Keep only 'key_share' for threshold decryption.
    This ensures no duplicate or legacy key material remains in the collection.
    """
    try:
        result = db["officials"].update_many(
            {"secret_key": {"$exists": True}},
            {"$unset": {"secret_key": ""}}
        )
        if result.modified_count > 0:
            print(f"  ✔ [Task 9] Removed {result.modified_count} redundant 'secret_key' fields from officials")
        return result.modified_count
    except Exception as e:
        print(f"  ⚠ [Task 9] Could not cleanup officials key shares: {e}")
        return 0
