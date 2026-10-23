# 🚀 E-Voting System - Complete Execution Guide

## System Architecture

### Two-Server Architecture

**Backend Server (server.py)** - Port 5000
- Vote processing & counting
- Blockchain operations
- Cryptographic operations
- RESTful API

**Frontend Server (app.py)** - Port 8000
- Voter registration & login
- Face recognition & OTP
- Admin dashboard
- Official management
- Web UI

---

## Quick Start

### 1. Install Dependencies

```bash
cd secure_e_voting_system
pip install -r requirements.txt
```

Install Tesseract OCR:
- Windows: https://github.com/UB-Mannheim/tesseract/wiki
- Mac: `brew install tesseract`
- Linux: `sudo apt-get install tesseract-ocr`

### 2. Configure Environment

Edit `.env` file:
```env
FLASK_SECRET_KEY=your_secret_key_here
MONGO_URI=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your_gmail_app_password
ELECTION_API_URL=http://localhost:5000
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
ELECTION_DB_NAME=evoting_db
```

### 3. Start Both Servers

**Terminal 1 - Backend Server:**
```bash
python voting_system_crypto/backend/server.py
```

**Terminal 2 - Frontend Server:**
```bash
python app.py
```

### 4. Access the System

- Frontend: http://localhost:8000
- Backend API: http://localhost:5000

---

## Complete Testing Flow

### Phase 1: Admin Setup

1. **Register Admin** → http://localhost:8000/admin/register
   - Username: admin
   - Password: Admin@123

2. **Login as Admin** → http://localhost:8000/admin/login

3. **Add Candidates** (Admin Dashboard)
   - ALICE - Alice Johnson
   - BOB - Bob Smith
   - CHARLIE - Charlie Brown

4. **Start Election** (Click button in dashboard)

### Phase 2: Voter Registration & Voting

1. **Register Voter** → http://localhost:8000/register
   - Aadhaar: 123456789012 (12 digits)
   - Name: John Doe
   - DOB: 1995-05-15
   - Email: voter1@example.com
   - Password: Voter@123
   - Capture face photo (webcam)
   - Upload Aadhaar card image

2. **Login** → http://localhost:8000/login
   - Enter Aadhaar & Password
   - Face verification (webcam)
   - Enter OTP from email

3. **Cast Vote**
   - Select candidate
   - Submit vote
   - Download receipt

### Phase 3: Official Approval & Counting

1. **Register 3 Officials**
   - Official 1: Aadhaar 111111111111, ID: OFFICIAL_1, Password: Official@123
   - Official 2: Aadhaar 222222222222, ID: OFFICIAL_2, Password: Official@123
   - Official 3: Aadhaar 333333333333, ID: OFFICIAL_3, Password: Official@123

2. **Admin Approves Officials**
   - Admin Dashboard → Manage Officials
   - Approve each official

3. **Officials Approve Decryption**
   - Each official logs in
   - Clicks "Approve Decryption" button

4. **Admin Triggers Counting**
   - Admin Dashboard → Trigger Vote Counting
   - View results

5. **End Election**
   - Click "End Election" button

---

## MongoDB Data Verification

### Connect to MongoDB

**Option 1: MongoDB Compass**
- Download from: https://www.mongodb.com/products/compass
- Connect with your MONGO_URI
- Select database: evoting_db

**Option 2: mongosh**
```bash
mongosh "mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/"
use evoting_db
```

### Collections to Check

#### 1. voter_users
```javascript
db.voter_users.find().pretty()
```
Check:
- aadhaar: 12-digit string
- password: hashed with $2b$
- face_encoding: array of 128-512 floats
- face_grid_id: ObjectId reference to GridFS
- role: "voter"

#### 2. votes
```javascript
db.votes.find().pretty()
```
Check:
- voter_id_hash: 64-char SHA-256
- receipt_hash: 64-char SHA-256
- timestamp: ISODate object (not string!)
- encrypted_vote: base64 string
- No duplicate (voter_id_hash, election_id)

**Double-vote test:**
```javascript
db.votes.aggregate([
  { $group: { _id: "$voter_id_hash", count: { $sum: 1 } } },
  { $match: { count: { $gt: 1 } } }
])
// Should return empty (no duplicates)
```

#### 3. blockchain
```javascript
db.blockchain.find().sort({ block_id: 1 }).pretty()
```
Check:
- Sequential block_ids: block_0, block_1, block_2...
- previous_hash links to prior block's vote_hash
- First block has previous_hash = "0000000..."

