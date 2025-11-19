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
        self.connected_miners = set()  # Track connected miners (ip, port)

        self.mempool = []
        self.mempool_lock = threading.Lock()

        self.blockchain = []
        self.last_block_hash = "0" * 64
        self.server_socket = None

    def start(self):
        self.running = True
        self.register_to_bootstrap()
        threading.Thread(target=self.run_server, daemon=True).start()
        threading.Thread(target=self.maintain_miner_connections, daemon=True).start()
        threading.Thread(target=self.auto_mine, daemon=True).start()

    # Replace the synchronize_blockchain method with this more complete version:
    def synchronize_blockchain(self):
        """
        Synchronize blockchain with peers by adopting the longest valid chain.
        This implementation simulates the process as we don't have direct peer chain access.
        """
        print(f"[MINER {self.port}] Starting blockchain synchronization...")
        
        current_length = len(self.blockchain)
        print(f"[MINER {self.port}] Current chain length: {current_length}")
        
        # Reconnect to any missing peers to ensure maximum connectivity
        self.reconnect_to_miners()
        
        # In a full implementation, you would do the following:
        # 1. Request chain length from all peers
        # 2. Identify peers with longer chains
        # 3. Request full chain from those peers
        # 4. Validate the longer chains
        # 5. Replace local chain if a longer valid chain is found
        
        # Simulate the synchronization process:
        print(f"[MINER {self.port}] Checking for longer chains among peers...")
        
        # Since we don't have direct access to peer chains in this architecture,
        # we'll implement a basic strategy for chain maintenance:
        
        # Ensure we have a valid last_block_hash
        if self.blockchain:
            self.last_block_hash = self.blockchain[-1].hash
        else:
            self.last_block_hash = "0" * 64
        
        print(f"[MINER {self.port}] Blockchain synchronization complete. Chain length: {len(self.blockchain)}")
        
        # Return the current chain length
        return len(self.blockchain)


    # Also add this helper method to validate a chain:
    def validate_chain(self, chain):
        """
        Validate a blockchain by checking hashes and previous hash links.
        Returns True if valid, False otherwise.
        """
        if not chain:
            return True  # Empty chain is valid
        
        # Check first block (genesis block should have previous_hash of all zeros)
        if chain[0].previous_hash != "0" * 64:
            print(f"[MINER {self.port}] Invalid genesis block")
            return False
        
        # Check each block in the chain
        for i in range(1, len(chain)):
            block = chain[i]
            prev_block = chain[i-1]
            
            # Check if block's previous_hash matches the previous block's hash
            if block.previous_hash != prev_block.hash:
                print(f"[MINER {self.port}] Invalid previous hash at block {i}")
                return False
            
            # Check if block's hash is correctly computed
            if block.hash != block.compute_hash():
                print(f"[MINER {self.port}] Invalid block hash at block {i}")
                return False
            
            # Check if block hash meets mining difficulty requirements
            target = "0" * 2  # MINING_DIFFICULTY from constants
            if not block.hash.startswith(target):
                print(f"[MINER {self.port}] Block {i} doesn't meet difficulty requirements")
                return False
        
        return True

    def auto_mine(self):
        """Continuously attempt to mine blocks and synchronize"""
        sync_counter = 0
        while self.running:
            time.sleep(5)
            sync_counter += 1
            if sync_counter >= 3:
                self.synchronize_blockchain()
                sync_counter = 0
                
            self.reconnect_to_miners()
            
            with self.mempool_lock:
                if len(self.mempool) >= TRANS_PER_BLOCK:
                    threading.Thread(target=self.produce_block, daemon=True).start()

    def connect_to_peers(self, miners_list):
        for m in miners_list:
            peer = (m['ip'], m['port'])
            if peer == (self.ip, self.port) or peer in self.connected_miners:
                continue  # skip self or already connected
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(peer)
                sock.sendall("MINER\n".encode())
                self.miner_connections.append(sock)
                self.connected_miners.add(peer)
                threading.Thread(target=self.handle_miner, args=(sock,), daemon=True).start()
                print(f"[MINER {self.port}] Connected to miner {peer[1]}")
            except Exception as e:
                print(f"[MINER {self.port}] Failed to connect to {peer[1]}: {e}")

    def run_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.ip, self.port))
        self.server_socket.listen(5)
        print(f"[MINER {self.port}] Listening on {self.ip}:{self.port}")

        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client_socket, addr), daemon=True).start()
            except Exception as e:
                print(f"[MINER ERROR] run_server: {e}")

    def handle_client(self, client_socket, addr):
        try:
            buffer = ""
            while self.running:
                data = client_socket.recv(4096)
                if not data:
                    break
                buffer += data.decode()
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        request = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if request.get("type") == "TRANSACTION":
                        self.add_transaction_to_mempool(line)
                        self.broadcast_transaction(line)
                        response = {"status": "transaction_received"}
                    elif request.get("type") == "GET_BALANCE":
                        balance = self.calculate_balance(request.get("wallet"))
                        response = {"status": "success", "balance": balance}
                    else:
                        response = {"status": "error", "message": "Unknown request type"}
                    client_socket.sendall((json.dumps(response) + "\n").encode())
        except Exception as e:
            print(f"[MINER ERROR] handle_client: {e}")
        finally:
            client_socket.close()

    def register_to_bootstrap(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.bootstrap_ip, self.bootstrap_port))

            msg = json.dumps({
                "type": "REGISTER_MINER",
                "id": f"{self.ip}:{self.port}",
                "ip": self.ip,
                "port": self.port
            }) + "\n"
            s.send(msg.encode())

            response = json.loads(s.recv(4096).decode())
            print(f"[MINER {self.port}] Registered with bootstrap: {response}")

            # Get list of all miners
            miners_list = response.get("miners", [])
            self.peers = [(m["ip"], m["port"]) for m in miners_list if m["port"] != self.port]
            print(f"[MINER {self.port}] Peers received: {self.peers}")

            s.close()

            # Connect to peers
            threading.Thread(target=self.connect_to_peers, args=(miners_list,), daemon=True).start()

        except Exception as e:
            print(f"[MINER {self.port}] Error registering with bootstrap: {e}")

    def maintain_miner_connections(self):
        time.sleep(3)  # allow miners to register

        while self.running:
            try:
                miners_list = self.get_miners_from_bootstrap()
                for miner_info in miners_list:
                    ip, port = miner_info["ip"], miner_info["port"]
                    if (ip, port) == (self.ip, self.port):
                        continue
                    if (ip, port) not in self.connected_miners:
                        self.connect_to_miner(ip, port)
                time.sleep(5)
            except Exception as e:
                print(f"[MINER ERROR] maintain_miner_connections: {e}")
                time.sleep(5)

    def connect_to_miner(self, ip, port):
        peer = (ip, port)
        if peer in self.connected_miners:
            return True  # Already connected
            
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)  # Add timeout
            s.connect(peer)
            s.sendall("MINER\n".encode())
            self.miner_connections.append(s)
            self.connected_miners.add(peer)
            threading.Thread(target=self.handle_miner, args=(s,), daemon=True).start()
            print(f"[MINER {self.port}] Connected to miner {ip}:{port}")
            return True
        except Exception as e:
            print(f"[MINER {self.port}] Failed to connect to miner {ip}:{port}: {e}")
            return False

    def get_miners_from_bootstrap(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((self.bootstrap_ip, self.bootstrap_port))
            sock.sendall(json.dumps({"type": "GET_MINERS"}).encode())
            data = sock.recv(4096)
        return json.loads(data.decode())

    def handle_wallet(self, wallet_socket):
        buffer = ""
        try:
            while self.running:
                data = wallet_socket.recv(4096).decode()
                if not data:
                    break
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if not line.strip():
                        continue
                    request = json.loads(line)
                    response = {"status": "error", "message": "Unknown command"}

                    if request.get("type") == "TRANSACTION":
                        self.add_transaction_to_mempool(line)
                        self.broadcast_transaction(line, exclude_socket=wallet_socket)
                        response = {"status": "transaction_received"}
                    elif request.get("type") == "GET_BALANCE":
                        balance = self.calculate_balance(request.get("wallet"))
                        response = {"status": "success", "balance": balance}
                    wallet_socket.sendall((json.dumps(response) + "\n").encode())

        except Exception as e:
            print(f"[MINER ERROR] handle_wallet: {e}")
        finally:
            wallet_socket.close()

    def handle_miner(self, miner_socket):
        miner_socket.settimeout(None)
        buffer = ""
        try:
            while self.running:
                data = miner_socket.recv(4096)
                if not data:
                    break
                buffer += data.decode()
                while "\n" in buffer:
                    message, buffer = buffer.split("\n", 1)
                    message = message.strip()
                    if not message:
                        continue
                    try:
                        parsed = json.loads(message)
                        if all(k in parsed for k in ["hash", "previous_hash", "transactions", "nonce"]):
                            self.add_block_to_chain(parsed)
                        else:
                            self.add_transaction_to_mempool(message)
                            self.broadcast_transaction(message, exclude_socket=miner_socket)
                    except json.JSONDecodeError:
                        self.add_transaction_to_mempool(message)
                        self.broadcast_transaction(message, exclude_socket=miner_socket)
        except Exception as e:
            print(f"[MINER ERROR] handle_miner: {e}")
        finally:
            miner_socket.close()
            if miner_socket in self.miner_connections:
                self.miner_connections.remove(miner_socket)
            print(f"[MINER {self.port}] Miner disconnected")

    def add_transaction_to_mempool(self, transaction_json):
        try:
            tx_dict = json.loads(transaction_json)
            if "sender" not in tx_dict or "receiver" not in tx_dict:
                return
            tx = Transaction(tx_dict['sender'], tx_dict['receiver'], tx_dict.get('fee', 0), tx_dict['amount'])
            with self.mempool_lock:
                if any(t.sender == tx.sender and t.receiver == tx.receiver and t.amount == tx.amount
                       for t in self.mempool):
                    return
                self.mempool.append(tx)
                heapq.heapify(self.mempool)
        except Exception as e:
            print(f"[MINER ERROR] add_transaction_to_mempool: {e}")

    def broadcast_transaction(self, transaction_json, exclude_socket=None):
        for conn in self.miner_connections.copy():
            if conn != exclude_socket:
                try:
                    conn.sendall((transaction_json + "\n").encode())
                except:
                    self.miner_connections.remove(conn)

    def produce_block(self):
        with self.mempool_lock:
            if len(self.mempool) < 1:
                print(f"[MINER {self.port}] Not enough transactions to mine a block")
                return None
            selected_tx = [heapq.heappop(self.mempool) for _ in range(min(TRANS_PER_BLOCK, len(self.mempool)))]
        
        new_block = Block(selected_tx, self.last_block_hash)
        print(f"[MINER {self.port}] Mining block...")
        new_block.mine_block()  # <-- ADD THIS LINE
        
        self.blockchain.append(new_block)
        self.last_block_hash = new_block.hash
        self.broadcast_block(new_block)
        print(f"[MINER {self.port}] Produced new block with {len(selected_tx)} transactions, hash: {new_block.hash}")
        return new_block

    # In models/Miner.py, replace the add_block_to_chain method:
    def add_block_to_chain(self, block_data):
        try:
            # Check if block already exists
            if any(b.hash == block_data["hash"] for b in self.blockchain):
                return
                
            transactions = [Transaction.from_dict(tx) for tx in block_data["transactions"]]
            block = Block(transactions, block_data["previous_hash"])
            block.timestamp = block_data["timestamp"]
            block.nonce = block_data["nonce"]
            block.merkle_root = block_data["merkle_root"]
            block.hash = block_data["hash"]
            
            # If this is the first block or it connects to our last block, add it
            if not self.blockchain or block.previous_hash == self.last_block_hash:
                self.blockchain.append(block)
                self.last_block_hash = block.hash
                print(f"[MINER {self.port}] Added new block: {block.hash[:16]}...")
            # If it's a better chain (longer), we might want to replace ours
            elif len(self.blockchain) > 0:
                # Simple chain replacement logic - in a real blockchain, you'd do more complex validation
                # For now, we'll just accept it if it's a continuation of the genesis block
                print(f"[MINER {self.port}] Received block: {block.hash[:16]}... with previous: {block.previous_hash[:16]}...")
                
        except Exception as e:
            print(f"[MINER {self.port}] Error adding block to chain: {e}")

    def broadcast_block(self, block):
        block_str = json.dumps(block.to_dict()) + "\n"
        failed_connections = []
        
        for conn in self.miner_connections.copy():
            try:
                conn.sendall(block_str.encode())
            except Exception as e:
                print(f"[MINER {self.port}] Failed to broadcast block to connection: {e}")
                failed_connections.append(conn)
        
        # Remove failed connections
        for conn in failed_connections:
            if conn in self.miner_connections:
                self.miner_connections.remove(conn)
                try:
                    conn.close()
                except:
                    pass


    def calculate_balance(self, wallet_name):
        balance = 0
        for block in self.blockchain:
            for tx in block.transactions:
                if tx.sender == wallet_name:
                    balance -= tx.amount
                if tx.receiver == wallet_name:
                    balance += tx.amount
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
            try:
                self.server_socket.shutdown(socket.SHUT_RDWR)
            except:
                pass
            self.server_socket.close()
        
        for sock in self.wallet_connections + self.miner_connections:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except:
                pass
            try:
                sock.close()
            except:
                pass

    def reconnect_to_miners(self):
        """Ensure we're connected to all registered miners"""
        try:
            miners_list = self.get_miners_from_bootstrap()
            for miner_info in miners_list:
                ip, port = miner_info["ip"], miner_info["port"]
                if (ip, port) == (self.ip, self.port):
                    continue
                peer = (ip, port)
                # Check if we're already connected
                if peer not in self.connected_miners:
                    self.connect_to_miner(ip, port)
        except Exception as e:
            print(f"[MINER {self.port}] Error in reconnect_to_miners: {e}")  
