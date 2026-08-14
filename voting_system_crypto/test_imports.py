"""
Test all imports to identify issues
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

print("Testing imports...")

try:
    print("✓ Importing Flask...")
    from flask import Flask, request, jsonify
    from flask_cors import CORS
    
    print("✓ Importing auth modules...")
    from auth.registration import VoterRegistration
    from auth.login import MultiFactorAuth
    
    print("✓ Importing voting modules...")
    from voting.vote_handler import VoteHandler
    from voting.mixnet import MixnetCascade
    
    print("✓ Importing blockchain...")
    from blockchain.chain import VotingBlockchain
    
    print("✓ Importing counting modules...")
    from counting.homomorphic import HomomorphicCounter
    from counting.threshold import ElectionAuthorities
    
    print("✓ Importing crypto modules...")
    from crypto.pq_crypto import generate_election_keypair, DilithiumKeyPair
    
    print("\n✅ All imports successful!")
    
    # Test basic initialization
    print("\nTesting initialization...")
    registration = VoterRegistration()
    print("✓ Registration system initialized")
    
    mfa = MultiFactorAuth(registration)
    print("✓ MFA system initialized")
    
    blockchain = VotingBlockchain()
    print("✓ Blockchain initialized")
    
    print("\n✅ All systems operational!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
