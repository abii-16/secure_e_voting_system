# MongoDB Security Implementation Guide

## Overview
This document outlines the MongoDB security features implemented in the secure e-voting system, including least-privilege access control, data encryption, and security best practices.

---

## 1. Separate Database Users (Least Privilege Principle)

### User Roles Architecture

The system uses **two separate MongoDB database users** with different privilege levels:

#### **App User** (`evoting_app_user`)
- **Purpose**: Handles voter registration, login, and authentication
- **Privileges**: Read/write access to voter-related collections
- **Collections**:
  - `voter_users` (read/write)
  - `otp_sessions` (read/write)
  - `login_attempts` (read/write)
  - `official_auth_users` (read/write)
  - `official_requests` (read/write)
  - `fs.files` and `fs.chunks` (read/write for GridFS)
- **No access to**: `votes`, `blockchain`, `agg_results`

#### **Server User** (`evoting_server_user`)
- **Purpose**: Handles vote submission, counting, and blockchain operations
- **Privileges**: Read/write access to voting and blockchain collections
- **Collections**:
  - `votes` (read/write)
  - `blockchain` (read/write)
  - `elections` (read/write)
  - `candidates` (read/write)
  - `officials` (read/write)
  - `agg_results` (read/write)
  - `audit_logs` (read/write)
- **Read-only access to**: `voter_users` (for voter verification)
- **No write access to**: voter registration or authentication collections

---

## 2. MongoDB Atlas Setup Instructions

### Step 1: Create Database Users

1. **Log into MongoDB Atlas**
   - Go to https://cloud.mongodb.com
   - Select your cluster

2. **Create App User** (for voter registration/login)
   ```
   Username: evoting_app_user
   Password: [generate strong password]
   Database: evoting_db
   ```
   
   **Privileges**:
   ```json
   {
     "db": "evoting_db",
     "privileges": [
       {
         "resource": { "db": "evoting_db", "collection": "voter_users" },
         "actions": ["find", "insert", "update", "remove"]
       },
       {
         "resource": { "db": "evoting_db", "collection": "otp_sessions" },
         "actions": ["find", "insert", "update", "remove"]
       },
       {
         "resource": { "db": "evoting_db", "collection": "login_attempts" },
         "actions": ["find", "insert", "update", "remove"]
       },
       {
         "resource": { "db": "evoting_db", "collection": "official_auth_users" },
         "actions": ["find", "insert", "update"]
       },
       {
         "resource": { "db": "evoting_db", "collection": "official_requests" },
         "actions": ["find", "insert", "update"]
       },
       {
         "resource": { "db": "evoting_db", "collection": "fs.files" },
         "actions": ["find", "insert", "update", "remove"]
       },
       {
         "resource": { "db": "evoting_db", "collection": "fs.chunks" },
         "actions": ["find", "insert", "update", "remove"]
       }
     ]
   }
   ```

3. **Create Server User** (for vote submission and counting)
   ```
   Username: evoting_server_user
   Password: [generate strong password]
   Database: evoting_db
   ```
   
   **Privileges**:
   ```json
   {
     "db": "evoting_db",
     "privileges": [
       {
         "resource": { "db": "evoting_db", "collection": "votes" },
         "actions": ["find", "insert", "update"]
       },
       {
         "resource": { "db": "evoting_db", "collection": "blockchain" },
         "actions": ["find", "insert", "update"]
       },
       {
         "resource": { "db": "evoting_db", "collection": "elections" },
         "actions": ["find", "insert", "update"]
       },
       {
         "resource": { "db": "evoting_db", "collection": "candidates" },
         "actions": ["find", "insert", "update"]
       },
       {
         "resource": { "db": "evoting_db", "collection": "officials" },
         "actions": ["find", "insert", "update"]
       },
       {
         "resource": { "db": "evoting_db", "collection": "agg_results" },
         "actions": ["find", "insert", "update"]
       },
       {
         "resource": { "db": "evoting_db", "collection": "audit_logs" },
         "actions": ["find", "insert"]
       },
       {
         "resource": { "db": "evoting_db", "collection": "voter_users" },
         "actions": ["find"]
       }
     ]
   }
   ```

