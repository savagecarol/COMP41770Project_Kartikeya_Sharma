import socket
import random
import json
import time


class Wallet:
    def __init__(self, owner, balance=100):
        self.owner = owner
        self.received_transactions = []
        self.sent_transactions = []
        self.balance = balance
        self.initial_balance = balance  # Store initial balance
        self.miners = []

    def connect_to_bootstrap(self, host, port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((host, port))
                request = json.dumps({"type": "GET_MINERS"}) + "\n"
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
        """Connect to miner WITHOUT sending connection type (wallet connections don't identify)"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10)
            s.connect((miner["ip"], miner["port"]))
            # DON'T send "WALLET\n" - wallets just send requests directly
            print(f"[WALLET] Connected to miner at {miner['ip']}:{miner['port']}")
            return s
        except Exception as e:
            print(f"[WALLET ERROR] Could not connect to miner: {e}")
            return None

    def update_balance(self):
        """Update wallet balance by querying a miner"""
        miner = self.select_miner()
        if not miner:
            return False

        try:
            sock = self.connect_to_miner(miner)
            if not sock:
                return False

            # Send balance query
            query = {
                "type": "GET_BALANCE",
                "wallet": self.owner
            }
            sock.sendall((json.dumps(query) + "\n").encode())

            # Receive response
            data = sock.recv(4096).decode().strip()
            if not data:
                print("[WALLET ERROR] Empty response from miner")
                sock.close()
                return False

            try:
                response = json.loads(data)
            except json.JSONDecodeError:
                print(f"[WALLET ERROR] Malformed response from miner: {data}")
                sock.close()
                return False

            if response.get("status") == "success":
                blockchain_balance = response.get("balance", 0)
                # Balance = initial balance + blockchain balance (transactions)
                self.balance = self.initial_balance + blockchain_balance
                print(f"[WALLET] Updated balance for {self.owner}: {self.balance}")
                sock.close()
                return True
            else:
                print(f"[WALLET] Error getting balance: {response.get('message')}")
                sock.close()
                return False

        except Exception as e:
            print(f"[WALLET ERROR] Updating balance: {e}")
            try:
                sock.close()
            except:
                pass
            return False

    def get_balance(self):
        """Get current balance (with update)"""
        self.update_balance()
        return self.balance

    def send_transaction(self, receiver, amount):
        """Send a transaction to another wallet"""
        if amount <= 0:
            print("[WALLET] Amount must be positive")
            return False

        # Update balance before sending
        self.update_balance()

        if self.balance < amount:
            print(f"[WALLET] Insufficient funds. Balance: {self.balance}, Amount: {amount}")
            return False

        miner = self.select_miner()
        if not miner:
            return False

        try:
            sock = self.connect_to_miner(miner)
            if not sock:
                return False

            tx = {
                "type": "TRANSACTION",
                "sender": self.owner,
                "receiver": receiver,
                "amount": amount,
                "fee": 0
            }
            sock.sendall((json.dumps(tx) + "\n").encode())
            print(f"[WALLET] Sent transaction: {tx}")

            # Receive response
            data = sock.recv(4096).decode().strip()
            if not data:
                print("[WALLET ERROR] Empty response from miner")
                sock.close()
                return False

            try:
                response = json.loads(data)
                print(f"[WALLET] Received response: {response}")
            except json.JSONDecodeError:
                print(f"[WALLET ERROR] Malformed response from miner: {data}")
                sock.close()
                return False

            if response.get("status") == "transaction_received":
                # Update local records
                self.sent_transactions.append({
                    "receiver": receiver,
                    "amount": amount,
                    "timestamp": time.time()
                })
                self.balance -= amount
                print(f"[WALLET] Transaction sent successfully: {self.owner} -> {receiver}: {amount}")
                sock.close()
                return True
            else:
                print(f"[WALLET] Error sending transaction: {response.get('message')}")
                sock.close()
                return False

        except Exception as e:
            print(f"[WALLET ERROR] Sending transaction: {e}")
            try:
                sock.close()
            except:
                pass
            return False