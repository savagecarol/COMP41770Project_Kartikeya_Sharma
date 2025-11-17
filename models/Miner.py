import socket
import threading
import json
import time

from models.transaction import Transaction
from models.block import Block
from utils.constants import TRANS_PER_BLOCK

class Miner:
    def __init__(self, ip, port, bootstrap_ip, bootstrap_port):
        self.ip = ip
        self.port = port
        self.bootstrap_ip = bootstrap_ip
        self.bootstrap_port = bootstrap_port

        self.running = False

        self.wallet_connections = []
        self.miner_connections = []

        self.mempool = []
        self.mempool_lock = threading.Lock()

        self.last_block_hash = "0" * 64  # Genesis prev hash

        self.server_socket = None

    def start(self):
        self.running = True
        self.register_to_bootstrap()
        threading.Thread(target=self.run_server, daemon=True).start()
        threading.Thread(target=self.maintain_miner_connections, daemon=True).start()

    def run_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.ip, self.port))
        self.server_socket.listen(5)
        print(f"[MINER] Listening on {self.ip}:{self.port}")

        while self.running:
            client_socket, addr = self.server_socket.accept()
            connection_type = client_socket.recv(1024).decode().strip()
            if connection_type == "WALLET":
                self.wallet_connections.append(client_socket)
                threading.Thread(target=self.handle_wallet, args=(client_socket,), daemon=True).start()
                print(f"[MINER] Wallet connected from {addr}")
            elif connection_type == "MINER":
                self.miner_connections.append(client_socket)
                threading.Thread(target=self.handle_miner, args=(client_socket,), daemon=True).start()
                print(f"[MINER] Miner connected from {addr}")
            else:
                client_socket.close()
                print(f"[MINER] Unknown connection type from {addr}, closed")

    def register_to_bootstrap(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.bootstrap_ip, self.bootstrap_port))
            registration_msg = json.dumps({
                "type": "REGISTER_MINER",
                "id": f"{self.ip}:{self.port}",
                "ip": self.ip,
                "port": self.port
            }) + "\n"

            sock.sendall(registration_msg.encode())

            # Receive response (optional)
            response = ""
            while True:
                part = sock.recv(1024).decode()
                if not part:
                    break
                response += part
                if "\n" in response:
                    break
            sock.close()
            print(
                f"[MINER] Registered with bootstrap node {self.bootstrap_ip}:{self.bootstrap_port}, response: {response.strip()}")

        except Exception as e:
            print(f"[MINER ERROR] Registering to bootstrap: {e}")

    def maintain_miner_connections(self):
        # Periodically refresh miner list from bootstrap, connect to miners not connected
        while self.running:
            try:
                miners_list = self.get_miners_from_bootstrap()
                # Connect to new miners not already connected
                for miner_info in miners_list:
                    if (miner_info['ip'], miner_info['port']) == (self.ip, self.port):
                        continue  # skip self
                    if not self.is_connected_to(miner_info['ip'], miner_info['port']):
                        self.connect_to_miner(miner_info['ip'], miner_info['port'])
                time.sleep(30)  # refresh every 30 sec
            except Exception as e:
                print(f"[MINER ERROR] maintain_miner_connections: {e}")
                time.sleep(30)

    def get_miners_from_bootstrap(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.bootstrap_ip, self.bootstrap_port))
        request_msg = json.dumps({"type": "GET_MINERS"})
        sock.sendall(request_msg.encode())
        data = sock.recv(4096)
        sock.close()
        miners_list = json.loads(data.decode())
        return miners_list

    def is_connected_to(self, ip, port):
        for s in self.miner_connections:
            try:
                if s.getpeername() == (ip, port):
                    return True
            except:
                pass
        return False

    def connect_to_miner(self, ip, port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((ip, port))
            s.sendall("MINER".encode())  # send connection type
            self.miner_connections.append(s)
            threading.Thread(target=self.handle_miner, args=(s,), daemon=True).start()
            print(f"[MINER] Connected to miner {ip}:{port}")
        except Exception as e:
            print(f"[MINER ERROR] Connecting to miner {ip}:{port} - {e}")

    def handle_wallet(self, wallet_socket):
        try:
            while self.running:
                data = wallet_socket.recv(4096)
                if not data:
                    break
                transaction_json = data.decode()
                self.add_transaction_to_mempool(transaction_json)
                self.broadcast_transaction(transaction_json, exclude_socket=wallet_socket)

                # Send ack response
                response = {"status": "transaction_received"}
                wallet_socket.sendall((json.dumps(response) + "\n").encode())

            wallet_socket.close()
            if wallet_socket in self.wallet_connections:
                self.wallet_connections.remove(wallet_socket)
            print("[MINER] Wallet disconnected")
        except Exception as e:
            print(f"[MINER ERROR] Wallet handler: {e}")

    def handle_miner(self, miner_socket):
        try:
            while self.running:
                data = miner_socket.recv(4096)
                if not data:
                    break
                message = data.decode()
                # Could be transaction or block, parse and handle accordingly
                # For now, assume it's a transaction JSON
                self.add_transaction_to_mempool(message)
                self.broadcast_transaction(message, exclude_socket=miner_socket)
            miner_socket.close()
            if miner_socket in self.miner_connections:
                self.miner_connections.remove(miner_socket)
            print("[MINER] Miner disconnected")
        except Exception as e:
            print(f"[MINER ERROR] Miner handler: {e}")

    def add_transaction_to_mempool(self, transaction_json):
        try:
            tx_dict = json.loads(transaction_json)
            tx = Transaction(
                sender=tx_dict['sender'],
                receiver=tx_dict['receiver'],
                transaction_fees=tx_dict.get('transaction_fees', 0),
                amount=tx_dict['amount']
            )
            with self.mempool_lock:
                self.mempool.append(tx)
            print(f"[MINER] Added transaction to mempool: {tx_dict}")
        except Exception as e:
            print(f"[MINER ERROR] Adding transaction to mempool: {e}")

    def broadcast_transaction(self, transaction_json, exclude_socket=None):
        for conn in self.miner_connections:
            if conn != exclude_socket:
                try:
                    conn.sendall(transaction_json.encode())
                except Exception as e:
                    print(f"[MINER ERROR] Broadcasting transaction: {e}")

    def produce_block(self):
        with self.mempool_lock:
            tx_to_include = self.mempool[:TRANS_PER_BLOCK]
            self.mempool = self.mempool[TRANS_PER_BLOCK:]

        if not tx_to_include:
            print("[MINER] No transactions to include in block")
            return None

        previous_hash = self.last_block_hash
        new_block = Block(tx_to_include, previous_hash)
        print(f"[MINER] Produced new block with {len(tx_to_include)} tx")
        self.last_block_hash = new_block.hash

        self.broadcast_block(new_block)
        return new_block

    def broadcast_block(self, block):
        block_json = {
            "transactions": [tx.tx_to_dict() for tx in block.transactions],
            "timestamp": block.timestamp,
            "previous_hash": block.previous_hash,
            "merkle_root": block.merkle_root,
            "nonce": block.nonce,
            "hash": block.hash
        }
        block_str = json.dumps(block_json)
        for conn in self.miner_connections:
            try:
                conn.sendall(block_str.encode())
            except Exception as e:
                print(f"[MINER ERROR] Broadcasting block: {e}")

    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        for sock in self.wallet_connections + self.miner_connections:
            sock.close()