### Step 2: Update Environment Configuration

Update your `.env` file with separate connection strings:

```env
# App.py MongoDB connection (voter registration/login)
MONGO_URI_APP=mongodb+srv://evoting_app_user:[APP_PASSWORD]@cluster0.29vglgs.mongodb.net/evoting_db

# Server.py MongoDB connection (vote submission/counting)
MONGO_URI_SERVER=mongodb+srv://evoting_server_user:[SERVER_PASSWORD]@cluster0.29vglgs.mongodb.net/evoting_db
```

### Step 3: Update Application Code

**In `app.py`**, update MongoDB connection:
```python
# Use app-specific connection string
MONGO_URI = os.getenv("MONGO_URI_APP", os.getenv("MONGO_URI"))
```

**In `voting_system_crypto/backend/server.py`**, update MongoDB connection:
```python
# Use server-specific connection string
MONGO_URI = os.getenv("MONGO_URI_SERVER", os.getenv("MONGO_URI"))
```

---

## 3. Data Encryption and Hashing

### Implemented Security Measures

#### ✅ OTP Hashing
- **Status**: IMPLEMENTED (Task 5)
- **Method**: SHA-256 hashing
- **Storage**: No plaintext OTPs stored in any collection
- **Implementation**: `store_otp_session()` in `mongo_features.py`

```python
def _hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode()).hexdigest()
```

#### ✅ Password Hashing
- **Status**: IMPLEMENTED
- **Method**: Werkzeug's `generate_password_hash()` with scrypt
- **Verification**: `check_password_hash()`
- **Collections**: `voter_users`, `official_auth_users`, `admin_auth_users`

#### ✅ Voter ID Anonymization
- **Status**: IMPLEMENTED
- **Method**: SHA-256(aadhaar + election_id)
- **Purpose**: Votes are linked to hashed voter IDs, not direct aadhaar numbers
- **Implementation**: `voter_id_hash` field in `votes` collection

#### ✅ GridFS Metadata Protection
- **Status**: IMPLEMENTED
- **Method**: Files indexed by aadhaar in metadata
- **Access Control**: Admin-only retrieval routes
- **Implementation**: GridFS storage with metadata in `mongo_features.py`

---

## 4. Field-Level Encryption (CSFLE) Approach

### Client-Side Field Level Encryption (CSFLE)

MongoDB CSFLE allows encrypting sensitive fields **before** they reach the database server.

#### Target Fields for CSFLE
1. **`voter_users.aadhaar`** - 12-digit national ID
2. **`voter_users.face_encoding`** - biometric data (128-512 element array)
3. **`voter_users.email`** - personal contact information
4. **`officials.key_share`** - cryptographic threshold key shares

#### Implementation Plan

**Prerequisites**:
- MongoDB Enterprise or Atlas M10+ cluster
- pymongo with pymongocrypt library
- Local or KMS encryption key management

**Step 1: Install Dependencies**
```bash
pip install 'pymongo[encryption]'
```

**Step 2: Generate Master Key**
```python
from pymongo.encryption import ClientEncryption
import os

# For development: local master key (96 bytes)
local_master_key = os.urandom(96)

# For production: AWS KMS, Azure Key Vault, or GCP KMS
kms_providers = {
    "local": {"key": local_master_key}
}
```

**Step 3: Create Data Encryption Keys**
```python
key_vault_namespace = "encryption.__keyVault"
client_encryption = ClientEncryption(
    kms_providers,
    key_vault_namespace,
    client,
    codec_options
)

# Create DEK for voter data
voter_data_key_id = client_encryption.create_data_key("local", key_alt_names=["voter_data_key"])
```

