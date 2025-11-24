from flask import Flask
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import sys
from datetime import datetime
import threading

from test_script_v2 import test_blockchain, stop_test

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Keep a global reference to the test thread ---
test_thread = None

class WebSocketLogger:
    # Same as before, intercepts print, emits logs, etc.
    def __init__(self):
        self.original_stdout = sys.stdout
        self.buffer = []

    def write(self, text):
        self.original_stdout.write(text)
        text = text.strip()
        if text and '[' in text and ']' in text:
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            log_entry = {
                'timestamp': timestamp,
                'message': text,
                'full': f"[{timestamp}] {text}"
            }
            socketio.emit('log', log_entry, namespace='/')

    def flush(self):
        self.original_stdout.flush()

    def close(self):
        sys.stdout = self.original_stdout

logger = None

def start_logging():
    global logger
    logger = WebSocketLogger()
    sys.stdout = logger
    print("[WEBSOCKET] Logging started - broadcasting to clients")
    return logger

def stop_logging():
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
    global test_thread
    if test_thread and test_thread.is_alive():
        emit('test_error', {'message': 'Test is already running'})
        return

    print("[WEBSOCKET] Starting blockchain test...")
    emit('test_started', {'message': 'Blockchain test initiated'})

    def run_test():
        try:
            start_logging()
            test_blockchain()
            stop_logging()
            socketio.emit('test_completed', {'message': 'Test completed successfully'})
        except Exception as e:
            print(f"[ERROR] Test failed: {str(e)}")
            socketio.emit('test_error', {'message': f'Test failed: {str(e)}'})

    test_thread = threading.Thread(target=run_test)
    test_thread.daemon = True
    test_thread.start()

@socketio.on('stop_test')
def handle_stop_test():
    global test_thread
    if not test_thread or not test_thread.is_alive():
        emit('test_error', {'message': 'No test is currently running'})
        return

    print("[WEBSOCKET] Stop test signal received")
    stop_test()  # Signal to stop the test in Python code
    test_thread.join(timeout=10)  # Wait up to 10 seconds for test thread to finish

    if test_thread.is_alive():
        emit('test_error', {'message': 'Test did not stop in time'})
    else:
        emit('test_stopped', {'message': 'Test stopped successfully'})
        print("[WEBSOCKET] Test stopped successfully")

@app.route('/health')
def health():
    return {'status': 'running', 'message': 'Blockchain logger is active'}

if __name__ == '__main__':
    print("[SERVER] Starting Flask-SocketIO server on http://localhost:5000")
    socketio.run(app, host='0.0.0.0', port=5400, debug=True, allow_unsafe_werkzeug=True)
