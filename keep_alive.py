from flask import Flask
import threading
import time
import os

# Create Flask app
app = Flask(__name__)

@app.route('/')
def home():
    """Home route to keep the server alive"""
    return "Discord bot is running! 🤖"

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Discord bot keep-alive server is running",
        "timestamp": time.time()
    }

@app.route('/ping')
def ping():
    """Simple ping endpoint"""
    return "pong"

def run():
    """Run the Flask server"""
    # Render provides PORT env var, default to 5000 if not set
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

def keep_alive():
    """Start the keep-alive server in a separate thread"""
    print("Starting keep-alive server...")

    server_thread = threading.Thread(target=run)
    server_thread.daemon = True  # dies when main thread dies
    server_thread.start()

    print(f"Keep-alive server started on port {os.getenv('PORT', 5000)}")

    # Give the server a moment to start
    time.sleep(1)
