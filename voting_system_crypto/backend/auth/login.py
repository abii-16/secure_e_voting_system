"""
Multi-Factor Authentication Module
Password + OTP + Device + Face Recognition
"""
import bcrypt
import pyotp
import hashlib
import json
from datetime import datetime
from typing import Dict, Optional

class MultiFactorAuth:
    """Handles MFA login flow"""
    
    def __init__(self, registration_system):
        self.registration = registration_system
        self.otp_secrets = {}
        self.device_fingerprints = {}
    
    def verify_password(self, voter_id: str, password: str) -> bool:
        """Verify password using bcrypt"""
        voter = self.registration.get_voter(voter_id)
        if not voter:
            return False
        
        stored_hash = voter['password_hash'].encode()
        return bcrypt.checkpw(password.encode(), stored_hash)
    
    def generate_otp_secret(self, voter_id: str) -> str:
        """Generate OTP secret for voter"""
        secret = pyotp.random_base32()
        self.otp_secrets[voter_id] = secret
        return secret
    
    def verify_otp(self, voter_id: str, otp_code: str) -> bool:
        """Verify OTP code"""
        secret = self.otp_secrets.get(voter_id)
        if not secret:
            return False
        
        totp = pyotp.TOTP(secret)
        return totp.verify(otp_code, valid_window=1)
    
    def register_device(self, voter_id: str, device_info: Dict) -> str:
        """Register device fingerprint"""
        fingerprint = hashlib.sha3_256(
            json.dumps(device_info, sort_keys=True).encode()
        ).hexdigest()
        
        self.device_fingerprints[voter_id] = fingerprint
        return fingerprint
    
    def verify_device(self, voter_id: str, device_info: Dict) -> bool:
        """Verify device fingerprint"""
        stored_fp = self.device_fingerprints.get(voter_id)
        if not stored_fp:
            return False
        
        current_fp = hashlib.sha3_256(
            json.dumps(device_info, sort_keys=True).encode()
        ).hexdigest()
        
        return stored_fp == current_fp
    
    def verify_face(self, voter_id: str, face_image) -> bool:
        """Verify face recognition"""
        voter = self.registration.get_voter(voter_id)
        if not voter:
            return False
        
        # Simulate face matching
        current_hash = hashlib.sha3_256(str(face_image).encode()).hexdigest()
        return current_hash == voter['face_hash']
    
    def login(self, voter_id: str, password: str, otp_code: str,
              device_info: Dict, face_image) -> Dict:
        """Complete MFA login flow"""
        
        # Step 1: Password
        if not self.verify_password(voter_id, password):
            return {'success': False, 'error': 'Invalid password'}
        
        # Step 2: OTP
        if not self.verify_otp(voter_id, otp_code):
            return {'success': False, 'error': 'Invalid OTP'}
        
        # Step 3: Device
        if not self.verify_device(voter_id, device_info):
            return {'success': False, 'error': 'Unrecognized device'}
        
        # Step 4: Face
        if not self.verify_face(voter_id, face_image):
            return {'success': False, 'error': 'Face recognition failed'}
        
        return {
            'success': True,
            'voter_id': voter_id,
            'session_token': hashlib.sha3_256(
                f"{voter_id}{datetime.now()}".encode()
            ).hexdigest()
        }
