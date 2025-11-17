import sys
from datetime import datetime

class PrintToFileLogger:
    """
    Intercepts all print() statements and saves only lines containing [] to a file.
    Also prints to console normally.
    """
    
    def __init__(self, filename="blockchain_logs.txt"):
        self.filename = filename
        self.original_stdout = sys.stdout
        self.file = open(filename, 'w')
        
        # Write header
        self.file.write(f"=== Blockchain Logs - Started at {datetime.now()} ===\n")
        self.file.flush()
    
    def write(self, text):
        """Intercept all print statements"""
        # Always write to console
        self.original_stdout.write(text)
        
        # Only write to file if line contains []
        text = text.strip()
        if text and '[' in text and ']' in text:
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            self.file.write(f"[{timestamp}] {text}\n")
            self.file.flush()
    
    def flush(self):
        """Required for file-like object"""
        self.original_stdout.flush()
        self.file.flush()
    
    def close(self):
        """Close the file"""
        self.file.close()
        sys.stdout = self.original_stdout


def start_logging(filename="blockchain_logs.txt"):
    """
    Start capturing print statements to file.
    Call this at the START of your main script.
    """
    logger = PrintToFileLogger(filename)
    sys.stdout = logger
    print(f"[TEST] Logging started - saving to {filename}")
    return logger

def stop_logging(logger):
    """
    Stop logging and close file.
    Call this at the END of your script.
    """
    logger.close()
    print(f"[TEST] Logging stopped")