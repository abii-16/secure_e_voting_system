"""
Homomorphic Counting Module
Privacy-preserving vote tallying using Paillier encryption
"""
from phe import paillier
from typing import Dict, List
import json

class HomomorphicCounter:
    """Counts votes without decrypting individual ballots"""
    
    def __init__(self):
        # Generate Paillier keypair
        self.public_key, self.private_key = paillier.generate_paillier_keypair()
        self.encrypted_tallies = {}
    
    def encode_vote(self, candidate_id: str, candidates: List[str]) -> Dict[str, int]:
        """Encode vote as one-hot vector"""
        encoding = {c: 0 for c in candidates}
        encoding[candidate_id] = 1
        return encoding
    
    def encrypt_vote(self, vote_encoding: Dict[str, int]) -> Dict[str, paillier.EncryptedNumber]:
        """Encrypt vote using Paillier"""
        encrypted = {}
        for candidate, value in vote_encoding.items():
            encrypted[candidate] = self.public_key.encrypt(value)
        return encrypted
    
    def add_encrypted_vote(self, encrypted_vote: Dict[str, paillier.EncryptedNumber]):
        """Add encrypted vote to tally"""
        for candidate, enc_value in encrypted_vote.items():
            if candidate not in self.encrypted_tallies:
                self.encrypted_tallies[candidate] = enc_value
            else:
                # Homomorphic addition
                self.encrypted_tallies[candidate] += enc_value
    
    def decrypt_final_tally(self) -> Dict[str, int]:
        """Decrypt only the final tally"""
        results = {}
        for candidate, enc_tally in self.encrypted_tallies.items():
            results[candidate] = self.private_key.decrypt(enc_tally)
        return results
    
    def count_votes(self, votes: List[Dict], candidates: List[str]) -> Dict[str, int]:
        """Complete homomorphic counting flow"""
        
        print(f"[Homomorphic] Counting {len(votes)} votes for {len(candidates)} candidates")
        
        # Process each vote
        for vote in votes:
            candidate_id = vote['candidate_id']
            
            # Encode and encrypt
            encoding = self.encode_vote(candidate_id, candidates)
            encrypted = self.encrypt_vote(encoding)
            
            # Add to tally
            self.add_encrypted_vote(encrypted)
        
        # Decrypt final result
        results = self.decrypt_final_tally()
        
        print(f"[Homomorphic] Final tally: {results}")
        return results
    
    def export_public_key(self) -> str:
        """Export public key for voters"""
        return str(self.public_key.n)
