"""
Complete Demo of All 9 Phases + ZKP
Demonstrates the entire post-quantum voting flow
"""
import requests
import json
import time

API_URL = "http://localhost:5000"

def print_phase(phase_num, title):
    """Print phase header"""
    print(f"\n{'='*70}")
    print(f"PHASE {phase_num}: {title}")
    print(f"{'='*70}\n")

def demo_complete_flow():
    """Demonstrate complete voting system with all phases"""
    
    print("\n" + "="*70)
    print("POST-QUANTUM VOTING SYSTEM - COMPLETE DEMO")
    print("="*70)
    
    # Check system status
    print("\nChecking system status...")
    response = requests.get(f"{API_URL}/")
    if response.status_code == 200:
        info = response.json()
        print(f"✔ System: {info['system']}")
        print(f"✔ Version: {info['version']}")
        print(f"✔ Phases: {len(info['phases_implemented'])}")
    
    # PHASE 1: REGISTRATION
    print_phase(1, "REGISTRATION - Quantum-Resistant Identity")
    
    voters = []
    for i in range(3):
        voter_id = f"VOTER_{i+1:03d}"
        print(f"\nRegistering {voter_id}...")
        
        data = {
            'voter_id': voter_id,
            'password': f'SecurePass{i+1}!',
            'aadhaar': {
                'name': f'Voter {i+1}',
                'dob': '1990-01-01',
                'address': f'Address {i+1}'
            },
            'face_image': f'face_data_{i+1}'
        }
        
        response = requests.post(f"{API_URL}/register", json=data)
        
        if response.status_code == 200:
            result = response.json()
            voters.append({
                'voter_id': voter_id,
                'password': data['password'],
                'private_key': result['private_key'],
                'otp_secret': result['otp_secret']
            })
            print(f"  ✔ Registered: {voter_id}")
            print(f"  ✔ OTP Secret: {result['otp_secret'][:16]}...")
            print(f"  ✔ Private Key: {result['private_key'][:32]}...")
        else:
            print(f"  ✗ Registration failed: {response.json()}")
    
    # PHASE 2: LOGIN (MFA)
    print_phase(2, "LOGIN - Multi-Factor Authentication")
    
    for voter in voters:
        print(f"\nLogging in {voter['voter_id']}...")
        
        # Generate OTP (simulated)
        import pyotp
        totp = pyotp.TOTP(voter['otp_secret'])
        otp_code = totp.now()
        
        data = {
            'voter_id': voter['voter_id'],
            'password': voter['password'],
            'otp': otp_code,
            'device': {'browser': 'Chrome', 'os': 'Windows'},
            'face_image': f'face_data_{voters.index(voter)+1}'
        }
        
        response = requests.post(f"{API_URL}/login", json=data)
        
        if response.status_code == 200:
            result = response.json()
            voter['session_token'] = result['session_token']
            print(f"  ✔ Login successful")
            print(f"  ✔ Session: {result['session_token'][:32]}...")
        else:
            print(f"  ✗ Login failed: {response.json()}")
    
    # PHASE 3: VOTING (Dilithium + Kyber)
    print_phase(3, "VOTING - Post-Quantum Cryptography")
    
    candidates = ['Alice', 'Bob', 'Charlie']
    votes_cast = []
    
    for i, voter in enumerate(voters):
        candidate = candidates[i % len(candidates)]
        print(f"\n{voter['voter_id']} voting for {candidate}...")
        
        data = {
            'voter_id': voter['voter_id'],
            'candidate_id': candidate,
            'private_key': voter['private_key']
        }
        
        response = requests.post(f"{API_URL}/vote", json=data)
        
        if response.status_code == 200:
            result = response.json()
            votes_cast.append(result)
            print(f"  ✔ Vote submitted")
            print(f"  ✔ Receipt: {result['receipt_hash']}")
            print(f"  ✔ Vote ID: {result['vote_id']}")
            if 'zkp' in result:
                print(f"  ✔ ZKP generated: {result['zkp']['proof_type']}")
        else:
            print(f"  ✗ Vote failed: {response.json()}")
        
        time.sleep(0.5)
    
    # PHASE 6: END-TO-END VERIFICATION
    print_phase(6, "E2E VERIFICATION - Receipt Checking")
    
    for vote in votes_cast:
        print(f"\nVerifying receipt: {vote['receipt_hash'][:16]}...")
        
        data = {'receipt_hash': vote['receipt_hash']}
        response = requests.post(f"{API_URL}/verify-receipt", json=data)
        
        if response.status_code == 200:
            result = response.json()
            if result['verified']:
                print(f"  ✔ Receipt verified")
                print(f"  ✔ In vote system: {result['in_vote_system']}")
                print(f"  ✔ In blockchain: {result['in_blockchain']}")
            else:
                print(f"  ✗ Receipt not found")
        
        time.sleep(0.3)
    
    # Check blockchain status
    print("\nChecking blockchain status...")
    response = requests.get(f"{API_URL}/blockchain")
    if response.status_code == 200:
        result = response.json()
        print(f"  ✔ Total blocks: {result['summary']['total_blocks']}")
        print(f"  ✔ Pending votes: {result['summary']['pending_votes']}")
        print(f"  ✔ Chain integrity: {result['summary']['integrity']}")
    
    # PHASES 4-9: COUNTING
    print_phase("4-9", "COMPLETE COUNTING FLOW")
    print("Executing: Mixnet → Blockchain → Homomorphic → Threshold → Air-Gapped")
    
    data = {'candidates': candidates}
    response = requests.post(f"{API_URL}/count-votes", json=data)
    
    if response.status_code == 200:
        result = response.json()
        
        print(f"\n{'='*70}")
        print("FINAL ELECTION RESULTS")
        print(f"{'='*70}")
        
        for candidate, count in result['results'].items():
            print(f"  {candidate}: {count} votes")
        
        print(f"\n{'='*70}")
        print("SECURITY VERIFICATION")
        print(f"{'='*70}")
        print(f"  ✔ Total votes: {result['total_votes']}")
        print(f"  ✔ Blockchain valid: {result['blockchain_valid']}")
        print(f"  ✔ Mixnet anonymity: {result['mixnet_anonymity']}")
        print(f"  ✔ Vote privacy: {result['vote_privacy']}")
        print(f"  ✔ Authorities used: {', '.join(result['threshold_authorities_used'])}")
        
        print(f"\n{'='*70}")
        print("PHASES COMPLETED")
        print(f"{'='*70}")
        for phase in result['phases_completed']:
            print(f"  ✔ {phase}")
        
        print(f"\n{'='*70}")
        print("DEMO COMPLETE - ALL 9 PHASES EXECUTED SUCCESSFULLY")
        print(f"{'='*70}\n")
    else:
        print(f"\n✗ Counting failed: {response.json()}")

if __name__ == "__main__":
    print("\nStarting complete system demo...")
    print("Make sure the server is running: python run_server.py\n")
    
    try:
        demo_complete_flow()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Cannot connect to server")
        print("Please start the server first: python run_server.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