**Step 4: Define Encrypted Schema**
```python
from pymongo.encryption import Algorithm

encrypted_fields_map = {
    "evoting_db.voter_users": {
        "bsonType": "object",
        "encryptMetadata": {
            "keyId": [voter_data_key_id],
            "algorithm": Algorithm.AEAD_AES_256_CBC_HMAC_SHA_512_Deterministic
        },
        "properties": {
            "aadhaar": {
                "encrypt": {
                    "bsonType": "string",
                    "algorithm": Algorithm.AEAD_AES_256_CBC_HMAC_SHA_512_Deterministic
                }
            },
            "email": {
                "encrypt": {
                    "bsonType": "string",
                    "algorithm": Algorithm.AEAD_AES_256_CBC_HMAC_SHA_512_Random
                }
            }
        }
    }
}
```

**Step 5: Create Encrypted MongoClient**
```python
auto_encryption_opts = AutoEncryptionOpts(
    kms_providers,
    key_vault_namespace,
    schema_map=encrypted_fields_map,
    key_vault_client=key_vault_client
)

encrypted_client = MongoClient(
    MONGO_URI,
    auto_encryption_opts=auto_encryption_opts,
    tlsCAFile=certifi.where()
)
```

#### Deterministic vs Random Encryption

- **Deterministic**: Use for fields that need exact-match queries (e.g., `aadhaar` lookups)
- **Random**: Use for fields that don't need querying (e.g., `face_encoding`, `email`)

#### Key Management Options

**Development**: Local master key (stored securely in environment variable)
```python
kms_providers = {"local": {"key": base64.b64decode(os.getenv("MASTER_KEY"))}}
```

**Production**: Use managed KMS
```python
kms_providers = {
    "aws": {
        "accessKeyId": os.getenv("AWS_ACCESS_KEY_ID"),
        "secretAccessKey": os.getenv("AWS_SECRET_ACCESS_KEY"),
        "region": "us-east-1",
        "key": "arn:aws:kms:us-east-1:123456789:key/12345678-1234-1234-1234-123456789012"
    }
}
```

---

## 5. Queryable Encryption (QE)

### Overview
Queryable Encryption is MongoDB's next-generation encryption (Atlas 6.0+) that allows **range queries** on encrypted data.

#### Advantages over CSFLE
- Supports range queries (`$gt`, `$lt`, `$gte`, `$lte`)
- Supports prefix queries on strings
- Automatic key rotation
- Stronger security guarantees

#### Use Cases in E-Voting
1. **Age verification queries** without decrypting DOB
2. **Range-based analytics** on encrypted timestamps
3. **Encrypted audit log searches** with preserved functionality

#### Setup Requirements
- MongoDB Atlas 6.0+
- Queryable Encryption enabled on cluster
- Automatic Encryption Shared Library installed

**Reference**: https://www.mongodb.com/docs/manual/core/queryable-encryption/

---

## 6. Network and Connection Security

### TLS/SSL Enforcement
```python
mongo_client = MongoClient(
    MONGO_URI,
    tls=True,
    tlsCAFile=certifi.where(),
    tlsAllowInvalidCertificates=False  # Enforce valid certificates
)
```

### IP Allowlist (Atlas)
- Configure IP allowlist in Atlas dashboard
- Add application server IPs only
- Use VPC peering for production deployments

### Connection String Security
- Never commit `.env` files to version control
- Use environment variables for all credentials
- Rotate passwords quarterly
- Use strong passwords (16+ characters, mixed case, symbols)

---

## 7. Officials Collection Key Share Cleanup

### Current Issue
The `officials` collection may contain redundant fields:
- `secret_key` (legacy field)
- `key_share` (current field)

### Cleanup Script

```python
def cleanup_officials_key_shares(db):
    """
    Remove redundant 'secret_key' field from officials collection.
    Keep only 'key_share' for threshold decryption.
    """
    result = db["officials"].update_many(
        {"secret_key": {"$exists": True}},
        {"$unset": {"secret_key": ""}}
    )
    print(f"[Security Cleanup] Removed {result.modified_count} redundant 'secret_key' fields from officials")
    return result.modified_count
```

### Integration
Add this call to `bootstrap_mongo_features()` in `mongo_features.py`:
```python
# Task 9: Remove redundant key fields
cleanup_officials_key_shares(db)
```

---

## 8. Security Checklist