**Blockchain integrity test:**
```javascript
var blocks = db.blockchain.find().sort({ block_id: 1 }).toArray();
for (var i = 1; i < blocks.length; i++) {
  if (blocks[i].previous_hash !== blocks[i-1].vote_hash) {
    print("CHAIN BROKEN at block " + blocks[i].block_id);
  }
}
print("Blockchain integrity: OK");
```

#### 4. candidates
```javascript
db.candidates.find().pretty()
```
Check: All 3 candidates present (ALICE, BOB, CHARLIE)

#### 5. elections
```javascript
db.elections.find().pretty()
```
Check:
- status: "active" or "ended"
- final_result_ready: true after counting

#### 6. officials
```javascript
db.officials.find().pretty()
```
Check:
- has_approved: true after officials approve
- key_share: base64 threshold key share
- NO "secret_key" field (cleaned by Task 9)

**Cleanup verification:**
```javascript
db.officials.countDocuments({ secret_key: { $exists: true } })
// Should return 0
```

#### 7. official_requests
```javascript
db.official_requests.find().pretty()
```
Check:
- status: "approved" after admin approval
- reviewed_at: set when approved

#### 8. otp_sessions (Task 5 - TTL)
```javascript
db.otp_sessions.find().pretty()
```
Check:
- otp_hash: 64-char SHA-256 (NEVER plaintext!)
- created_at: ISODate
- attempts: counter for failed OTP entries
- TTL: Auto-deletes after 5 minutes

**TTL verification:**
```javascript
db.otp_sessions.getIndexes()
// Should show: expireAfterSeconds: 300
```

#### 9. login_attempts (Task 5 - Lockout)
```javascript
db.login_attempts.find().pretty()
```
Check:
- success: false for failed attempts
- TTL: Auto-deletes after 15 minutes

**Lockout test:**
```javascript
db.login_attempts.countDocuments({
  aadhaar: "123456789012",
  success: false
})
// If >= 5, account is locked
```

#### 10. audit_logs (Task 7)
```javascript
db.audit_logs.find().sort({ timestamp: -1 }).limit(10).pretty()
```
Check:
- Events: voter_registered, login_success, vote_submitted, double_vote_attempt
- TTL: 90-day retention (7,776,000 seconds)

**Failed logins per hour:**
```javascript
db.audit_logs.aggregate([
  { $match: { event: "login_attempt", success: false } },
  {
    $group: {
      _id: { $dateTrunc: { date: "$timestamp", unit: "hour" } },
      failures: { $sum: 1 }
    }
  },
  { $sort: { _id: 1 } }
])
```

#### 11. fs.files & fs.chunks (Task 8 - GridFS)
```javascript
db.fs.files.find().pretty()
```
Check:
- metadata.aadhaar: voter's aadhaar
- metadata.type: "image/jpeg" or "image/png"
- Two files per voter: face photo + aadhaar card

**Index verification:**
```javascript
db.fs.files.getIndexes()
// Should show: gridfs_aadhaar index on metadata.aadhaar
```

**List voter's files:**
```javascript
db.fs.files.find({ "metadata.aadhaar": "123456789012" })
```

#### 12. agg_results (Task 2)
```javascript
db.agg_results.find().pretty()
```
Check: Vote counts per candidate (created by $merge pipeline)

---

## Test Aggregation Pipelines (Task 2)

### Votes Per Candidate
```javascript
db.votes.aggregate([
  { $match: { election_id: "2024_GENERAL" } },
  { $group: { _id: "$candidate_id", count: { $sum: 1 } } },
  {
    $lookup: {
      from: "candidates",
      localField: "_id",
      foreignField: "candidate_id",
      as: "cand"
    }
  },
  {
    $project: {
      candidate_id: "$_id",
      count: 1,
      name: { $arrayElemAt: ["$cand.name", 0] },
      _id: 0
    }
  },
  { $sort: { count: -1 } }
])
```

### Turnout Per Hour
```javascript
db.votes.aggregate([
  { $match: { election_id: "2024_GENERAL" } },
  {
    $group: {
      _id: {
        $dateTrunc: {
          date: { $toDate: "$timestamp" },
          unit: "hour"
        }
      },
      votes: { $sum: 1 }
    }
  },
  { $project: { hour: "$_id", votes: 1, _id: 0 } },
  { $sort: { hour: 1 } }
])
```

---

## Test ACID Transactions (Task 3)

