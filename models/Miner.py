# /Users/apple/Documents/ucd/blockchain/models/Miner.py
import socket
import threading
import json
import time
import heapq

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

        self.mempool = []  # Will function as a priority queue
        self.mempool_lock = threading.Lock()

        self.blockchain = []  # Store the blockchain
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
            try:
                connection_type = client_socket.recv(1024).decode().strip()
                print(f"[MINER] Received connection type: {connection_type} from {addr}")
                if connection_type == "WALLET":
                    self.wallet_connections.append(client_socket)
                    threading.Thread(target=self.handle_wallet, args=(client_socket,), daemon=True).start()
                    print(f"[MINER] Wallet connected from {addr}")
                elif connection_type == "MINER":
                    self.miner_connections.append(client_socket)
                    threading.Thread(target=self.handle_miner, args=(client_socket,), daemon=True).start()
                    print(f"[MINER] Miner connected from {addr}")
                else:
                    print(f"[MINER] Unknown connection type from {addr}, closed")
                    client_socket.close()
            except Exception as e:
                print(f"[MINER ERROR] Error handling connection from {addr}: {e}")
                client_socket.close()

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
            s.sendall("MINER\n".encode())  # send connection type with newline
            self.miner_connections.append(s)
            threading.Thread(target=self.handle_miner, args=(s,), daemon=True).start()
            print(f"[MINER] Connected to miner {ip}:{port}")
        except Exception as e:
            print(f"[MINER ERROR] Connecting to miner {ip}:{port} - {e}")

    def handle_wallet(self, wallet_socket):
        try:
            # Receive and validate the connection type
            connection_type = wallet_socket.recv(1024).decode().strip()
            print(f"[MINER] Received connection type: {connection_type}")
            if connection_type != "WALLET":
                print(f"[MINER] Unknown connection type from wallet, closing connection")
                wallet_socket.close()
                return

            # Process subsequent JSON payloads
            buffer = ""
            while True:
                data = wallet_socket.recv(4096).decode()
                if not data:
                    break
                buffer += data
                
                # Process complete messages (separated by newlines)
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        request = json.loads(line)
                        print(f"[MINER] Received request: {request}")
                    except json.JSONDecodeError:
                        response = {"status": "error", "message": "Invalid JSON"}
                        wallet_socket.sendall((json.dumps(response) + "\n").encode())
                        continue
                    
                    # Handle different request types
                    if request.get("type") == "TRANSACTION":
                        self.add_transaction_to_mempool(line)
                        self.broadcast_transaction(line, exclude_socket=wallet_socket)
                        response = {"status": "transaction_received"}
                    
                    elif request.get("type") == "GET_BLOCKCHAIN":
                        blockchain_data = [
                            {
                                "transactions": [tx.tx_to_dict() for tx in block.transactions],
                                "timestamp": block.timestamp,
                                "previous_hash": block.previous_hash,
                                "merkle_root": block.merkle_root,
                                "nonce": block.nonce,
                                "hash": block.hash
                            }
                            for block in self.blockchain
                        ]
                        response = {"status": "success", "blockchain": blockchain_data}
                    
                    elif request.get("type") == "GET_MEMPOOL":
                        with self.mempool_lock:
                            sorted_mempool = sorted(self.mempool, reverse=True)
                            mempool_data = [tx.tx_to_dict() for tx in sorted_mempool]
                        response = {"status": "success", "mempool": mempool_data}
                    
                    elif request.get("type") == "GET_BALANCE":
                        wallet_name = request.get("wallet")
                        balance = self.calculate_balance(wallet_name)
                        response = {"status": "success", "balance": balance}
                    
                    else:
                        response = {"status": "error", "message": "Unknown command type"}
                    
                    print(f"[MINER] Sending response: {response}")
                    wallet_socket.sendall((json.dumps(response) + "\n").encode())
        except Exception as e:
            print(f"[MINER ERROR] Wallet handler: {e}")
        finally:
            wallet_socket.close()

    def handle_miner(self, miner_socket):
        try:
            buffer = ""
            while self.running:
                data = miner_socket.recv(4096)
                if not data:
                    break
                buffer += data.decode()
                
                # Process complete messages (separated by newlines)
                while "\n" in buffer:
                    message, buffer = buffer.split("\n", 1)
                    message = message.strip()
                    if not message:
                        continue
                        
                    # Try to parse as JSON to determine if it's a block or transaction
                    try:
                        parsed_data = json.loads(message)
                        # Check if it's a block by looking for block-specific fields
                        if all(key in parsed_data for key in ["hash", "previous_hash", "transactions", "nonce"]):
                            # This is a block
                            self.add_block_to_chain(parsed_data)
                        else:
                            # This is a transaction
                            self.add_transaction_to_mempool(message)
                            self.broadcast_transaction(message, exclude_socket=miner_socket)
                    except json.JSONDecodeError:
                        # Assume it's a transaction if not valid JSON for a block
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
            # Skip if it's not a transaction (e.g., if it's a block)
            if "sender" not in tx_dict or "receiver" not in tx_dict:
                print("[MINER] Invalid transaction format, skipping")
                return
                
            tx = Transaction(
                sender=tx_dict['sender'],
                receiver=tx_dict['receiver'],
                transaction_fees=tx_dict.get('fee', 0),  # Use 'fee' field from client
                amount=tx_dict['amount']
            )
            with self.mempool_lock:
                # Check if transaction already exists to avoid duplicates
                for existing_tx in self.mempool:
                    if (existing_tx.sender == tx.sender and 
                        existing_tx.receiver == tx.receiver and 
                        existing_tx.amount == tx.amount):
                        print("[MINER] Duplicate transaction, skipping")
                        return  # Transaction already exists
                        
                # Add to mempool and maintain heap property
                self.mempool.append(tx)
                heapq.heapify(self.mempool)  # Re-heapify to maintain priority
            print(f"[MINER] Added transaction to mempool: {tx_dict}")
        except Exception as e:
            print(f"[MINER ERROR] Adding transaction to mempool: {e}")

    def broadcast_transaction(self, transaction_json, exclude_socket=None):
        disconnected_sockets = []
        for conn in self.miner_connections:
            if conn != exclude_socket:
                try:
                    conn.sendall((transaction_json + "\n").encode())  # Ensure newline
                    print(f"[MINER] Broadcasted transaction to miner {conn.getpeername()}")
                except Exception as e:
                    print(f"[MINER ERROR] Broadcasting transaction: {e}")
                    disconnected_sockets.append(conn)
        
        # Remove disconnected sockets
        for sock in disconnected_sockets:
            if sock in self.miner_connections:
                self.miner_connections.remove(sock)

    def produce_block(self):
        # Only mine if we have enough transactions
        with self.mempool_lock:
            if len(self.mempool) < 2:  # Require at least 2 transactions
                print("[MINER] Not enough transactions to mine a block (need at least 2)")
                return None
                
            # Select transactions with highest fees (up to TRANS_PER_BLOCK)
            selected_transactions = []
            temp_mempool = self.mempool.copy()  # Work with a copy
            
            # Extract transactions in priority order (highest fees first)
            heapq.heapify(temp_mempool)
            count = 0
            while temp_mempool and count < TRANS_PER_BLOCK:
                tx = heapq.heappop(temp_mempool)
                selected_transactions.append(tx)
                count += 1
            
            # Remove selected transactions from actual mempool
            for tx in selected_transactions:
                self.mempool.remove(tx)

        if not selected_transactions:
            print("[MINER] No transactions to include in block")
            return None

        previous_hash = self.last_block_hash
        new_block = Block(selected_transactions, previous_hash)
        print(f"[MINER] Produced new block with {len(selected_transactions)} tx")
        self.last_block_hash = new_block.hash
        
        # Add block to our blockchain
        self.blockchain.append(new_block)

        self.broadcast_block(new_block)
        return new_block

    def add_block_to_chain(self, block_data):
        try:
            # Check if block already exists in blockchain
            for existing_block in self.blockchain:
                if existing_block.hash == block_data["hash"]:
                    return  # Block already exists
                    
            transactions = [Transaction.from_dict(tx_data) for tx_data in block_data["transactions"]]
            new_block = Block(transactions, block_data["previous_hash"])
            new_block.timestamp = block_data["timestamp"]
            new_block.merkle_root = block_data["merkle_root"]
            new_block.nonce = block_data["nonce"]
            new_block.hash = block_data["hash"]
            
            # Validate the block before adding
            if new_block.previous_hash != self.last_block_hash and len(self.blockchain) > 0:
                print(f"[MINER] Block rejected - invalid previous hash: {new_block.previous_hash}")
                return
                
            self.blockchain.append(new_block)
            self.last_block_hash = new_block.hash
            print(f"[MINER] Added new block to chain: {new_block.hash}")
        except Exception as e:
            print(f"[MINER ERROR] Adding block to chain: {e}")

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
        
        disconnected_sockets = []
        for conn in self.miner_connections:
            try:
                conn.sendall((block_str + "\n").encode())  # Ensure newline
            except Exception as e:
                print(f"[MINER ERROR] Broadcasting block: {e}")
                disconnected_sockets.append(conn)
        
        # Remove disconnected sockets
        for sock in disconnected_sockets:
            if sock in self.miner_connections:
                self.miner_connections.remove(sock)

    def calculate_balance(self, wallet_name):
        balance = 0
        
        # Calculate from blockchain
        for block in self.blockchain:
            for tx in block.transactions:
                if tx.sender == wallet_name:
                    balance -= tx.amount
                if tx.receiver == wallet_name:
                    balance += tx.amount
                    
        # Calculate from mempool
        with self.mempool_lock:
            for tx in self.mempool:
                if tx.sender == wallet_name:
                    balance -= tx.amount
                if tx.receiver == wallet_name:
                    balance += tx.amount
                    
        return balance

    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        for sock in self.wallet_connections + self.miner_connections:
            try:
                sock.close()
            except:
                pass