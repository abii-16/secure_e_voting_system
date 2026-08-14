# Post-Quantum Secure Voting System

A quantum-resistant e-voting platform using Dilithium signatures and Kyber encryption.

## Security Features

- **Post-Quantum Cryptography**: Dilithium (signatures) + Kyber (encryption)
- **Multi-Factor Authentication**: Password + OTP + Face Recognition
- **Mixnet Shuffling**: Anonymous vote submission
- **Blockchain Integrity**: Tamper-proof audit trail
- **Homomorphic Counting**: Privacy-preserving tallying
- **Threshold Decryption**: Distributed key management
- **End-to-End Verification**: Receipt-based verification

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Start registration server
python backend/server.py

# Run voter client
python frontend/voter_app.py
```

## Architecture

1. **Registration**: Identity verification → Dilithium keypair → Certificate issuance
2. **Login**: MFA (password + OTP + face + device)
3. **Voting**: Sign (Dilithium) → Encrypt (Kyber) → Mixnet → Blockchain
4. **Counting**: Homomorphic addition → Threshold decryption → Result publication
