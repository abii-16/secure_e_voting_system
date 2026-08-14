"""
Threshold Decryption Module
Splits election key among multiple authorities
"""
import hashlib
import secrets
from typing import List, Dict, Tuple

class ThresholdKeyShare:
    """Single key share for threshold scheme"""
    
    def __init__(self, share_id: int, share_data: bytes, authority: str):
        self.share_id = share_id
        self.share_data = share_data
        self.authority = authority
    
    def to_dict(self) -> Dict:
        return {
            'share_id': self.share_id,
            'share_data': self.share_data.hex(),
            'authority': self.authority
        }

class ThresholdCrypto:
    """Implements (t, n) threshold scheme"""
    
    def __init__(self, threshold: int, total_shares: int):
        self.threshold = threshold  # Minimum shares needed
        self.total_shares = total_shares  # Total shares created
        self.master_key = secrets.token_bytes(32)
    
    def split_key(self, authorities: List[str]) -> List[ThresholdKeyShare]:
        """Split master key into shares"""
        
        if len(authorities) != self.total_shares:
            raise ValueError(f"Need {self.total_shares} authorities")
        
        shares = []
        
        # Simple XOR-based secret sharing (use Shamir in production)
        for i, authority in enumerate(authorities):
            if i < self.total_shares - 1:
                share_data = secrets.token_bytes(32)
            else:
                # Last share reconstructs the key
                share_data = self.master_key
                for s in shares:
                    share_data = bytes(a ^ b for a, b in zip(share_data, s.share_data))
            
            share = ThresholdKeyShare(i, share_data, authority)
            shares.append(share)
        
        return shares
    
    def reconstruct_key(self, shares: List[ThresholdKeyShare]) -> bytes:
        """Reconstruct key from threshold shares"""
        
        if len(shares) < self.threshold:
            raise ValueError(f"Need at least {self.threshold} shares")
        
        # XOR all shares together
        reconstructed = shares[0].share_data
        for share in shares[1:]:
            reconstructed = bytes(a ^ b for a, b in zip(reconstructed, share.share_data))
        
        return reconstructed
    
    def verify_reconstruction(self, reconstructed_key: bytes) -> bool:
        """Verify reconstructed key matches master"""
        return reconstructed_key == self.master_key

class ElectionAuthorities:
    """Manages election authorities and key reconstruction"""
    
    def __init__(self, authority_names: List[str], threshold: int):
        self.authorities = authority_names
        self.threshold = threshold
        self.total = len(authority_names)
        
        self.crypto = ThresholdCrypto(threshold, self.total)
        self.shares = self.crypto.split_key(authority_names)
    
    def get_share(self, authority: str) -> ThresholdKeyShare:
        """Get key share for authority"""
        for share in self.shares:
            if share.authority == authority:
                return share
        raise ValueError(f"Authority {authority} not found")
    
    def reconstruct_election_key(self, participating_authorities: List[str]) -> Dict:
        """Reconstruct key with participating authorities"""
        
        if len(participating_authorities) < self.threshold:
            return {
                'success': False,
                'error': f'Need {self.threshold} authorities, got {len(participating_authorities)}'
            }
        
        # Collect shares
        shares = [self.get_share(auth) for auth in participating_authorities]
        
        # Reconstruct
        key = self.crypto.reconstruct_key(shares[:self.threshold])
        
        # Verify
        valid = self.crypto.verify_reconstruction(key)
        
        return {
            'success': valid,
            'key': key.hex() if valid else None,
            'authorities_used': participating_authorities[:self.threshold]
        }
