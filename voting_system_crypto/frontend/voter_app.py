"""
Voter Client Application
Simple CLI interface for voters
"""
import requests
import json

API_URL = "http://localhost:5000"

class VoterClient:
    """Client for voter interactions"""
    
    def __init__(self):
        self.voter_id = None
        self.private_key = None
        self.session_token = None
    
    def register(self):
        """Register as new voter"""
        print("\n=== VOTER REGISTRATION ===")
        
        voter_id = input("Enter Voter ID: ")
        password = input("Enter Password: ")
        name = input("Enter Name: ")
        
        data = {
            'voter_id': voter_id,
            'password': password,
            'aadhaar': {
                'name': name,
                'dob': '1990-01-01',
                'address': 'Sample Address'
            },
            'face_image': 'simulated_face_data'
        }
        
        response = requests.post(f"{API_URL}/register", json=data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ Registration Successful!")
            print(f"📱 OTP Secret: {result['otp_secret']}")
            print(f"🔑 Private Key: {result['private_key'][:32]}...")
            print(f"📜 Certificate Issued")
            
            self.voter_id = voter_id
            self.private_key = result['private_key']
        else:
            print(f"\n❌ Registration Failed: {response.json()}")
    
    def login(self):
        """Login with MFA"""
        print("\n=== VOTER LOGIN ===")
        
        voter_id = input("Enter Voter ID: ")
        password = input("Enter Password: ")
        otp = input("Enter OTP: ")
        
        data = {
            'voter_id': voter_id,
            'password': password,
            'otp': otp,
            'device': {'browser': 'Chrome', 'os': 'Windows'},
            'face_image': 'simulated_face_data'
        }
        
        response = requests.post(f"{API_URL}/login", json=data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ Login Successful!")
            print(f"🎫 Session Token: {result['session_token'][:32]}...")
            
            self.voter_id = voter_id
            self.session_token = result['session_token']
        else:
            print(f"\n❌ Login Failed: {response.json()}")
    
    def vote(self):
        """Cast vote"""
        print("\n=== CAST VOTE ===")
        
        if not self.private_key:
            self.private_key = input("Enter your Private Key: ")
        
        print("\nCandidates:")
        print("1. Alice")
        print("2. Bob")
        
        choice = input("\nSelect candidate (1 or 2): ")
        candidate_id = "Alice" if choice == "1" else "Bob"
        
        data = {
            'voter_id': self.voter_id,
            'candidate_id': candidate_id,
            'private_key': self.private_key
        }
        
        response = requests.post(f"{API_URL}/vote", json=data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ Vote Submitted!")
            print(f"🧾 Receipt Hash: {result['receipt_hash']}")
            print(f"\n⚠️  Save this receipt to verify your vote later!")
        else:
            print(f"\n❌ Vote Failed: {response.json()}")
    
    def verify(self):
        """Verify vote receipt"""
        print("\n=== VERIFY RECEIPT ===")
        
        receipt_hash = input("Enter Receipt Hash: ")
        
        response = requests.post(f"{API_URL}/verify-receipt", 
                                json={'receipt_hash': receipt_hash})
        
        result = response.json()
        
        if result['verified']:
            print(f"\n✅ Receipt Verified!")
            print(f"📦 Block: {result['blockchain_proof']['block_index']}")
            print(f"⏰ Timestamp: {result['blockchain_proof']['timestamp']}")
        else:
            print(f"\n❌ Receipt Not Found")
    
    def run(self):
        """Main menu"""
        while True:
            print("\n" + "="*50)
            print("🔐 POST-QUANTUM VOTING SYSTEM")
            print("="*50)
            print("1. Register")
            print("2. Login")
            print("3. Vote")
            print("4. Verify Receipt")
            print("5. Exit")
            
            choice = input("\nSelect option: ")
            
            if choice == "1":
                self.register()
            elif choice == "2":
                self.login()
            elif choice == "3":
                self.vote()
            elif choice == "4":
                self.verify()
            elif choice == "5":
                print("\n👋 Goodbye!")
                break

if __name__ == "__main__":
    client = VoterClient()
    client.run()
