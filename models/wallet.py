import socket
import random
import json

class Wallet:
    def __init__(self, owner):
        self.owner = owner
        self.received_transactions = []
        self.miners = []

    def connect_to_bootstrap(self, host, port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((host, port))
                request = json.dumps({"type": "get_miners"}) + "\n"
                s.sendall(request.encode())

                data = ""
                while True:
                    part = s.recv(4096).decode()
                    if not part:
                        break
                    data += part
                    if "\n" in data:
                        line, _ = data.split("\n", 1)
                        self.miners = json.loads(line.strip())
                        break

                print(f"[WALLET] Miners received: {self.miners}")
        except Exception as e:
            print(f"[WALLET ERROR] Could not connect to bootstrap: {e}")

    def select_miner(self):
        if not self.miners:
            print("[WALLET] No miners available.")
            return None
        miner = random.choice(self.miners)
        print(f"[WALLET] Selected miner: {miner}")
        return miner

    def connect_to_miner(self, miner):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((miner["ip"], miner["port"]))
            print(f"[WALLET] Connected to miner {miner['ip']}:{miner['port']}")
            return s
        except Exception as e:
            print(f"[WALLET ERROR] Could not connect to miner: {e}")
            return None

    # ... rest of Wallet code here (add_transaction, wallet_loop, etc.) ...
