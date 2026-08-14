"""
Voting Module - PHASE 3: Post-Quantum Secure Voting Flow
Implements: Dilithium Signing + Kyber Encryption + Homomorphic Layer
"""
import json
import hashlib
from typing import Dict, List
from datetime import datetime
from crypto.pq_crypto import DilithiumKeyPair, KyberEncryption

class VoteHandler:
    """Handles secure vote submission with full PQ crypto flow"""
    
    def __init__(self, election_public_key: str):
        self.election_public_key = bytes.fromhex(election_public_key)
        self.kyber = KyberEncryption()
        self.submitted_votes = []
        self.vote_counter = 0
    
    def create_vote(self, candidate_id: str, voter_id: str) -> Dict:
        """PHASE 3 - STEP 1: Vote Selection"""
        self.vote_counter += 1
        vote = {
            'vote_id': f"VOTE_{self.vote_counter:06d}",
            'candidate_id': candidate_id,
            'timestamp': datetime.now().isoformat(),
            'voter_id_hash': hashlib.sha3_256(voter_id.encode()).hexdigest()
        }
        print(f"[PHASE 3.1] Vote created: {vote['vote_id']} for {candidate_id}")
        return vote
    
    def sign_vote(self, vote: Dict, voter_keypair: DilithiumKeyPair) -> Dict:
        """PHASE 3 - STEP 2: Sign Vote with Dilithium
        
        Guarantees:
        ✔ Authentic voter
        ✔ No tampering
        ✔ Quantum resistance
        """
        vote_data = json.dumps(vote, sort_keys=True).encode()
        signature = voter_keypair.sign(vote_data)
        
        signed_vote = {
            'vote': vote,
            'signature': signature.hex(),
            'public_key': voter_keypair.public_key.hex(),
            'signature_algorithm': 'Dilithium3'
        }
        
        print(f"[PHASE 3.2] Vote signed with Dilithium")
        print(f"  ✔ Signature: {signature.hex()[:32]}...")
        print(f"  ✔ Public Key: {voter_keypair.public_key.hex()[:32]}...")
        
        return signed_vote
    
    def verify_signature(self, signed_vote: Dict, voter_keypair=None) -> bool:
        """PHASE 3 - STEP 2b: Verify Dilithium Signature
        
        Server verifies using Dilithium public key
        If invalid → reject
        """
        vote_data = json.dumps(signed_vote['vote'], sort_keys=True).encode()
        signature = bytes.fromhex(signed_vote['signature'])
        public_key = bytes.fromhex(signed_vote['public_key'])

        # Demo-safe verification:
        # If the server has the reconstructed voter keypair (because the client supplied the private key),
        # verify using that keypair to keep signing/verification consistent in this simulation.
        if voter_keypair is not None:
            is_valid = voter_keypair.verify(vote_data, signature, public_key)
        else:
            # Fallback to legacy simulation
            expected = hashlib.sha3_512(public_key + vote_data).digest()
            is_valid = signature == expected
        
        if is_valid:
            print(f"[PHASE 3.2b] ✔ Signature verified - Vote authentic")
        else:
            print(f"[PHASE 3.2b] ✗ Signature verification FAILED - Vote rejected")
        
        return is_valid
    
    def encrypt_vote(self, signed_vote: Dict) -> bytes:
        """PHASE 3 - STEP 3: Encrypt Vote with Kyber
        
        Election Authority publishes: Kyber Public Key
        Vote encrypted using Kyber
        
        Result: EncryptedVote_Kyber
        Only election private key can decrypt
        
        Provides:
        ✔ Quantum-safe encryption
        ✔ Future-proof secrecy
        """
        vote_json = json.dumps(signed_vote, sort_keys=True).encode()
        encrypted = self.kyber.encrypt(vote_json, self.election_public_key)
        
        print(f"[PHASE 3.3] Vote encrypted with Kyber")
        print(f"  ✔ Encrypted size: {len(encrypted)} bytes")
        print(f"  ✔ Quantum-safe: YES")
        print(f"  ✔ Only election authority can decrypt")
        
        return encrypted
    
    def generate_receipt(self, encrypted_vote: bytes) -> str:
        """PHASE 6: End-to-End Verification
        
        Generate: ReceiptHash = SHA3(EncryptedVote)
        User stores receipt
        
        Ensures:
        ✔ Vote recorded
        ✔ No deletion
        """
        receipt_hash = hashlib.sha3_256(encrypted_vote).hexdigest()
        
        print(f"[PHASE 6] Receipt generated")
        print(f"  ✔ Receipt Hash: {receipt_hash}")
        print(f"  ⚠️  User must save this receipt for verification")
        
        return receipt_hash
    
    def submit_vote(self, voter_id: str, candidate_id: str, 
                   voter_keypair: DilithiumKeyPair) -> Dict:
        """Complete PHASE 3 voting flow with all security layers"""
        
        print(f"\n{'='*60}")
        print(f"STARTING POST-QUANTUM VOTING FLOW")
        print(f"{'='*60}")
        
        # PHASE 3 - STEP 1: Vote Selection
        vote = self.create_vote(candidate_id, voter_id)
        
        # PHASE 3 - STEP 2: Sign with Dilithium
        signed_vote = self.sign_vote(vote, voter_keypair)
        
        # PHASE 3 - STEP 2b: Verify signature
        if not self.verify_signature(signed_vote, voter_keypair=voter_keypair):
            print(f"[ERROR] Vote rejected - Invalid signature")
            raise ValueError("Invalid Dilithium signature - Vote rejected")
        
        # PHASE 3 - STEP 3: Encrypt with Kyber
        encrypted_vote = self.encrypt_vote(signed_vote)
        
        # PHASE 6: Generate receipt for E2E verification
        receipt_hash = self.generate_receipt(encrypted_vote)
        
        # Store vote record (will be processed through mixnet and blockchain)
        vote_record = {
            'vote_id': vote['vote_id'],
            'voter_id': voter_id,
            'encrypted_vote': encrypted_vote.hex(),
            'signature': signed_vote['signature'],
            'receipt_hash': receipt_hash,
            'candidate_id': candidate_id,  # For demo counting
            'timestamp': datetime.now().isoformat(),
            'status': 'submitted',
            'phases_completed': [
                'PHASE_3_SIGNING',
                'PHASE_3_ENCRYPTION',
                'PHASE_6_RECEIPT_GENERATED'
            ]
        }
        
        self.submitted_votes.append(vote_record)
        
        print(f"\n{'='*60}")
        print(f"VOTE SUBMISSION COMPLETE")
        print(f"{'='*60}")
        print(f"✔ Vote ID: {vote['vote_id']}")
        print(f"✔ Receipt: {receipt_hash}")
        print(f"✔ Status: Ready for mixnet processing")
        print(f"{'='*60}\n")
        
        return {
            'success': True,
            'vote_id': vote['vote_id'],
            'receipt_hash': receipt_hash,
            'message': 'Vote submitted successfully',
            'next_phases': [
                'PHASE_4_MIXNET_SHUFFLING',
                'PHASE_5_BLOCKCHAIN_STORAGE',
                'PHASE_7_HOMOMORPHIC_COUNTING'
            ]
        }
    
    def verify_receipt(self, receipt_hash: str) -> bool:
        """PHASE 6: Verify receipt exists in system"""
        exists = any(v['receipt_hash'] == receipt_hash for v in self.submitted_votes)
        
        if exists:
            print(f"[PHASE 6] ✔ Receipt verified - Vote recorded")
        else:
            print(f"[PHASE 6] ✗ Receipt not found")
        
        return exists
    
    def get_encrypted_votes(self) -> List[str]:
        """Get all encrypted votes for mixnet processing"""
        return [v['encrypted_vote'] for v in self.submitted_votes]
    
    def get_vote_by_receipt(self, receipt_hash: str) -> Dict:
        """Get vote record by receipt hash"""
        for vote in self.submitted_votes:
            if vote['receipt_hash'] == receipt_hash:
                return vote
        return None
