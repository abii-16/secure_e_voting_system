"""
Post-Quantum Certificate Authority
Issues certificates for verified voters
"""
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict

class CertificateAuthority:
    """Issues and verifies voter certificates"""
    
    def __init__(self):
        self.ca_private_key = hashlib.sha3_256(b"CA_MASTER_KEY").digest()
    
    def issue_certificate(self, voter_id: str, public_key: str, 
                         validity_days: int = 365) -> Dict:
        """Issue certificate for verified voter"""
        
        expiry = datetime.now() + timedelta(days=validity_days)
        
        certificate = {
            'voter_id': voter_id,
            'public_key': public_key,
            'issued_at': datetime.now().isoformat(),
            'expires_at': expiry.isoformat(),
            'issuer': 'QuantumVotingCA'
        }
        
        # Sign certificate with CA key
        cert_data = json.dumps(certificate, sort_keys=True).encode()
        signature = hashlib.sha3_512(self.ca_private_key + cert_data).digest()
        
        certificate['ca_signature'] = signature.hex()
        
        return certificate
    
    def verify_certificate(self, certificate: Dict) -> bool:
        """Verify certificate signature and expiry"""
        
        # Check expiry
        expiry = datetime.fromisoformat(certificate['expires_at'])
        if datetime.now() > expiry:
            return False
        
        # Verify signature
        ca_sig = bytes.fromhex(certificate['ca_signature'])
        cert_copy = certificate.copy()
        del cert_copy['ca_signature']
        
        cert_data = json.dumps(cert_copy, sort_keys=True).encode()
        expected_sig = hashlib.sha3_512(self.ca_private_key + cert_data).digest()
        
        return ca_sig == expected_sig
