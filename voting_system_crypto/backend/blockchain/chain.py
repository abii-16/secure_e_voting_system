"""
PHASE 5: BLOCKCHAIN INTEGRITY LAYER
Provides immutable audit trail for votes

Each encrypted vote block contains:
- Hash(EncryptedVote)
- Timestamp
- PreviousBlockHash
- Nonce

Uses SHA-3 (modern hashing)

Purpose:
✔ Detect tampering
✔ Immutable audit trail
"""
import hashlib
import json
from typing import List, Dict
from datetime import datetime

class Block:
    """Single block in the blockchain"""
    
    def __init__(self, index: int, votes: List[Dict], previous_hash: str):
        self.index = index
        self.timestamp = datetime.now().isoformat()
        self.votes = votes
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = ""
    
    def calculate_hash(self) -> str:
        """Calculate SHA-3 hash of block
        
        Block contains:
        - Hash(EncryptedVote)
        - Timestamp
        - PreviousBlockHash
        - Nonce
        """
        block_data = {
            'index': self.index,
            'timestamp': self.timestamp,
            'votes': self.votes,
            'previous_hash': self.previous_hash,
            'nonce': self.nonce
        }
        
        block_string = json.dumps(block_data, sort_keys=True).encode()
        return hashlib.sha3_256(block_string).hexdigest()
    
    def mine_block(self, difficulty: int = 2):
        """Proof-of-work mining for block integrity"""
        target = '0' * difficulty
        
        print(f"[PHASE 5] Mining block {self.index}...")
        
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.calculate_hash()
        
        print(f"  ✔ Block mined! Nonce: {self.nonce}, Hash: {self.hash[:32]}...")
    
    def to_dict(self) -> Dict:
        """Export block as dictionary"""
        return {
            'index': self.index,
            'timestamp': self.timestamp,
            'votes': self.votes,
            'previous_hash': self.previous_hash,
            'nonce': self.nonce,
            'hash': self.hash,
            'vote_count': len(self.votes)
        }

class VotingBlockchain:
    """PHASE 5: Blockchain for vote integrity
    
    Provides:
    ✔ Tamper detection
    ✔ Immutable audit trail
    ✔ Cryptographic proof of vote existence
    """
    
    def __init__(self):
        self.chain: List[Block] = []
        self.pending_votes: List[Dict] = []
        self.difficulty = 2
        self.create_genesis_block()
    
    def create_genesis_block(self):
        """Create first block in chain"""
        print(f"\n{'='*60}")
        print(f"PHASE 5: INITIALIZING BLOCKCHAIN")
        print(f"{'='*60}")
        
        genesis = Block(0, [], "0")
        genesis.mine_block(self.difficulty)
        self.chain.append(genesis)
        
        print(f"✔ Genesis block created")
        print(f"✔ Blockchain initialized")
        print(f"{'='*60}\n")
    
    def get_latest_block(self) -> Block:
        """Get most recent block"""
        return self.chain[-1]
    
    def add_vote(self, vote: Dict):
        """Add vote to pending pool
        
        Vote contains:
        - voter_id
        - receipt_hash (SHA-3 of encrypted vote)
        - timestamp
        """
        vote_entry = {
            'receipt_hash': vote['receipt_hash'],
            'timestamp': vote.get('timestamp', datetime.now().isoformat()),
            'vote_hash': hashlib.sha3_256(vote['receipt_hash'].encode()).hexdigest()
        }
        
        self.pending_votes.append(vote_entry)
        print(f"[PHASE 5] Vote added to pending pool: {vote['receipt_hash'][:16]}...")
    
    def mine_pending_votes(self):
        """PHASE 5: Create new block with pending votes
        
        Each block contains:
        - Hash(EncryptedVote) for each vote
        - Timestamp
        - PreviousBlockHash
        - Nonce (from mining)
        """
        if not self.pending_votes:
            print(f"[PHASE 5] No pending votes to mine")
            return
        
        print(f"\n{'='*60}")
        print(f"PHASE 5: MINING NEW BLOCK")
        print(f"{'='*60}")
        print(f"Pending votes: {len(self.pending_votes)}")
        
        block = Block(
            index=len(self.chain),
            votes=self.pending_votes.copy(),
            previous_hash=self.get_latest_block().hash
        )
        
        block.mine_block(self.difficulty)
        self.chain.append(block)
        
        print(f"✔ Block {block.index} added to chain")
        print(f"✔ Votes in block: {len(self.pending_votes)}")
        print(f"✔ Block hash: {block.hash}")
        print(f"✔ Previous hash: {block.previous_hash[:32]}...")
        print(f"✔ Immutable audit trail created")
        print(f"{'='*60}\n")
        
        self.pending_votes = []
    
    def verify_chain(self) -> bool:
        """Verify blockchain integrity
        
        Checks:
        ✔ Each block hash is valid
        ✔ Each block links to previous
        ✔ No tampering detected
        """
        print(f"[PHASE 5] Verifying blockchain integrity...")
        
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]
            
            # Verify hash
            if current.hash != current.calculate_hash():
                print(f"  ✗ Block {i} hash invalid - TAMPERING DETECTED")
                return False
            
            # Verify link
            if current.previous_hash != previous.hash:
                print(f"  ✗ Block {i} link broken - TAMPERING DETECTED")
                return False
        
        print(f"  ✔ All {len(self.chain)} blocks verified")
        print(f"  ✔ No tampering detected")
        print(f"  ✔ Audit trail intact")
        
        return True
    
    def get_vote_proof(self, receipt_hash: str) -> Dict:
        """PHASE 6: Get blockchain proof for receipt
        
        Public portal displays all receipt hashes
        User checks: "My receipt exists"
        
        Ensures:
        ✔ Vote recorded
        ✔ No deletion
        """
        print(f"[PHASE 6] Searching blockchain for receipt: {receipt_hash[:16]}...")
        
        for block in self.chain:
            for vote in block.votes:
                if vote.get('receipt_hash') == receipt_hash:
                    proof = {
                        'found': True,
                        'block_index': block.index,
                        'block_hash': block.hash,
                        'timestamp': block.timestamp,
                        'vote_timestamp': vote['timestamp'],
                        'previous_block_hash': block.previous_hash,
                        'nonce': block.nonce,
                        'verification': 'Vote permanently recorded in blockchain'
                    }
                    
                    print(f"  ✔ Receipt found in block {block.index}")
                    print(f"  ✔ Block hash: {block.hash[:32]}...")
                    print(f"  ✔ Vote permanently recorded")
                    
                    return proof
        
        print(f"  ✗ Receipt not found in blockchain")
        return {'found': False}
    
    def get_chain_summary(self) -> Dict:
        """Get blockchain statistics"""
        total_votes = sum(len(block.votes) for block in self.chain)
        
        return {
            'total_blocks': len(self.chain),
            'total_votes': total_votes,
            'latest_block_hash': self.get_latest_block().hash,
            'chain_valid': self.verify_chain(),
            'pending_votes': len(self.pending_votes),
            'integrity': 'INTACT' if self.verify_chain() else 'COMPROMISED'
        }