### ✅ Completed
- [x] OTP hashed with SHA-256 (no plaintext storage)
- [x] Password hashing with scrypt
- [x] Voter ID anonymization (SHA-256 hashing)
- [x] Separate collections for different data domains
- [x] Schema validation on all collections
- [x] GridFS file access control (admin only)
- [x] TLS/SSL enabled for MongoDB connections
- [x] Audit logging for security events
- [x] TTL indexes for OTP and login attempt expiration

### 📋 To Implement
- [ ] Separate DB users (app vs server) - **Requires Atlas configuration**
- [ ] CSFLE for aadhaar and face_encoding - **Requires Enterprise/Atlas M10+**
- [ ] `secret_key` field cleanup in officials collection
- [ ] Queryable Encryption evaluation - **Requires Atlas 6.0+**
- [ ] KMS integration for production key management
- [ ] IP allowlist configuration in Atlas
- [ ] Regular password rotation policy
- [ ] Security audit and penetration testing

---

## 9. Additional Security Recommendations

### Application-Level
1. **Rate Limiting**: Implement rate limiting on login endpoints (Flask-Limiter)
2. **CSRF Protection**: Enable Flask-WTF CSRF tokens
3. **Session Security**: Use secure, httpOnly cookies
4. **Input Validation**: Validate all user inputs (aadhaar format, etc.)

### Database-Level
1. **Backup Encryption**: Enable encryption at rest for Atlas backups
2. **Point-in-Time Recovery**: Enable continuous backups
3. **Database Auditing**: Enable Atlas database auditing for compliance
4. **Monitoring**: Set up alerts for suspicious query patterns

### Infrastructure-Level
1. **VPC Peering**: Use private network connections (not public internet)
2. **Firewall Rules**: Restrict MongoDB port (27017) to application servers only
3. **Secrets Management**: Use HashiCorp Vault or AWS Secrets Manager
4. **Log Analysis**: Implement SIEM for security log analysis

---

## 10. Testing Security Features

### Test OTP Hashing
```python
from voting_system_crypto.backend.mongo_features import store_otp_session, verify_otp_session

# Store OTP
store_otp_session(db, "123456789012", "123456")

# Verify correct OTP
ok, msg = verify_otp_session(db, "123456789012", "123456")
assert ok == True

# Verify wrong OTP
ok, msg = verify_otp_session(db, "123456789012", "999999")
assert ok == False
```

### Test Login Lockout
```python
from voting_system_crypto.backend.mongo_features import record_login_attempt, is_account_locked

aadhaar = "123456789012"

# Simulate 5 failed attempts
for _ in range(5):
    record_login_attempt(db, aadhaar, success=False, ip="192.168.1.1")

# Check if locked
assert is_account_locked(db, aadhaar) == True
```

### Test Separate User Access
```bash
# Test app user (should succeed)
mongosh "mongodb+srv://evoting_app_user:[PASSWORD]@cluster0.29vglgs.mongodb.net/evoting_db" \
  --eval "db.voter_users.findOne()"

# Test app user trying to access votes (should fail)
mongosh "mongodb+srv://evoting_app_user:[PASSWORD]@cluster0.29vglgs.mongodb.net/evoting_db" \
  --eval "db.votes.findOne()"  # Unauthorized

# Test server user (should succeed)
mongosh "mongodb+srv://evoting_server_user:[PASSWORD]@cluster0.29vglgs.mongodb.net/evoting_db" \
  --eval "db.votes.findOne()"
```

---

## References

- [MongoDB Security Checklist](https://www.mongodb.com/docs/manual/administration/security-checklist/)
- [Client-Side Field Level Encryption](https://www.mongodb.com/docs/manual/core/csfle/)
- [Queryable Encryption](https://www.mongodb.com/docs/manual/core/queryable-encryption/)
- [MongoDB Atlas Security](https://www.mongodb.com/docs/atlas/security/)
- [Python CSFLE Example](https://pymongo.readthedocs.io/en/stable/examples/encryption.html)

---

## Maintenance

**Last Updated**: October 2026  
**Next Review**: Quarterly security audit  
**Contact**: Security team for production deployment guidance
