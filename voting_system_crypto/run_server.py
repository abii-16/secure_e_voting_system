"""
Server Launcher
Run from project root
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Import and run server
from server import app

if __name__ == '__main__':
    print("🔐 Post-Quantum Voting System Started")
    print("📡 Server running on http://localhost:5000")
    app.run(debug=True, port=5000)
