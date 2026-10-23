# ⚡ Quick Start Guide

## 1. Start Servers

```bash
# Terminal 1 - Backend (Port 5000)
python voting_system_crypto/backend/server.py

# Terminal 2 - Frontend (Port 8000)  
python app.py
```

## 2. Complete Flow

### Admin (Port 8000)
1. `/admin/register` → admin / Admin@123
2. `/admin/login` → Login
3. Add candidates: ALICE, BOB, CHARLIE
4. Click "Start Election"

### Voter (Port 8000)
1. `/register` → Aadhaar: 123456789012, capture face
2. `/login` → Face verify → OTP from email
3. Vote for candidate → Download receipt

### Officials (Port 8000)
1. Register 3 officials (OFFICIAL_1, OFFICIAL_2, OFFICIAL_3)
2. Admin approves all 3
3. Each official logs in and approves decryption
4. Admin triggers counting → View results

## 3. MongoDB Quick Check

```javascript
use evoting_db

// Check votes
db.votes.countDocuments({})

// Check no double-voting
db.votes.aggregate([
  { $group: { _id: "$voter_id_hash", count: { $sum: 1 } } },
  { $match: { count: { $gt: 1 } } }
])

// Check OTP security
db.otp_sessions.findOne()  // otp_hash should be 64-char hex

// Check officials cleanup
db.officials.countDocuments({ secret_key: { $exists: true } })  // Should be 0

// Check GridFS files
db.fs.files.countDocuments({ "metadata.aadhaar": "123456789012" })  // Should be 2

// Check blockchain integrity
db.votes.countDocuments({}) == db.blockchain.countDocuments({})  // Should be true
```

## 4. Test Features

### Task 1: Double-Vote Prevention
- Vote once → Logout → Login → Vote again
- Should get "already voted" error ✅

### Task 5: OTP Security
```javascript
db.otp_sessions.find()
// otp_hash = SHA-256 (64 chars), NOT plaintext ✅
```

### Task 5: Login Lockout
- Wrong password 5 times → Account locked ✅

### Task 8: GridFS Images
- Admin Dashboard → GridFS Images → Enter aadhaar
- Should show face photo + aadhaar card ✅

### Task 9: Key Cleanup
```javascript
db.officials.find({ secret_key: { $exists: true } })
// Should return empty ✅
```

## 5. Admin Features

| Feature | URL | What to Check |
|---------|-----|---------------|
| Blockchain | `/admin/view-blockchain` | Block linkage, pagination |
| Encrypted Votes | `/admin/view-encrypted-votes` | Truncated data, hashes |
| Audit Logs | `/admin/audit-logs-ui` | Events, failed logins chart |
| GridFS Images | `/admin/gridfs-images` | Face photos, aadhaar cards |

## 6. Reset System

```javascript
use evoting_db
db.votes.deleteMany({})
db.blockchain.deleteMany({})
db.voter_users.deleteMany({})
db.officials.deleteMany({})
db.official_requests.deleteMany({})
db.official_auth_users.deleteMany({})
db.otp_sessions.deleteMany({})
db.login_attempts.deleteMany({})
db.audit_logs.deleteMany({})
db.fs.files.deleteMany({})
db.fs.chunks.deleteMany({})
db.elections.updateOne(
  { election_id: "2024_GENERAL" },
  { $set: { status: "active", final_result_ready: false } }
)
```

## 7. Environment Setup

```env
FLASK_SECRET_KEY=your_secret_key
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/
SENDER_EMAIL=your@gmail.com
SENDER_PASSWORD=gmail_app_password
ELECTION_API_URL=http://localhost:5000
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
ELECTION_DB_NAME=evoting_db
```

## 8. Troubleshooting

| Issue | Fix |
|-------|-----|
| Backend won't start | Check MONGO_URI, IP whitelist in Atlas |
| Frontend won't start | Install Tesseract OCR |
| Face not recognized | Good lighting, face camera directly |
| OTP not received | Use Gmail App Password, check spam |
| Double-vote error | Expected! Reset election to test again |
| Counting fails | Need 3 officials approved + decryption approved |

## Documentation

- **Full Guide**: EXECUTION_GUIDE.md
- **Security**: MONGODB_SECURITY.md  
- **Tasks**: MONGODB_TASKS.md
- **Summary**: TASK_8_9_COMPLETION_SUMMARY.md

---

**Status**: All Tasks 1-9 Complete (100%) ✅
