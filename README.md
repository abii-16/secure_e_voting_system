# 🗳️ Post-Quantum Secure E-Voting System

A secure and quantum-resistant electronic voting platform that combines Post-Quantum Cryptography (PQC), Multi-Factor Authentication (MFA), Blockchain, Mixnets, Homomorphic Encryption, and Threshold Decryption to ensure voter privacy, vote integrity, and end-to-end verifiability. The system is implemented using Python, Flask, and MongoDB Atlas.

---

## 🚀 Features

* 🔐 **Post-Quantum Security**

  * Dilithium digital signatures
  * Kyber encryption
* 👤 **Multi-Factor Authentication**

  * Password authentication
  * Email OTP verification
  * Face recognition
  * Device fingerprinting
* 🕵️ **Anonymous Voting**

  * 3-node Mixnet vote shuffling
* ⛓️ **Blockchain Audit Trail**

  * SHA3-based tamper-evident ledger
* 📊 **Privacy-Preserving Vote Counting**

  * Homomorphic tallying using Paillier encryption
* 🔑 **Threshold Decryption**

  * Distributed trust with 3-of-5 authority approval
* ✅ **End-to-End Verification**

  * Receipt-based vote verification
* 🧾 **Digital Certificates**

  * Certificate Authority for voter credentials

---

## 🏗️ System Architecture

The application consists of two major layers:

### Frontend Layer

* Flask-based web interface
* Voter, Admin, and Election Official portals
* Session management and authentication
* Face recognition and OTP verification

### Cryptographic Backend

* REST API-based secure voting pipeline
* Post-quantum cryptography operations
* Mixnet anonymization
* Blockchain storage
* Homomorphic vote counting
* Threshold decryption services

Both layers connect to a shared MongoDB Atlas database.

---

## 🔄 Voting Workflow

### 1. Voter Registration

* Aadhaar verification using OCR
* Face capture and biometric encoding
* Password hashing with bcrypt
* Dilithium keypair generation
* Certificate issuance by Certificate Authority

### 2. Secure Login

* Password verification
* OTP authentication
* Face recognition matching
* Device fingerprint validation

### 3. Vote Casting

* Vote creation and signing using Dilithium
* Encryption using Kyber
* Receipt generation for verification

### 4. Vote Anonymization

* Multi-layer Mixnet shuffling
* Re-encryption and randomization
* Removal of voter-vote linkage

### 5. Blockchain Recording

* Vote hashes stored in blockchain blocks
* SHA3-based proof-of-work integrity checks

### 6. Vote Verification

* Receipt lookup and inclusion proof
* End-to-end vote confirmation

### 7. Homomorphic Counting

* Encrypted vote aggregation
* No individual vote decryption

### 8. Threshold Decryption

* 3-of-5 authority approval model
* Distributed key reconstruction

### 9. Result Publication

* Final tally generation
* Integrity verification
* Election result publication

---

## 🔒 Security Mechanisms

| Property                    | Mechanism                       |
| --------------------------- | ------------------------------- |
| Voter Authenticity          | Dilithium Digital Signatures    |
| Vote Confidentiality        | Kyber Encryption                |
| Voter Anonymity             | Mixnet Shuffling                |
| Vote Integrity              | SHA3 Blockchain                 |
| Privacy-Preserving Counting | Paillier Homomorphic Encryption |
| Distributed Trust           | Threshold Decryption            |
| Vote Verification           | Receipt-Based Verification      |
| Identity Assurance          | Aadhaar OCR + Face Recognition  |
| Quantum Resistance          | Dilithium + Kyber               |

---

## 🛠️ Technology Stack

| Category                  | Technology                    |
| ------------------------- | ----------------------------- |
| Backend                   | Flask                         |
| Database                  | MongoDB Atlas                 |
| Post-Quantum Cryptography | Dilithium, Kyber (simulation) |
| Homomorphic Encryption    | Paillier                      |
| Authentication            | bcrypt, pyotp                 |
| Biometrics                | DeepFace (Facenet)            |
| OCR                       | pytesseract + Tesseract OCR   |
| Cryptography              | PyCryptodome, cryptography    |
| Email Services            | SMTP                          |
| CORS                      | flask-cors                    |

---

## 📦 Installation

```bash
git clone https://github.com/abii-16/secure_e_voting_system.git
cd secure_e_voting_system
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set `FLASK_SECRET_KEY`, `MONGO_URI`, `SENDER_EMAIL`, and `SENDER_PASSWORD`. Do not commit `.env`. Tesseract OCR must be installed on the machine for Aadhaar card login.

Optional crypto-only install:

```bash
pip install -r voting_system_crypto/requirements-minimal.txt
```

---

## ▶️ Running the Application

Create a `.env` file first. Both processes share `MONGO_URI`.

### Start the Cryptographic Backend (port 5000)

```bash
python voting_system_crypto/backend/server.py
```

### Start the Frontend Application (port 8000)

```bash
python app.py
```

---

## 👥 User Roles

### Voter

* Register with Aadhaar and facial verification
* Login through 4-factor authentication
* Cast votes securely
* Verify vote using receipt hash

### Admin

* Manage elections and candidates
* View blockchain records
* Monitor election status

### Election Official

* Participate in threshold decryption
* Approve result decryption process
* Monitor election integrity

---

## ⚠️ Current Limitations

* Dilithium and Kyber are simulated and can be replaced with real NIST-standard PQC implementations such as `liboqs-python`.
* Threshold sharing currently uses XOR-based splitting instead of Shamir's Secret Sharing.
* Mixnet and Zero-Knowledge Proof implementations are simplified for demonstration purposes.
* Store secrets only in `.env`. Never commit MongoDB URIs, Gmail app passwords, or Aadhaar images.

---

## 📌 Project Objective

This project demonstrates how post-quantum cryptography, blockchain, biometric authentication, homomorphic encryption, and distributed trust mechanisms can be integrated into a secure electronic voting system capable of resisting both classical and future quantum computing threats.
