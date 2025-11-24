import socket
import threading
import json
import time
import heapq

from models.transaction import Transaction
from models.block import Block
from utils.constants import TRANS_PER_BLOCK, MINING_DIFFICULTY


class Miner:
    def __init__(self, ip, port, bootstrap_ip, bootstrap_port):
        self.ip = ip
        self.port = port
        self.bootstrap_ip = bootstrap_ip
        self.bootstrap_port = bootstrap_port

        self.running = False
        self.wallet_connections = []
        self.miner_connections = []
        self.miner_connections_lock = threading.Lock()
        self.connected_miners = set()

        self.mempool = []
        self.mempool_lock = threading.Lock()

        self.blockchain = []
        self.blockchain_lock = threading.Lock()
        self.last_block_hash = "0" * 64
        self.server_socket = None

        # Mining control
        self.currently_mining = False
        self.mining_lock = threading.Lock()
        self.stop_mining = threading.Event()

    def start(self):
        self.running = True
        self.register_to_bootstrap()
        threading.Thread(target=self.run_server, daemon=True).start()
        threading.Thread(target=self.maintain_miner_connections, daemon=True).start()

        # Wait for connections and sync blockchain
        time.sleep(5)
        self.sync_blockchain_on_startup()

        threading.Thread(target=self.auto_mine, daemon=True).start()

    def sync_blockchain_on_startup(self):
        """Request blockchain from peers when starting"""
        with self.miner_connections_lock:
            if self.miner_connections:
                print(f"[MINER {self.port}] Requesting blockchain from peers...")
                try:
                    self.request_chain_from_peer(self.miner_connections[0])
                    time.sleep(2)
                except:
                    pass

    def auto_mine(self):
        """Continuously attempt to mine blocks"""
        while self.running:
            time.sleep(2)

            # Check if we should mine
            with self.mempool_lock:
                mempool_size = len(self.mempool)

            with self.mining_lock:
                should_mine = (mempool_size >= TRANS_PER_BLOCK and
                               not self.currently_mining)

            if should_mine:
                threading.Thread(target=self.produce_block, daemon=True).start()

    def connect_to_peers(self, miners_list):
        for m in miners_list:
            peer = (m['ip'], m['port'])
            if peer == (self.ip, self.port) or peer in self.connected_miners:
                continue
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect(peer)
                sock.sendall("MINER\n".encode())
                sock.settimeout(None)

                with self.miner_connections_lock:
                    self.miner_connections.append(sock)
                    self.connected_miners.add(peer)

                threading.Thread(target=self.handle_miner, args=(sock,), daemon=True).start()
                print(f"[MINER {self.port}] Connected to miner {peer[1]}")
            except Exception as e:
                print(f"[MINER {self.port}] Failed to connect to {peer[1]}: {e}")

    def run_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.ip, self.port))
        self.server_socket.listen(10)
        print(f"[MINER {self.port}] Listening on {self.ip}:{self.port}")

        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                threading.Thread(target=self.handle_connection, args=(client_socket, addr), daemon=True).start()
            except Exception as e:
                if self.running:
                    print(f"[MINER ERROR] run_server: {e}")

    def handle_connection(self, client_socket, addr):
        """Handle incoming connection - determine if it's a miner or wallet"""
        try:
            client_socket.settimeout(2)

            # Peek at first line without consuming it
            first_data = client_socket.recv(1024, socket.MSG_PEEK).decode()

            if not first_data:
                client_socket.close()
                return

            # Check if it starts with "MINER"
            if first_data.strip().startswith("MINER"):
                # This is a miner connection
                client_socket.recv(1024)  # Consume the "MINER\n" line
                client_socket.settimeout(None)

                with self.miner_connections_lock:
                    self.miner_connections.append(client_socket)
                    peer = (addr[0], addr[1])
                    self.connected_miners.add(peer)

                threading.Thread(target=self.handle_miner, args=(client_socket,), daemon=True).start()
                print(f"[MINER {self.port}] Accepted miner connection from {addr}")
            else:
                # This is a wallet/client connection
                client_socket.settimeout(10)
                threading.Thread(target=self.handle_client, args=(client_socket, addr), daemon=True).start()

        except socket.timeout:
            # Treat timeout as wallet connection
            client_socket.settimeout(10)
            threading.Thread(target=self.handle_client, args=(client_socket, addr), daemon=True).start()
        except Exception as e:
            print(f"[MINER ERROR] handle_connection: {e}")
            try:
                client_socket.close()
            except:
                pass

    def handle_client(self, client_socket, addr):
        """Handle wallet connections - must respond quickly"""
        buffer = ""
        try:
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

                    response = None

                    if request.get("type") == "TRANSACTION":
                        # Add to mempool and broadcast
                        self.add_transaction_to_mempool(line)
                        self.broadcast_transaction(line)
                        response = {"status": "transaction_received"}

                    elif request.get("type") == "GET_BALANCE":
                        balance = self.calculate_balance(request.get("wallet"))
                        response = {"status": "success", "balance": balance}
                    else:
                        response = {"status": "error", "message": "Unknown request type"}

                    # Send response immediately
                    if response:
                        try:
                            client_socket.sendall((json.dumps(response) + "\n").encode())
                        except Exception as e:
                            print(f"[MINER ERROR] Failed to send response: {e}")
                            break

        except socket.timeout:
            pass
        except Exception as e:
            print(f"[MINER ERROR] handle_client: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass

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

            miners_list = response.get("miners", [])
            self.peers = [(m["ip"], m["port"]) for m in miners_list if m["port"] != self.port]
            print(f"[MINER {self.port}] Peers received: {self.peers}")

            s.close()
            threading.Thread(target=self.connect_to_peers, args=(miners_list,), daemon=True).start()

        except Exception as e:
            print(f"[MINER {self.port}] Error registering with bootstrap: {e}")

    def maintain_miner_connections(self):
        time.sleep(3)

        while self.running:
            try:
                miners_list = self.get_miners_from_bootstrap()
                for miner_info in miners_list:
                    ip, port = miner_info["ip"], miner_info["port"]
                    if (ip, port) == (self.ip, self.port):
                        continue
                    if (ip, port) not in self.connected_miners:
                        self.connect_to_miner(ip, port)
                time.sleep(10)
            except Exception as e:
                print(f"[MINER ERROR] maintain_miner_connections: {e}")
                time.sleep(10)

    def connect_to_miner(self, ip, port):
        peer = (ip, port)
        if peer in self.connected_miners:
            return
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect(peer)
            s.sendall("MINER\n".encode())
            s.settimeout(None)

            with self.miner_connections_lock:
                self.miner_connections.append(s)
                self.connected_miners.add(peer)

            threading.Thread(target=self.handle_miner, args=(s,), daemon=True).start()
            print(f"[MINER {self.port}] Connected to miner {ip}:{port}")
        except Exception as e:
            print(f"[MINER ERROR] Failed to connect to miner {ip}:{port}: {e}")

    def get_miners_from_bootstrap(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                sock.connect((self.bootstrap_ip, self.bootstrap_port))
                sock.sendall((json.dumps({"type": "GET_MINERS"}) + "\n").encode())
                data = sock.recv(4096)
            return json.loads(data.decode())
        except:
            return []

    def handle_miner(self, miner_socket):
        """Handle miner-to-miner communication"""
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

                        # Handle chain requests
                        if parsed.get("type") == "REQUEST_CHAIN":
                            self.send_blockchain(miner_socket)

                        # Handle chain responses
                        elif parsed.get("type") == "CHAIN_RESPONSE":
                            received_chain = [Block.from_dict(b) for b in parsed["chain"]]
                            self.replace_chain(received_chain)

                        # Handle blocks
                        elif all(k in parsed for k in ["hash", "previous_hash", "transactions", "nonce"]):
                            if self.add_block_to_chain(parsed):
                                # Re-broadcast to other miners (flood protocol)
                                self.broadcast_block_dict(parsed, exclude_socket=miner_socket)

                        # Handle transactions
                        else:
                            self.add_transaction_to_mempool(message)
                            self.broadcast_transaction(message, exclude_socket=miner_socket)

                    except json.JSONDecodeError:
                        # Try as transaction
                        self.add_transaction_to_mempool(message)
                        self.broadcast_transaction(message, exclude_socket=miner_socket)

        except Exception as e:
            print(f"[MINER ERROR] handle_miner: {e}")
        finally:
            try:
                miner_socket.close()
            except:
                pass

            with self.miner_connections_lock:
                if miner_socket in self.miner_connections:
                    self.miner_connections.remove(miner_socket)

    def add_transaction_to_mempool(self, transaction_json):
        try:
            tx_dict = json.loads(transaction_json)
            if "sender" not in tx_dict or "receiver" not in tx_dict:
                return
            tx = Transaction(tx_dict['sender'], tx_dict['receiver'], tx_dict.get('fee', 0), tx_dict['amount'])

            with self.mempool_lock:
                # Check for duplicates in mempool
                if any(t.sender == tx.sender and t.receiver == tx.receiver and t.amount == tx.amount
                       for t in self.mempool):
                    return

                # Check if transaction already in blockchain
                if self.is_transaction_in_chain(tx):
                    return

                self.mempool.append(tx)
                heapq.heapify(self.mempool)

        except Exception as e:
            print(f"[MINER ERROR] add_transaction_to_mempool: {e}")

    def is_transaction_in_chain(self, tx):
        """Check if transaction already exists in blockchain"""
        with self.blockchain_lock:
            for block in self.blockchain:
                for block_tx in block.transactions:
                    if (block_tx.sender == tx.sender and
                            block_tx.receiver == tx.receiver and
                            block_tx.amount == tx.amount):
                        return True
        return False

    def broadcast_transaction(self, transaction_json, exclude_socket=None):
        """Broadcast transaction to all connected miners"""
        dead_connections = []

        with self.miner_connections_lock:
            connections = list(self.miner_connections)

        for conn in connections:
            if conn != exclude_socket:
                try:
                    conn.sendall((transaction_json + "\n").encode())
                except Exception as e:
                    dead_connections.append(conn)

        # Remove dead connections
        if dead_connections:
            with self.miner_connections_lock:
                for conn in dead_connections:
                    if conn in self.miner_connections:
                        self.miner_connections.remove(conn)

    def produce_block(self):
        with self.mining_lock:
            if self.currently_mining:
                return None
            self.currently_mining = True

        self.stop_mining.clear()

        try:
            with self.mempool_lock:
                if len(self.mempool) < TRANS_PER_BLOCK:
                    with self.mining_lock:
                        self.currently_mining = False
                    return None
                selected_tx = [heapq.heappop(self.mempool) for _ in range(min(TRANS_PER_BLOCK, len(self.mempool)))]

            with self.blockchain_lock:
                new_block = Block(selected_tx, self.last_block_hash)

            print(f"[MINER {self.port}] Mining block with {len(selected_tx)} transactions...")

            # Mine the block with cancellation support
            success = self.mine_block_with_cancel(new_block)

            if not success:
                # Mining was cancelled, return transactions to mempool
                print(f"[MINER {self.port}] Mining cancelled, returning transactions to mempool")
                with self.mempool_lock:
                    for tx in selected_tx:
                        if not self.is_transaction_in_chain(tx):
                            heapq.heappush(self.mempool, tx)
                with self.mining_lock:
                    self.currently_mining = False
                return None

            # Mining succeeded - add to chain
            with self.blockchain_lock:
                # Double-check we're still on same chain
                if new_block.previous_hash != self.last_block_hash:
                    print(f"[MINER {self.port}] Chain changed during mining, discarding block")
                    with self.mempool_lock:
                        for tx in selected_tx:
                            if not self.is_transaction_in_chain(tx):
                                heapq.heappush(self.mempool, tx)
                    with self.mining_lock:
                        self.currently_mining = False
                    return None

                self.blockchain.append(new_block)
                self.last_block_hash = new_block.hash

            # Broadcast to all miners
            self.broadcast_block(new_block)
            print(f"[MINER {self.port}] Successfully mined and broadcast block: {new_block.hash[:16]}...")

            with self.mining_lock:
                self.currently_mining = False
            return new_block

        except Exception as e:
            print(f"[MINER ERROR] produce_block: {e}")
            import traceback
            traceback.print_exc()
            with self.mining_lock:
                self.currently_mining = False
            return None

    def mine_block_with_cancel(self, block):
        """Mine block with ability to cancel - check frequently"""
        target = "0" * MINING_DIFFICULTY

        while not block.hash.startswith(target):
            if self.stop_mining.is_set():
                return False

            block.nonce += 1
            block.hash = block.compute_hash()

            # Check every 100 iterations (more frequent checks)
            if block.nonce % 100 == 0:
                if self.stop_mining.is_set():
                    return False

        print(f"[MINER {self.port}] Block mined: {block.hash}")
        return True

    def add_block_to_chain(self, block_data):
        """Add received block to blockchain with validation"""
        try:
            with self.blockchain_lock:
                # Check for duplicate
                if any(b.hash == block_data["hash"] for b in self.blockchain):
                    return False

                # Reconstruct the block
                transactions = [Transaction.from_dict(tx) for tx in block_data["transactions"]]
                block = Block(transactions, block_data["previous_hash"])
                block.timestamp = block_data["timestamp"]
                block.nonce = block_data["nonce"]
                block.merkle_root = block_data["merkle_root"]
                block.hash = block_data["hash"]

                # Validate the hash
                if block.compute_hash() != block.hash:
                    print(f"[MINER {self.port}] Block rejected: hash mismatch")
                    return False

                # Validate mining difficulty
                if not block.hash.startswith("0" * MINING_DIFFICULTY):
                    print(f"[MINER {self.port}] Block rejected: insufficient difficulty")
                    return False

                # Validate previous hash (chain continuity)
                if block.previous_hash != self.last_block_hash:
                    print(f"[MINER {self.port}] Block has different previous_hash")
                    print(f"[MINER {self.port}] Expected: {self.last_block_hash}, Got: {block.previous_hash}")

                    # If we have no blocks, accept this one
                    if not self.blockchain:
                        print(f"[MINER {self.port}] Empty chain, accepting block")
                    else:
                        # This is a fork - reject it
                        print(f"[MINER {self.port}] Fork detected - rejecting block")
                        return False

                # Stop current mining if in progress
                with self.mining_lock:
                    if self.currently_mining:
                        self.stop_mining.set()
                        print(f"[MINER {self.port}] Stopping current mining due to new block")

                # Remove transactions from mempool
                with self.mempool_lock:
                    tx_hashes_in_block = {
                        json.dumps(tx.tx_to_dict(), sort_keys=True)
                        for tx in block.transactions
                    }
                    self.mempool = [
                        tx for tx in self.mempool
                        if json.dumps(tx.tx_to_dict(), sort_keys=True) not in tx_hashes_in_block
                    ]
                    heapq.heapify(self.mempool)

                # Add to blockchain
                self.blockchain.append(block)
                self.last_block_hash = block.hash
                print(
                    f"[MINER {self.port}] Block accepted: {block.hash[:16]}... (Chain length: {len(self.blockchain)})")

                return True

        except Exception as e:
            print(f"[MINER ERROR] add_block_to_chain: {e}")
            import traceback
            traceback.print_exc()
            return False

    def broadcast_block(self, block):
        """Broadcast newly mined block"""
        block_str = json.dumps(block.to_dict()) + "\n"
        dead_connections = []
        broadcast_count = 0

        with self.miner_connections_lock:
            connections = list(self.miner_connections)

        for conn in connections:
            try:
                conn.sendall(block_str.encode())
                broadcast_count += 1
            except Exception as e:
                print(f"[MINER {self.port}] Failed to broadcast block: {e}")
                dead_connections.append(conn)

        print(f"[MINER {self.port}] Block broadcast to {broadcast_count} miners")

        # Remove dead connections
        if dead_connections:
            with self.miner_connections_lock:
                for conn in dead_connections:
                    if conn in self.miner_connections:
                        self.miner_connections.remove(conn)

    def broadcast_block_dict(self, block_dict, exclude_socket=None):
        """Re-broadcast received block to other miners"""
        block_str = json.dumps(block_dict) + "\n"
        dead_connections = []
        broadcast_count = 0

        with self.miner_connections_lock:
            connections = list(self.miner_connections)

        for conn in connections:
            if conn != exclude_socket:
                try:
                    conn.sendall(block_str.encode())
                    broadcast_count += 1
                except Exception as e:
                    dead_connections.append(conn)

        if broadcast_count > 0:
            print(f"[MINER {self.port}] Re-broadcast block to {broadcast_count} miners")

        # Remove dead connections
        if dead_connections:
            with self.miner_connections_lock:
                for conn in dead_connections:
                    if conn in self.miner_connections:
                        self.miner_connections.remove(conn)

    def validate_chain(self, chain):
        """Validate an entire blockchain"""
        if not chain:
            return True

        # Check genesis block
        if chain[0].previous_hash != "0" * 64:
            return False

        # Validate each block
        for i, block in enumerate(chain):
            # Check hash validity
            if block.compute_hash() != block.hash:
                print(f"[MINER {self.port}] Invalid hash at block {i}")
                return False

            # Check mining difficulty
            if not block.hash.startswith("0" * MINING_DIFFICULTY):
                print(f"[MINER {self.port}] Insufficient difficulty at block {i}")
                return False

            # Check chain linkage
            if i > 0:
                if block.previous_hash != chain[i - 1].hash:
                    print(f"[MINER {self.port}] Chain break at block {i}")
                    return False

        return True

    def replace_chain(self, new_chain):
        """Replace blockchain if new chain is longer and valid"""
        with self.blockchain_lock:
            if len(new_chain) <= len(self.blockchain):
                return False

            if not self.validate_chain(new_chain):
                print(f"[MINER {self.port}] New chain invalid")
                return False

            print(f"[MINER {self.port}] Replacing chain: {len(self.blockchain)} -> {len(new_chain)} blocks")

            # Stop current mining
            with self.mining_lock:
                if self.currently_mining:
                    self.stop_mining.set()

            self.blockchain = new_chain
            self.last_block_hash = new_chain[-1].hash if new_chain else "0" * 64

            # Rebuild mempool
            with self.mempool_lock:
                chain_txs = set()
                for block in self.blockchain:
                    for tx in block.transactions:
                        tx_str = json.dumps(tx.tx_to_dict(), sort_keys=True)
                        chain_txs.add(tx_str)

                self.mempool = [
                    tx for tx in self.mempool
                    if json.dumps(tx.tx_to_dict(), sort_keys=True) not in chain_txs
                ]
                heapq.heapify(self.mempool)

            return True

    def send_blockchain(self, socket):
        """Send blockchain to requesting peer"""
        try:
            with self.blockchain_lock:
                chain_data = {
                    "type": "CHAIN_RESPONSE",
                    "chain": [block.to_dict() for block in self.blockchain]
                }
            socket.sendall((json.dumps(chain_data) + "\n").encode())
        except Exception as e:
            print(f"[MINER ERROR] send_blockchain: {e}")

    def request_chain_from_peer(self, peer_socket):
        """Request blockchain from a peer"""
        try:
            request = {"type": "REQUEST_CHAIN"}
            peer_socket.sendall((json.dumps(request) + "\n").encode())
        except Exception as e:
            print(f"[MINER ERROR] request_chain_from_peer: {e}")

    def calculate_balance(self, wallet_name):
        """Calculate wallet balance from blockchain and mempool"""
        balance = 0

        with self.blockchain_lock:
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
        self.stop_mining.set()

        if self.server_socket:
            try:
                self.server_socket.shutdown(socket.SHUT_RDWR)
            except:
                pass
            try:
                self.server_socket.close()
            except:
                pass

        with self.miner_connections_lock:
            for sock in self.wallet_connections + self.miner_connections:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except:
                    pass
                try:
                    sock.close()
                except:
                    pass