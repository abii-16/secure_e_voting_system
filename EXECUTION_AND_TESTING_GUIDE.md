a complete understanding of:
1. ✅ How to start both servers
2. ✅ Complete testing flow (admin → voter → official → counting)
3. ✅ MongoDB data verification for all 14 collections
4. ✅ All MongoDB features (Tasks 1-9) verification
5. ✅ Troubleshooting common issues
6. ✅ Security testing procedures

**Need Help?**
- Check terminal logs for detailed error messages
- Review MONGODB_TASKS.md for feature details
- See MONGODB_SECURITY.md for security setup
- Check audit_logs collection for event history

Happy testing! 🎉
hex(32)`)
- [ ] Set up separate MongoDB users (see MONGODB_SECURITY.md)
- [ ] Enable MongoDB encryption at rest
- [ ] Configure IP whitelist in Atlas
- [ ] Set up TLS/SSL certificates for Flask
- [ ] Use production WSGI server (Gunicorn/uWSGI, not Flask dev server)
- [ ] Enable rate limiting (Flask-Limiter)
- [ ] Set up monitoring and alerting
- [ ] Configure backup strategy
- [ ] Perform security audit and penetration testing
- [ ] Review MONGODB_SECURITY.md for CSFLE setup

---

## Conclusion

You now have fficial_auth_users.deleteMany({})
db.otp_sessions.deleteMany({})
db.login_attempts.deleteMany({})
db.audit_logs.deleteMany({})
db.agg_results.deleteMany({})
db.fs.files.deleteMany({})
db.fs.chunks.deleteMany({})

// Reset election status
db.elections.updateOne(
  { election_id: "2024_GENERAL" },
  { $set: { status: "active", final_result_ready: false } }
)

print("System reset complete!")
```

---

## Production Deployment Checklist

Before deploying to production:

