import sys


class WebSocketLogger:
    """
    Intercepts all print() statements for WebSocket broadcasting.
    This is a simplified version that just intercepts stdout.
    The actual broadcasting is handled by the Flask app.
    """

    def __init__(self):
        self.original_stdout = sys.stdout

    def write(self, text):
        """Intercept all print statements"""
        # Always write to console (which Flask will capture)
        self.original_stdout.write(text)

    def flush(self):
        """Required for file-like object"""
        self.original_stdout.flush()

    def close(self):
        """Restore original stdout"""
        sys.stdout = self.original_stdout


def start_logging(filename=None):
    """
    Start capturing print statements.
    Filename parameter is kept for compatibility but ignored.
    """
    logger = WebSocketLogger()
    sys.stdout = logger
    print(f"[WEBSOCKET] Logging started - broadcasting to clients")
    return logger


def stop_logging(logger):
    """
    Stop logging and restore stdout.
    """
    if logger:
        logger.close()
    print(f"[WEBSOCKET] Logging stopped")