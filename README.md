# 🗳️ Secure E-Voting System

<p align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Web_Framework-000000?style=for-the-badge&logo=flask&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?style=for-the-badge&logo=mongodb&logoColor=white)
![Post Quantum](https://img.shields.io/badge/Post--Quantum-Cryptography-6A5ACD?style=for-the-badge)
![Blockchain](https://img.shields.io/badge/Blockchain-SHA3-orange?style=for-the-badge)
![Face Recognition](https://img.shields.io/badge/Face-Recognition-success?style=for-the-badge)
![OCR](https://img.shields.io/badge/OCR-Tesseract-blue?style=for-the-badge)

</p>

<p align="center">

![Status](https://img.shields.io/badge/Status-Completed-brightgreen)
![License](https://img.shields.io/badge/License-MIT-green)
![Flask](https://img.shields.io/badge/Framework-Flask-red)
![Database](https://img.shields.io/badge/Database-MongoDB-success)

</p>

---

## 📌 Overview

A **prototype secure electronic voting system** demonstrating the integration of modern authentication and cryptographic techniques for digital voting.

The project combines:

- 🗳️ Secure voter registration
- 👤 Face Recognition
- 🪪 Aadhaar OCR Verification
- ✉️ Email OTP Authentication
- 🔐 Password Hashing (bcrypt)
- 🛡️ Simulated Post-Quantum Cryptography
- 🔄 Mixnet-based Vote Anonymization
- ⛓️ Blockchain-inspired Audit Trail
- ➕ Homomorphic Vote Counting
- 🔑 Threshold Decryption

> **Note:** This project is intended as a **research and educational prototype** to demonstrate the workflow of a secure e-voting system. Certain cryptographic components (such as Dilithium and Kyber) are **simulated** for demonstration purposes and are **not intended for production deployment**.

---

## 🏗️ Architecture

```
Browser
     │
     ▼
Flask Web Application
(app.py)
     │
 REST API
     │
     ▼
Crypto Backend
(server.py)
     │
     ▼
MongoDB Atlas
```

---

## 📂 Project Structure

```
Secure-E-Voting-System
│
├── app.py
├── test.py
├── templates/
│
├── voting_system_crypto/
│   ├── backend/
│   ├── frontend/
│   ├── run_server.py
│   ├── run_client.py
│   ├── demo_all_phases.py
│   ├── test_imports.py
│   ├── test_server.py
│   └── requirements.txt
│
├── requirements.txt
├── README.md
└── .gitignore
```

---

## 🔒 Security Components

| Component | Technology |
|-----------|------------|
| Authentication | Password + OTP + Face Recognition |
| Password Hashing | bcrypt |
| OCR | Tesseract |
| Face Recognition | face_recognition |
| Database | MongoDB Atlas |
| Digital Signature | Dilithium (Simulation) |
| Encryption | Kyber (Simulation) |
| Vote Privacy | Mixnet |
| Audit Trail | Blockchain |
| Vote Counting | Paillier Homomorphic Encryption |
| Trust Distribution | Threshold Decryption |

---

## ⚙️ Installation

Clone the repository

```bash
git clone https://github.com/raveena31/secure-e-voting-system.git

cd secure-e-voting-system
```

Create virtual environment

```bash
python -m venv venv
```

Activate

### Windows

```bash
venv\Scripts\activate
```

### Linux/macOS

```bash
source venv/bin/activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

## 🔑 Configure Environment Variables

Create a `.env` file in the project root.

```env
FLASK_SECRET_KEY=

MONGO_URI=

ELECTION_API_URL=http://localhost:5000

SENDER_EMAIL=

SENDER_PASSWORD=
```

---

## ▶️ Run the Project

### Start Crypto Backend

```bash
python voting_system_crypto/run_server.py
```

### Start Flask Application

Open another terminal.

```bash
python app.py
```

Open

```
http://localhost:8000
```

---

## 👤 Voter Workflow

```
Register
   │
   ▼
Login
   │
   ▼
Face Verification
   │
   ▼
OTP Verification
   │
   ▼
Cast Vote
   │
   ▼
Receipt Generation
```

---

## 👨‍💼 Admin Workflow

```
Admin Login
      │
      ▼
Dashboard
      │
      ▼
Manage Elections
      │
      ▼
View Blockchain
      │
      ▼
Publish Results
```

---

## 🛠️ Technologies Used

- Python
- Flask
- MongoDB Atlas
- PyMongo
- OpenCV
- face_recognition
- Tesseract OCR
- bcrypt
- Cryptography
- PyCryptodome
- Paillier Homomorphic Encryption
- PyOTP
- Flask-CORS

---

## 🚀 Future Enhancements

- Real Dilithium & Kyber using liboqs
- JWT Authentication
- Docker Deployment
- Kubernetes Deployment
- CI/CD Pipeline
- Shamir Secret Sharing
- Verifiable Mixnets
- Production-grade Zero Knowledge Proofs

---

## 👩‍💻 Author

**Raveena**

B.Tech Computer Science and Engineering

VIT Chennai

---

## ⭐ If you found this project useful, consider giving it a Star!