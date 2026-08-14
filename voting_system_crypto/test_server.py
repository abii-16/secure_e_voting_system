"""
Test server startup
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

print("Starting test server...")

try:
    from flask import Flask
    
    app = Flask(__name__)
    
    @app.route('/')
    def home():
        return {'status': 'Server is running!'}
    
    @app.route('/test')
    def test():
        return {'message': 'Test endpoint works!'}
    
    print("✅ Flask app created successfully")
    print("Starting server on http://localhost:5000")
    print("Try visiting: http://localhost:5000/ or http://localhost:5000/test")
    
    app.run(debug=True, port=5000)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