- [ ] Change FLASK_SECRET_KEY (use `secrets.token_Queries | <500ms |

### Load Testing

```bash
# Install Apache Bench
apt-get install apache2-utils  # Linux
brew install httpd             # Mac

# Test vote endpoint
ab -n 100 -c 10 -p vote.json -T application/json http://localhost:5000/vote
```

---

## Cleanup and Reset

### Reset Entire System

```javascript
// WARNING: Deletes all data!

use evoting_db

db.votes.deleteMany({})
db.blockchain.deleteMany({})
db.voter_users.deleteMany({})
db.officials.deleteMany({})
db.official_requests.deleteMany({})
db.opt
db.audit_logs.find({ event: "vote_submitted" }).count()
db.audit_logs.find({ event: "login_success" }).count()
db.audit_logs.find({ event: "double_vote_attempt" }).count()
```

---

## Performance Benchmarks

### Expected Performance

| Operation | Expected Time |
|-----------|---------------|
| Voter Registration | 2-5 seconds |
| Face Verification | 1-3 seconds |
| Vote Submission | 0.5-1 second |
| Vote Counting (100 votes) | 5-10 seconds |
| Blockchain Verification | <100ms per block |
| Aggregation ected**: "Account locked" error
4. **MongoDB**: Check login_attempts collection

```javascript
db.login_attempts.countDocuments({
  aadhaar: "123456789012",
  success: false
})
// Should show 5 attempts
```

---

### 4. Test TTL Expiration (Task 5)

```javascript
// Create OTP session
// Wait 6 minutes
// Check if auto-deleted
db.otp_sessions.countDocuments({})
// Should be 0 after 5 minutes + 1 minute cleanup window
```

---

### 5. Test Audit Logging (Task 7)

Check audit trail for key events:
```javascricted**: "You have already voted" error
5. **MongoDB**: Check unique index prevented duplicate

---

### 2. Test OTP Hashing (Task 5)

```javascript
// OTP should NEVER be plaintext
db.otp_sessions.findOne()

// otp_hash should be 64-character hex (SHA-256)
// BAD: { otp: "123456" }
// GOOD: { otp_hash: "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92" }
```

---

### 3. Test Login Lockout (Task 5)

Try logging in with wrong password 5 times:
1. Enter wrong password
2. Repeat 5 times
3. **Expinal
- Verify field types match schema:
  - aadhaar: 12-digit string
  - face_encoding: array with 128-512 elements
  - timestamp: ISODate object (not string)
  - voter_id_hash: 64-character hex string

**Debug**:
```javascript
// Get validation rules
db.getCollectionInfos({ name: "voter_users" })[0].options.validator
```

---

## Security Testing

### 1. Test Double-Vote Prevention (Task 1)

Try voting twice with same voter:
1. Login and vote for Alice
2. Logout, login again
3. Try voting for Bob
4. **Expefiles
db.fs.files.find({ "metadata.aadhaar": "123456789012" })

// Check voter has face_grid_id
db.voter_users.findOne(
  { aadhaar: "123456789012" },
  { face_grid_id: 1 }
)
```

---

#### 8. Aggregation Pipeline Errors

**Error**: `$dateTrunc not recognized`

**Solution**:
- Update MongoDB to 5.0+ (required for $dateTrunc)
- Check MongoDB version:
```javascript
db.version()
```

---

#### 9. Schema Validation Errors

**Error**: `Document failed validation`

**Solution**:
- Check exact error message in termicials are registered
- Admin must approve all 3 officials
- Each official must login and click "Approve Decryption"
- Check officials collection:
```javascript
db.officials.countDocuments({ has_approved: true })
// Should return 3
```

---

#### 7. GridFS Images Not Showing

**Error**: Images not found or display broken

**Solution**:
- Check fs.files collection has entries
- Verify face_grid_id in voter_users matches fs.files._id
- Check file MIME type in metadata

**Debug**:
```javascript
// Check GridFS m", 587)
server.starttls()
server.login(sender, password)
server.send_message(msg)
server.quit()
```

---

#### 5. Double-Vote Error

**Error**: `You have already voted in this election`

**This is expected behavior!** The unique compound index prevents double-voting.

**To test again**:
1. Reset election (Admin Dashboard → Reset Election)
2. Or register a new voter with different Aadhaar

---

#### 6. Vote Counting Fails

**Error**: `Not enough officials approved (need 3)`

**Solution**:
- Ensure all 3 offd SENDER_PASSWORD in `.env`
- Verify Gmail App Password (not regular password)
- Check spam/junk folder
- Enable "Less secure app access" in Gmail (if using regular password)
- Try with different email provider

**Debug**:
```python
# Test email manually
import smtplib
from email.mime.text import MIMEText

sender = "your_email@gmail.com"
password = "your_app_password"

msg = MIMEText("Test")
msg["Subject"] = "Test"
msg["From"] = sender
msg["To"] = "recipient@example.com"

server = smtplib.SMTP("smtp.gmail.coghting (bright, even light)
- Face camera directly
- Remove glasses/hats if worn during registration
- Use same device/camera for registration and login
- Check face_encoding array in database (should have 128+ elements)

**Debug**:
```javascript
// Check if face encoding was saved
db.voter_users.findOne(
  { aadhaar: "123456789012" },
  { face_encoding: { $slice: 5 } }
)
// Should show array of floats
```

---

#### 4. OTP Not Received

**Error**: Email with OTP never arrives

**Solution**:
- Check SENDER_EMAIL anenv`
- Verify MongoDB Atlas cluster is running
- Check IP whitelist in Atlas (add your IP or use 0.0.0.0/0 for testing)
- Test connection: `mongosh "YOUR_MONGO_URI"`

---

#### 2. Frontend Server Won't Start

**Error**: `Tesseract executable not found`

**Solution**:
- Install Tesseract OCR (see installation section)
- Set TESSERACT_CMD in `.env` to full path
- Verify: `tesseract --version`

---

#### 3. Face Recognition Fails

**Error**: `Face not detected` or `No match found`

**Solution**:
- Ensure good li("executionStats")

// Check: stage should be "IXSCAN", not "COLLSCAN"
// Check: totalDocsExamined should equal nReturned (efficient)
```

**Index Usage Check**:
```javascript
// List all indexes and their sizes
db.votes.stats().indexSizes

// Check index usage statistics (requires MongoDB 4.2+)
db.votes.aggregate([{ $indexStats: {} }])
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. Backend Server Won't Start

**Error**: `MongoDB connection failed`

**Solution**:
- Check MONGO_URI in `.http://localhost:5000/admin/stream
```

Should stream JSON updates every second:
```json
data: {"2024_GENERAL": {"ALICE": 1}}

data: {"2024_GENERAL": {"ALICE": 1}}
```

3. Submit a new vote and watch the stream update in real-time

---

#### Performance Testing (Task 10)

**Explain Plan Analysis**:

```javascript
// Check if query uses index (IXSCAN) or full scan (COLLSCAN)

// Good: Uses unique_voter_per_election index
db.votes.find({
  voter_id_hash: "8f3a2b1c...",
  election_id: "2024_GENERAL"
}).explainckchain",
      let: { vote_id: "$vote_id" },
      pipeline: [
        { $match: { $expr: { $regexMatch: { input: "$vote_hash", regex: "$$vote_id" } } } }
      ],
      as: "block"
    }
  },
  { $match: { block: { $size: 0 } } }
])
```
Result should be **empty** (all votes have blocks).

---

#### Test Change Streams (Task 6)

**Verify Live Dashboard**:

1. Check that change stream is running (look at server.py terminal):
```
[MongoDB] Change stream watching votes...
```

2. Test SSE endpoint:
```bash
curl     votes: { $sum: 1 }
          }
        },
        { $sort: { _id: 1 } }
      ]
    }
  }
])
```

---

#### Test ACID Transactions (Task 3)

**Check Vote + Blockchain Atomicity**:

1. Count votes and blockchain blocks:
```javascript
db.votes.countDocuments({})
db.blockchain.countDocuments({})
```

Both should be equal (one blockchain block per vote).

2. Verify no orphaned data:
```javascript
// Every vote should have a corresponding blockchain entry
db.votes.aggregate([
  {
    $lookup: {
      from: "blohboard Facet** (single query, multiple stats):
```javascript
db.votes.aggregate([
  { $match: { election_id: "2024_GENERAL" } },
  {
    $facet: {
      total: [{ $count: "n" }],
      per_candidate: [
        { $group: { _id: "$candidate_id", count: { $sum: 1 } } },
        { $sort: { count: -1 } }
      ],
      per_hour: [
        {
          $group: {
            _id: {
              $dateTrunc: {
                date: { $toDate: "$timestamp" },
                unit: "hour"
              }
            },
        te_id: "$_id",
      count: 1,
      name: { $arrayElemAt: ["$cand.name", 0] },
      _id: 0
    }
  },
  { $sort: { count: -1 } }
])
```

**2. Turnout Per Hour**:
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

**3. Das db.fs.files.findOne()._id;
db.fs.chunks.countDocuments({ files_id: fileId })
// Should be > 0
```

---

### Advanced Verification Queries

#### Test Aggregation Pipelines (Task 2)

**1. Votes Per Candidate**:
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
      candidas per voter: face photo + aadhaar card image
- [ ] metadata.aadhaar matches voter's aadhaar
- [ ] metadata.type is "image/jpeg" or "image/png"
- [ ] Index on metadata.aadhaar for fast lookups

**Index Check**:
```javascript
db.fs.files.getIndexes()
```
Should show: `gridfs_aadhaar` index on `metadata.aadhaar`

**File Retrieval Test**:
```javascript
// List all files for a voter
db.fs.files.find({ "metadata.aadhaar": "123456789012" })
```

**Chunks Check**:
```javascript
// Verify chunks exist for a file
var fileId =b.fs.files.find().pretty()
```

**What to Check**:
```javascript
{
  "_id": ObjectId("..."),
  "length": 45678,                      // ✓ File size in bytes
  "chunkSize": 261120,                  // ✓ GridFS chunk size
  "uploadDate": ISODate("..."),         // ✓ Upload timestamp
  "filename": "face_123456789012.jpg",  // ✓ Original filename
  "metadata": {                         // ✓ Custom metadata
    "aadhaar": "123456789012",
    "type": "image/jpeg"
  }
}
```

**Verification Checklist**:
- [ ] Two file*:
```javascript
{
  "_id": ObjectId("..."),
  "election_id": "2024_GENERAL",
  "candidate_id": "ALICE",
  "vote_count": 1                       // ✓ Aggregated count
}
```

**Verification Checklist**:
- [ ] One document per candidate
- [ ] vote_count matches actual votes in votes collection
- [ ] Created by `agg_merge_results()` aggregation pipeline

---

#### 14. **fs.files** and **fs.chunks** Collections (GridFS - Task 8)

**Purpose**: GridFS storage for Aadhaar images and face photos

**Query**:
```javascript
dntains relevant event data

**Aggregation Test** (Task 2):
```javascript
// Failed logins per hour
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

---

#### 13. **agg_results** Collection (Task 2)

**Purpose**: Aggregated vote counts (via $merge)

**Query**:
```javascript
db.agg_results.find().pretty()
```

**What to Check*ssociated aadhaar
  "success": true,                      // ✓ Success/failure flag
  "details": {                          // ✓ Additional context
    "candidate_id": "ALICE",
    "vote_id": "vote_abc123..."
  },
  "timestamp": ISODate("...")           // ✓ Event time
}
```

**Verification Checklist**:
- [ ] Events logged: voter_registered, login_success, vote_submitted, double_vote_attempt, etc.
- [ ] TTL index expires after 90 days (7,776,000 seconds)
- [ ] success field shows true/false
- [ ] details object coCount failed attempts for an aadhaar
db.login_attempts.countDocuments({
  aadhaar: "123456789012",
  success: false
})
// If >= 5, account is locked
```

---

#### 12. **audit_logs** Collection (Task 7)

**Purpose**: Security audit trail (90-day retention)

**Query**:
```javascript
db.audit_logs.find().sort({ timestamp: -1 }).limit(10).pretty()
```

**What to Check**:
```javascript
{
  "_id": ObjectId("..."),
  "event": "vote_submitted",            // ✓ Event type
  "aadhaar": "123456789012",            // ✓ A```

**What to Check**:
```javascript
{
  "_id": ObjectId("..."),
  "aadhaar": "123456789012",
  "success": false,                     // ✓ false for failed attempts
  "ip": "192.168.1.100",                // ✓ IP address
  "created_at": ISODate("...")          // ✓ Timestamp
}
```

**Verification Checklist**:
- [ ] Failed logins recorded with success: false
- [ ] TTL index expires after 15 minutes (900 seconds)
- [ ] Account locks after 5 failed attempts in 15-minute window

**Lockout Test**:
```javascript
// tes after 5 minutes (300 seconds)
- [ ] attempts increments on wrong OTP

**TTL Index Check**:
```javascript
db.otp_sessions.getIndexes()
```
Should show: `expireAfterSeconds: 300` on `created_at` field

**Test TTL**:
```javascript
// Check count immediately
db.otp_sessions.countDocuments({})

// Wait 6 minutes, check again (should be 0 or fewer)
```

---

#### 11. **login_attempts** Collection (Task 5)

**Purpose**: Failed login tracking with lockout

**Query**:
```javascript
db.login_attempts.find().pretty()
t
db.otp_sessions.find().pretty()
```

**What to Check**:
```javascript
{
  "_id": ObjectId("..."),
  "aadhaar": "123456789012",
  "otp_hash": "sha256hash...",          // ✓ SHA-256 hashed OTP (NOT plaintext!)
  "created_at": ISODate("..."),         // ✓ Expiry reference
  "attempts": 0                         // ✓ Failed attempt counter
}
```

**Verification Checklist**:
- [ ] OTP is hashed with SHA-256 (64 hex chars, never plaintext like "123456")
- [ ] created_at is datetime object
- [ ] TTL index auto-dele is hashed
- [ ] role is "official"

---

#### 9. **admin_auth_users** Collection

**Purpose**: Admin user credentials

**Query**:
```javascript
db.admin_auth_users.find().pretty()
```

**What to Check**:
```javascript
{
  "_id": ObjectId("..."),
  "username": "admin",
  "password": "$2b$12$...",             // ✓ Hashed password
  "role": "admin"                       // ✓ Must be "admin"
}
```

---

#### 10. **otp_sessions** Collection (Task 5)

**Purpose**: Temporary OTP storage with TTL

**Query**:
```javascrip8. **official_auth_users** Collection

**Purpose**: Approved officials with login credentials

**Query**:
```javascript
db.official_auth_users.find().pretty()
```

**What to Check**:
```javascript
{
  "_id": ObjectId("..."),
  "aadhaar": "111111111111",
  "official_id": "OFFICIAL_1",
  "password": "$2b$12$...",             // ✓ Hashed password
  "role": "official"                    // ✓ Must be "official"
}
```

**Verification Checklist**:
- [ ] Created during transactional approval (Task 3)
- [ ] Passwordfind().pretty()
```

**What to Check**:
```javascript
{
  "_id": ObjectId("..."),
  "aadhaar": "111111111111",
  "official_id": "OFFICIAL_1",
  "password": "$2b$12$...",             // ✓ Hashed password
  "status": "approved",                 // ✓ "pending", "approved", or "rejected"
  "reviewed_at": ISODate("...")         // ✓ Set when admin approves
}
```

**Verification Checklist**:
- [ ] status changes from "pending" to "approved"
- [ ] reviewed_at is set after approval
- [ ] Aadhaar is 12 digits

---

#### proved is true for all (after approval)
- [ ] key_share field exists (no "secret_key" field - cleaned by Task 9)
- [ ] Partial index on (election_id, has_approved) where has_approved=true

**Key Share Cleanup Check** (Task 9):
```javascript
// Should return 0 (no redundant secret_key fields)
db.officials.countDocuments({ secret_key: { $exists: true } })
```

---

#### 7. **official_requests** Collection

**Purpose**: Pending/approved official registration requests

**Query**:
```javascript
db.official_requests.ey shares

**Query**:
```javascript
db.officials.find().pretty()
```

**What to Check**:
```javascript
{
  "_id": ObjectId("..."),
  "official_id": "OFFICIAL_1",
  "election_id": "2024_GENERAL",
  "has_approved": true,                 // ✓ true after official approves
  "key_share": "base64encodedshare...", // ✓ Threshold key share
  "approved_at": ISODate("...")         // ✓ Approval timestamp
}
```

**Verification Checklist**:
- [ ] All 3 officials present (OFFICIAL_1, OFFICIAL_2, OFFICIAL_3)
- [ ] has_apid": ObjectId("..."),
  "election_id": "2024_GENERAL",
  "status": "active",                   // ✓ "active" or "ended"
  "final_result_ready": false,          // ✓ true after counting
  "candidates": ["ALICE", "BOB", "CHARLIE"]
}
```

**Verification Checklist**:
- [ ] status is "active" (before end) or "ended" (after)
- [ ] final_result_ready changes to true after counting
- [ ] candidates array matches added candidates

---

#### 6. **officials** Collection

**Purpose**: Election officials with threshold k,
  "candidate_id": "ALICE",              // ✓ Uppercase ID
  "name": "Alice Johnson",              // ✓ Display name
  "election_id": "2024_GENERAL"         // ✓ Associated election
}
```

**Verification Checklist**:
- [ ] All 3 candidates present (ALICE, BOB, CHARLIE)
- [ ] Compound unique index on (candidate_id, election_id)

---

#### 5. **elections** Collection

**Purpose**: Election status and configuration

**Query**:
```javascript
db.elections.find().pretty()
```

**What to Check**:
```javascript
{
  "_avascript
// Verify chain linkage
var blocks = db.blockchain.find().sort({ block_id: 1 }).toArray();
for (var i = 1; i < blocks.length; i++) {
  if (blocks[i].previous_hash !== blocks[i-1].vote_hash) {
    print("CHAIN BROKEN at block " + blocks[i].block_id);
  }
}
print("Blockchain integrity: OK");
```

---

#### 4. **candidates** Collection

**Purpose**: Available candidates for election

**Query**:
```javascript
db.candidates.find().pretty()
```

**What to Check**:
```javascript
{
  "_id": ObjectId("...")// ✓ Sequential: block_0, block_1, ...
  "vote_hash": "a1b2c3d4...",               // ✓ SHA-256 of vote data
  "previous_hash": "0000000...",            // ✓ Links to previous block
  "timestamp": "2024-10-23T12:34:56.789Z"   // ✓ ISO timestamp
}
```

**Verification Checklist**:
- [ ] block_id increments: block_0, block_1, block_2...
- [ ] First block has previous_hash = "0000000..."
- [ ] Each block's previous_hash matches prior block's vote_hash
- [ ] One block per vote

**Blockchain Integrity Check**:
```j
```javascript
// This should return 1 for each voter (no duplicates)
db.votes.aggregate([
  { $group: { _id: "$voter_id_hash", count: { $sum: 1 } } },
  { $match: { count: { $gt: 1 } } }
])
```
Result should be **empty** (no voter voted twice)

---

#### 3. **blockchain** Collection

**Purpose**: Immutable blockchain audit trail

**Query**:
```javascript
db.blockchain.find().sort({ block_id: 1 }).pretty()
```

**What to Check**:
```javascript
{
  "_id": ObjectId("..."),
  "block_id": "block_0",                    ot string!)
}
```

**Verification Checklist**:
- [ ] voter_id_hash is 64 characters (SHA-256)
- [ ] receipt_hash is 64 characters
- [ ] timestamp is ISODate (not string)
- [ ] encrypted_vote contains base64 data
- [ ] No duplicate (voter_id_hash, election_id) pairs

**Index Check**:
```javascript
db.votes.getIndexes()
```
Should show:
- `vote_id` unique index
- `unique_voter_per_election` compound index on (voter_id_hash, election_id)
- Compound index on (election_id, candidate_id)

**Double-Vote Prevention Test**:*What to Check**:
```javascript
{
  "_id": ObjectId("..."),
  "vote_id": "vote_abc123...",          // ✓ Unique vote identifier
  "election_id": "2024_GENERAL",        // ✓ Election identifier
  "voter_id_hash": "8f3a2b1c...",       // ✓ SHA-256 hash (64 chars)
  "receipt_hash": "7e2d4f5a...",        // ✓ SHA-256 hash (64 chars)
  "candidate_id": "ALICE",              // ✓ Candidate choice
  "encrypted_vote": "base64string...",  // ✓ Encrypted vote data
  "timestamp": ISODate("2024-10-23...") // ✓ datetime object (nrid_id": ObjectId("...")       // ✓ GridFS file ID for face photo
}
```

**Verification Checklist**:
- [ ] Aadhaar is 12 digits
- [ ] Password is hashed (starts with `$2b$`)
- [ ] face_encoding is array with 128+ elements
- [ ] role is "voter"
- [ ] face_grid_id exists

**Index Check**:
```javascript
db.voter_users.getIndexes()
```
Should show: `unique_aadhaar` index on aadhaar field

---

#### 2. **votes** Collection

**Purpose**: Stores all cast votes

**Query**:
```javascript
db.votes.find().pretty()
```

*{
  "_id": ObjectId("..."),
  "aadhaar": "123456789012",           // ✓ 12-digit number
  "name": "John Doe",                   // ✓ Voter name
  "dob": "1995-05-15",                  // ✓ Date of birth
  "email": "voter1@example.com",        // ✓ Email
  "password": "$2b$12$...",             // ✓ Hashed password (bcrypt)
  "face_encoding": [0.123, -0.456, ...], // ✓ Array of 128-512 floats
  "role": "voter",                      // ✓ Must be "voter"
  "registered_at": ISODate("..."),      // ✓ Timestamp
  "face_gith your MONGO_URI
3. Select database: `evoting_db`

**Option 2: MongoDB Shell**
```bash
mongosh "mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/"
use evoting_db
```

**Option 3: Atlas Web UI**
1. Login to MongoDB Atlas
2. Click "Browse Collections"
3. Select your cluster and database

---

### Collection-by-Collection Verification

#### 1. **voter_users** Collection

**Purpose**: Stores registered voter data

**Query**:
```javascript
db.voter_users.find().pretty()
```

**What to Check**:
```javascript

   - Event details (aadhaar, success status)

#### 6.4 View GridFS Images (Task 8)

1. In Admin Dashboard, click **"GridFS Images"**
2. Enter Aadhaar: **123456789012**
3. Click **"Search Images"**
4. **Check**:
   - Face photo thumbnail
   - Aadhaar card image
   - File metadata (size, upload date, type)
   - "View Full Size" buttons work

---

## MongoDB Data Verification

### Connect to MongoDB

**Option 1: MongoDB Compass** (Recommended)
1. Download: https://www.mongodb.com/products/compass
2. Connect wk cards with vote hashes
   - Previous hash linkage
   - Timestamps
   - Pagination controls

#### 6.2 View Encrypted Votes

1. In Admin Dashboard, click **"View Encrypted Votes"**
2. **Check**:
   - Table with truncated encrypted data
   - Voter ID hashes (SHA-256)
   - Receipt hashes
   - Candidate IDs
   - Timestamps

#### 6.3 View Audit Logs

1. In Admin Dashboard, click **"Audit Logs"**
2. **Check**:
   - Recent audit events (voter_registered, login_success, vote_submitted)
   - Failed logins per hour chartng initiated. Check results below."

#### 5.3 View Results

1. Results appear in Admin Dashboard:
   ```
   === FINAL VOTE COUNTS (Homomorphic + Threshold Decryption) ===
   Alice Johnson: 1 vote(s)
   Bob Smith: 0 vote(s)
   Charlie Brown: 0 vote(s)
   ```

2. **End the Election**:
   - Click **"End Election"** button
   - **Result**: Election status changed to "ended"

---

### Phase 6: Verify All Features

#### 6.1 View Blockchain

1. In Admin Dashboard, click **"View Blockchain"**
2. **Check**:
   - Blocigate to: http://localhost:8000/official/login
2. Login with:
   - **Aadhaar**: 111111111111 (or 222222222222, 333333333333)
   - **Password**: Official@123
3. Click **"Login"**
4. On Official Dashboard, click **"Approve Decryption for 2024_GENERAL"**
5. **Result**: "Decryption approved successfully!"

#### 5.2 Trigger Vote Counting (Admin)

Once **all 3 officials** have approved:

1. Go to Admin Dashboard
2. In the "Counting Control" section
3. Click **"Trigger Vote Counting"** button
4. **Result**: "Vote countiicials

1. Go back to Admin Dashboard (http://localhost:8000/admin/dashboard)
2. Click **"Manage Officials"**
3. You'll see pending official requests
4. For each official:
   - Click **"Approve"** button
   - **Result**: "Official [ID] approved successfully"

5. Refresh page to see approved officials list

**MongoDB Check**: Officials collection updated with key shares

---

### Phase 5: Vote Counting (Threshold Decryption)

#### 5.1 Official Login and Approve Decryption

For **EACH of the 3 officials**:

1. Navte to: http://localhost:8000/official/register
3. Fill in:
   - **Aadhaar Number**: 111111111111
   - **Official ID**: OFFICIAL_1
   - **Password**: Official@123
   - **Confirm Password**: Official@123
4. Click **"Register"**
5. **Result**: "Registration request submitted. Awaiting admin approval."

#### 4.2 Register More Officials (Need 3 total for threshold)

Repeat with:
- **Official 2**: Aadhaar 222222222222, ID: OFFICIAL_2
- **Official 3**: Aadhaar 333333333333, ID: OFFICIAL_3

#### 4.3 Admin Approves Offt

1. On success page, you'll see:
   - **Vote ID**: Unique identifier
   - **Receipt Hash**: SHA-256 hash
   - **Timestamp**: Vote submission time
   - **Encrypted Vote**: Base64-encoded ciphertext

2. **Copy the Vote ID** for later verification
3. Click **"Download Receipt"** to save as text file

**MongoDB Check**: Votes are now stored (see verification section)

---

### Phase 4: Official Registration and Approval

#### 4.1 Register as Official

1. Open **new browser window** (or use incognito)
2. Navigacation

1. Check email (voter1@example.com)
2. Find email with subject: "Your OTP for E-Voting System"
3. Copy the 6-digit OTP code
4. Enter OTP in the form
5. Click **"Verify OTP"**
6. **Result**: Redirected to voting page

#### 3.4 Cast Vote

1. On voting page, you'll see:
   - Alice Johnson
   - Bob Smith
   - Charlie Brown

2. Click radio button next to your choice (e.g., **Alice**)
3. Click **"Submit Vote"** button
4. **Result**: "Vote submitted successfully! Here is your receipt."

#### 3.5 Verify Receipn and Voting

#### 3.1 Login with Face Recognition

1. Navigate to: http://localhost:8000/login
2. Enter **Aadhaar**: 123456789012
3. Enter **Password**: Voter@123
4. Click **"Login"**
5. **Result**: Redirected to face verification page

#### 3.2 Face Verification

1. Click **"Capture Face for Verification"**
2. Allow camera access
3. Position face in same lighting as registration
4. Click **"Capture"** button
5. Click **"Verify Face"** button
6. **Result**: Face matched! OTP sent to email

#### 3.3 OTP Verifiar image of Aadhaar card (or any ID with 12-digit number)
   - Make sure the number is visible

5. Click **"Register"**

6. **Result**: "Registration successful! Please login."

#### 2.2 Register More Voters (Optional)

Repeat the above with different details:
- **Voter 2**: Aadhaar 234567890123, Name: Jane Smith, Email: voter2@example.com
- **Voter 3**: Aadhaar 345678901234, Name: Mike Wilson, Email: voter3@example.com

**MongoDB Check**: See "MongoDB Data Verification" section below

---

### Phase 3: Voter Logito: http://localhost:8000/register
2. Fill in:
   - **Aadhaar Number**: 123456789012 (12 digits)
   - **Name**: John Doe
   - **Date of Birth**: 1995-05-15
   - **Email**: voter1@example.com
   - **Password**: Voter@123
   - **Confirm Password**: Voter@123

3. **Capture Face Photo**:
   - Click "Capture Face Photo" button
   - Allow camera access
   - Position face in camera
   - Click "Capture" button
   - Verify photo shows your face clearly

4. **Upload Aadhaar Card**:
   - Click "Choose File"
   - Upload a cledmin Dashboard, click **"Add Candidate"**
2. Add 3 candidates:
   - **Candidate ID**: ALICE, **Name**: Alice Johnson
   - **Candidate ID**: BOB, **Name**: Bob Smith
   - **Candidate ID**: CHARLIE, **Name**: Charlie Brown
3. Click "Add Candidate" for each
4. **Result**: Candidates added to election

#### 1.4 Start Election

1. In Admin Dashboard, click **"Start Election"** button
2. **Result**: "Election started successfully!"

---

### Phase 2: Voter Registration

#### 2.1 Register First Voter

1. Navigate low

### Phase 1: Admin Setup

#### 1.1 Register Admin Account

1. Navigate to: http://localhost:8000/admin/register
2. Fill in:
   - **Username**: admin
   - **Password**: Admin@123
   - **Confirm Password**: Admin@123
3. Click "Register"
4. **Result**: Admin account created

#### 1.2 Login as Admin

1. Navigate to: http://localhost:8000/admin/login
2. Login with:
   - **Username**: admin
   - **Password**: Admin@123
3. Click "Login"
4. **Result**: Redirected to Admin Dashboard

#### 1.3 Add Candidates

1. In Aart Frontend Server (Port 8000)

Open **Terminal 2**:

```bash
cd secure_e_voting_system
python app.py
```

**Expected Output**:
```
Tesseract executable: C:\Program Files\Tesseract-OCR\tesseract.exe
 * Running on http://127.0.0.1:8000
 * Debug mode: on
```

**Leave this terminal running!**

### Step 3: Verify Both Servers

Open browser and check:
- Frontend: http://localhost:8000 (should show home page)
- Backend: http://localhost:5000/health (should show `{"status": "healthy"}`)

---

## Complete Testing F=================================
🔐 POST-QUANTUM VOTING SYSTEM STARTED
======================================================================
📡 Server: http://localhost:5000
🔑 Election Public Key: b'...'...
👥 Candidates: Alice, Bob, Charlie
🔐 Security: Dilithium + Kyber + Mixnet + Blockchain + Homomorphic
======================================================================

[MongoDB] Change stream watching votes...
 * Running on http://127.0.0.1:5000
```

**Leave this terminal running!**

### Step 2: Stta.aadhaar index
[MongoDB] Bootstrap complete.

=====================================Start Backend Server (Port 5000)

Open **Terminal 1**:

```bash
cd secure_e_voting_system
python voting_system_crypto/backend/server.py
```

**Expected Output**:
```
[MongoDB] Bootstrapping features...
  ✔ Created collection 'voter_users' with $jsonSchema validator
  ✔ Created collection 'votes' with $jsonSchema validator
  ✔ [Task 1] Unique compound index voter_id_hash+election_id on votes
  ✔ [Task 5] OTP TTL index (5-minute expiry)
  ✔ [Task 7] Audit log TTL index (90-day retention)
  ✔ [Task 8] GridFS metadassword for "Mail"
5. Copy the 16-character password

---

## Starting the System

### Step 1: xxxxx.mongodb.net/

# Email for OTP (Gmail recommended)
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your_gmail_app_password

# Backend API URL (don't change unless deploying)
ELECTION_API_URL=http://localhost:5000

# Tesseract path (Windows only, if not in PATH)
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe

# Database name
ELECTION_DB_NAME=evoting_db
```

**How to get Gmail App Password**:
1. Go to Google Account → Security
2. Enable 2-Step Verification
3. Go to App Passwords
4. Generate pa
MONGO_URI=mongodb+srv://username:password@cluster0.r requirements.txt
```

**Key Dependencies**:
- Flask (web framework)
- pymongo (MongoDB driver)
- deepface (face recognition)
- opencv-python (image processing)
- pytesseract (OCR)
- cryptography (encryption)
- pycryptodome (crypto operations)
- phe (Paillier homomorphic encryption)

### 4. Configure Environment Variables

Edit `.env` file:

```env
# Flask secret key (generate with: python -c "import secrets; print(secrets.token_hex(32))")
FLASK_SECRET_KEY=your_secret_key_here

# MongoDB Atlas connection stringheim/tesseract/wiki
# Install to: C:\Program Files\Tesseract-OCR\
# Add to PATH or set in .env: TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

**Mac**:
```bash
brew install tesseract
```

**Linux**:
```bash
sudo apt-get install tesseract-ocr
```

### 3. Install Python Dependencies

```bash
cd secure_e_voting_system
pip install -
```bash
# Download from: https://github.com/UB-Mann    ↓                        ↓
              Face Recognition        Crypto Operations
              OTP via Email          Blockchain Storage
              Session Management     Vote Counting
```

---

## Prerequisites & Installation

### 1. System Requirements

- **Python**: 3.9 or higher
- **MongoDB Atlas**: Active cluster
- **Tesseract OCR**: For Aadhaar card text extraction
- **Webcam**: For face photo capture
- **Email Account**: Gmail with App Password for OTP

### 2. Install Tesseract OCR

**Windows**:                - Voter registration and login
   - Face recognition and OTP verification
   - Admin dashboard and management
   - Official registration and approval
   - Web UI for all users

2. **Backend Server (server.py)** - Port 5000
   - Vote submission and processing
   - Blockchain operations
   - Cryptographic operations (Dilithium, Kyber)
   - Homomorphic counting
   - Threshold decryption
   - RESTful API endpoints

### Data Flow

```
User Browser → app.py (Port 8000) → server.py (Port 5000) → MongoDB Atlas
    [System Architecture Overview](#system-architecture-overview)
2. [Prerequisites & Installation](#prerequisites--installation)
3. [Starting the System](#starting-the-system)
4. [Complete Testing Flow](#complete-testing-flow)
5. [MongoDB Data Verification](#mongodb-data-verification)
6. [Troubleshooting](#troubleshooting)

---

## System Architecture Overview

### Two-Server Architecture

The system runs on **TWO separate Flask servers**:

1. **Frontend Server (app.py)** - Port 8000
# 🚀 Complete Execution and Testing Guide

## Table of Contents
1.