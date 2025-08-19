import os
import time
import threading
import logging
from flask import Flask

# Disable Flask's default request logging (keeps console clean)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Create Flask app
app = Flask(__name__)

@app.route('/')
def home():
    """Home route to keep the server alive"""
    return "Discord bot is running on Render! 🤖"

@app.route('/health')
def health_check():
    """Health check endpoint (for UptimeRobot or monitoring)"""
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
    port = int(os.environ.get("PORT", 5000))  # Render provides PORT
    app.run(host="0.0.0.0", port=port, debug=False)

def keep_alive():
    """Start the keep-alive server in a separate thread"""
    print("Starting keep-alive server...")

    # Create and start the server thread
    server_thread = threading.Thread(target=run)
    server_thread.daemon = True  # Dies when main thread dies
    server_thread.start()

    print(f"Keep-alive server started on port {os.environ.get('PORT', 5000)}")

    # Give the server a moment to start
    time.sleep(1)

if __name__ == "__main__":
    # If running directly, start the server
    run()
