from flask import Flask
import threading
import time

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
    # Run on all interfaces, port 5000 (Replit requirement)
    app.run(host='0.0.0.0', port=5000, debug=False)

def keep_alive():
    """Start the keep-alive server in a separate thread"""
    print("Starting keep-alive server...")
    
    # Create and start the server thread
    server_thread = threading.Thread(target=run)
    server_thread.daemon = True  # Dies when main thread dies
    server_thread.start()
    
    print("Keep-alive server started on http://0.0.0.0:5000")
    
    # Give the server a moment to start
    time.sleep(1)

if __name__ == "__main__":
    # If running directly, start the server
    run()
