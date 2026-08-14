"""
Client Launcher
Run from project root
"""
import sys
import os

# Add frontend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'frontend'))

from voter_app import VoterClient

if __name__ == '__main__':
    client = VoterClient()
    client.run()
