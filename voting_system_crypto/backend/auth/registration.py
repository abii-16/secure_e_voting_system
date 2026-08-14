"""
Voter Registration Module
Handles identity verification and key generation
"""
import bcrypt
import hashlib
import json
from typing import Dict, Tuple
from crypto.pq_crypto import generate_voter_keypair
from crypto.certificate import CertificateAuthority

class VoterRegistration:
    """Handles voter registration flow"""
    
    def __init__(self):
        self.ca = CertificateAuthority()
        self.registered_voters = {}
    
    def verify_identity(self, voter_id: str, aadhaar_data: Dict) -> bool:
        """Simulate Aadhaar identity verification"""
        # In production: integrate with actual identity verification API
        required_fields = ['name', 'dob', 'address']
        return all(field in aadhaar_data for field in required_fields)
    
    def capture_biometric(self, face_image) -> str:
        """Capture and hash face embedding"""
        # In production: use face_recognition library
        # For now, simulate with hash
        face_hash = hashlib.sha3_256(str(face_image).encode()).hexdigest()
        return face_hash
    
    def register_voter(self, voter_id: str, password: str, 
                      aadhaar_data: Dict, face_image) -> Dict:
        """Complete registration flow"""
        
        # Step 1: Verify identity
        if not self.verify_identity(voter_id, aadhaar_data):
            raise ValueError("Identity verification failed")
        
        # Step 2: Capture biometric
        face_hash = self.capture_biometric(face_image)
        
        # Step 3: Generate Dilithium keypair
        keypair, keys = generate_voter_keypair()
        
        # Step 4: Issue certificate
        certificate = self.ca.issue_certificate(voter_id, keys['public_key'])
        
        # Step 5: Store password securely
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        password_integrity = hashlib.sha3_256(password.encode()).hexdigest()
        
        # Store voter data
        voter_data = {
            'voter_id': voter_id,
            'password_hash': password_hash.decode(),
            'password_integrity': password_integrity,
            'face_hash': face_hash,
            'public_key': keys['public_key'],
            'certificate': certificate,
            'registered': True
        }
        
        self.registered_voters[voter_id] = voter_data
        
        return {
            'voter_id': voter_id,
            'private_key': keys['private_key'],  # Give to voter securely
            'public_key': keys['public_key'],
            'certificate': certificate,
            'status': 'registered'
        }
    
    def get_voter(self, voter_id: str) -> Dict:
        """Retrieve voter data"""
        return self.registered_voters.get(voter_id)