```javascript
// Verify vote count matches blockchain count
db.votes.countDocuments({})
db.blockchain.countDocuments({})
// Should be equal

// Check for orphaned votes (votes without blockchain entry)
db.votes.aggregate([
  {
    $lookup: {
      from: "blockchain",
      let: { vote_id: "$vote_id" },
      pipeline: [
        { $match: { $expr: { $regexMatch: { input: "$vote_hash", regex: "$$vote_id" } } } }
      ],
      as: "block"
    }
  },
  { $match: { block: { $size: 0 } } }
])
// Should return empty array
```

---

## Admin Features to Test

### 1. View Blockchain
- Admin Dashboard → View Blockchain
- Check: Block cards, pagination, hash linkage

### 2. View Encrypted Votes
- Admin Dashboard → View Encrypted Votes
- Check: Table with truncated encrypted data, pagination

### 3. Audit Logs
- Admin Dashboard → Audit Logs
- Check: Event list, failed logins chart

### 4. GridFS Images (Task 8)
- Admin Dashboard → GridFS Images
- Enter aadhaar: 123456789012
- Check: Face photo & aadhaar card images display
- Click "View Full Size" to download

---

## Troubleshooting

### Backend Won't Start
- Check MONGO_URI in .env
- Verify MongoDB Atlas cluster is running
- Check IP whitelist in Atlas (add your IP)

### Frontend Won't Start
- Install Tesseract OCR
- Set TESSERACT_CMD in .env

### Face Recognition Fails
- Ensure good lighting
- Face camera directly
- Use same device for registration and login

### OTP Not Received
- Check SENDER_EMAIL and SENDER_PASSWORD
- Use Gmail App Password (not regular password)
- Check spam folder

### Double-Vote Error
- Expected! Unique index prevents double-voting
- Reset election or use different voter

### Vote Counting Fails
- Ensure 3 officials registered and approved
- Each official must login and approve decryption
- Check: `db.officials.countDocuments({ has_approved: true })`

---

## Security Tests

### 1. Double-Vote Prevention
- Login and vote
- Logout and login again
- Try voting again → Should fail with "already voted" error

### 2. OTP Security
```javascript
db.otp_sessions.findOne()
// otp_hash should be 64-char hex (SHA-256)
// NEVER plaintext like "123456"
```

### 3. Login Lockout
- Try wrong password 5 times
- Should get "Account locked" error
- Check: `db.login_attempts.countDocuments({ success: false })`

### 4. TTL Expiration
- Create OTP session
- Wait 6 minutes
- Check: `db.otp_sessions.countDocuments({})` should be 0

---

## Complete System Reset

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
db.agg_results.deleteMany({})
db.fs.files.deleteMany({})
db.fs.chunks.deleteMany({})

db.elections.updateOne(
  { election_id: "2024_GENERAL" },
  { $set: { status: "active", final_result_ready: false } }
)

print("System reset complete!")
```

---

## Summary Checklist

✅ **Installation**
- [ ] Python 3.9+ installed
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Tesseract OCR installed
- [ ] MongoDB Atlas cluster configured
- [ ] .env file configured

✅ **System Startup**
- [ ] Backend server running on port 5000
- [ ] Frontend server running on port 8000
- [ ] Both terminals showing no errors

✅ **Admin Setup**
- [ ] Admin registered and logged in
- [ ] 3 candidates added
- [ ] Election started

✅ **Voter Flow**
- [ ] Voter registered with face photo
- [ ] Voter logged in with face verification
- [ ] OTP received and verified
- [ ] Vote cast successfully
- [ ] Receipt downloaded

✅ **Official Flow**
- [ ] 3 officials registered
- [ ] Admin approved all 3 officials
- [ ] All 3 officials approved decryption
- [ ] Vote counting completed
- [ ] Results displayed

✅ **MongoDB Verification**
- [ ] voter_users: password hashed, face_encoding array exists
- [ ] votes: no duplicates, timestamp is ISODate
- [ ] blockchain: chain integrity verified
- [ ] officials: no secret_key field (cleaned)
- [ ] otp_sessions: OTP is hashed (not plaintext)
- [ ] audit_logs: events logged correctly
- [ ] fs.files: GridFS images stored with metadata
- [ ] All indexes present and correct

✅ **Feature Testing**
- [ ] Double-vote prevention works
- [ ] Login lockout after 5 failed attempts
- [ ] OTP expires after 5 minutes
- [ ] Audit logs retained for 90 days
- [ ] GridFS images viewable in admin UI
- [ ] Aggregation pipelines return correct data
- [ ] ACID transactions maintain data consistency
- [ ] Change streams update live dashboard

---

**For detailed security documentation, see:**
- MONGODB_SECURITY.md
- MONGODB_TASKS.md

**All code verified and ready for testing!** 🎉
