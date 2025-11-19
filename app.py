from flask import Flask
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import sys
from datetime import datetime
import threading

from test_script_v2 import test_blockchain

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")


class WebSocketLogger:
    """
    Intercepts all print() statements and broadcasts them via WebSocket.
    Also prints to console normally.
    """

    def __init__(self):
        self.original_stdout = sys.stdout
        self.buffer = []

    def write(self, text):
        """Intercept all print statements"""
        # Always write to console
        self.original_stdout.write(text)

        # Only broadcast to WebSocket if line contains []
        text = text.strip()
        if text and '[' in text and ']' in text:
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            log_entry = {
                'timestamp': timestamp,
                'message': text,
                'full': f"[{timestamp}] {text}"
            }

            # Broadcast to all connected clients
            socketio.emit('log', log_entry, namespace='/')

    def flush(self):
        """Required for file-like object"""
        self.original_stdout.flush()

    def close(self):
        """Restore original stdout"""
        sys.stdout = self.original_stdout


# Global logger instance
logger = None


def start_logging():
    """Start capturing print statements and broadcasting via WebSocket"""
    global logger
    logger = WebSocketLogger()
    sys.stdout = logger
    print("[WEBSOCKET] Logging started - broadcasting to clients")
    return logger


def stop_logging():
    """Stop logging and restore stdout"""
    global logger
    if logger:
        logger.close()
        print("[WEBSOCKET] Logging stopped")


@socketio.on('connect')
def handle_connect():
    print(f"[WEBSOCKET] Client connected")
    emit('connected', {'message': 'Connected to blockchain logger'})


@socketio.on('disconnect')
def handle_disconnect():
    print(f"[WEBSOCKET] Client disconnected")


@socketio.on('start_test')
def handle_start_test():
    """Trigger to start the blockchain test"""
    print("[WEBSOCKET] Starting blockchain test...")
    emit('test_started', {'message': 'Blockchain test initiated'})

    # Import and run your test in a separate thread
    def run_test():
        try:
            start_logging()
            test_blockchain()

            # Stop logging
            stop_logging()

            socketio.emit('test_completed', {'message': 'Test completed successfully'})
        except Exception as e:
            print(f"[ERROR] Test failed: {str(e)}")
            socketio.emit('test_error', {'message': f'Test failed: {str(e)}'})

    # Run in background thread
    thread = threading.Thread(target=run_test)
    thread.daemon = True
    thread.start()


@app.route('/health')
def health():
    return {'status': 'running', 'message': 'Blockchain logger is active'}


if __name__ == '__main__':
    print("[SERVER] Starting Flask-SocketIO server on http://localhost:5000")
    socketio.run(app, host='0.0.0.0', port=5400, debug=True, allow_unsafe_werkzeug=True)