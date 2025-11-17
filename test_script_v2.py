import threading
import time
from models.wallet import Wallet
from models.Miner import Miner
from models.bootstrapNode import BootstrapNode
from utils.constants import MINER_PORT, TRANS_PER_BLOCK
import sys
from logger import start_logging, stop_logging


# Import the logger
sys.path.append('.')
from logger import start_logging, stop_logging

BOOTSTRAP_IP = "127.0.0.1"
BOOTSTRAP_PORT = 5500
NUM_CLIENTS = 10
NUM_TRANSACTIONS = 50

def start_bootstrap():
    print("[BOOTSTRAP NODE] Starting bootstrap node")
    bootstrap = BootstrapNode(BOOTSTRAP_IP, BOOTSTRAP_PORT)
    threading.Thread(target=bootstrap.start, daemon=True).start()
    time.sleep(2)
    print("[BOOTSTRAP NODE] Bootstrap node started successfully")
    return bootstrap

def start_miners():
    print("[TEST] Starting miners")
    miners = []
    for port in MINER_PORT:
        try:
            miner = Miner(BOOTSTRAP_IP, port, BOOTSTRAP_IP, BOOTSTRAP_PORT)
            miner.start()
            miners.append(miner)
            print(f"[MINER {port}] Miner started on port {port}")
            time.sleep(2)
        except OSError as e:
            print(f"[ERROR] Could not start miner on port {port}: {e}")
    
    print("[TEST] Waiting for miners to connect to each other")
    time.sleep(8)
    print("[TEST] Miner connections established")
    return miners

def setup_wallets():
    print("[TEST] Setting up wallets")
    wallets = {}
    for i in range(NUM_CLIENTS):
        client_name = f"Client{i+1}"
        wallet = Wallet(client_name, 100)
        wallet.connect_to_bootstrap(BOOTSTRAP_IP, BOOTSTRAP_PORT)
        wallets[client_name] = wallet
        print(f"[WALLET {client_name}] Wallet connected with balance 100")
        time.sleep(1)
    print("[TEST] All wallets connected")
    return wallets

def simulate_transactions(wallets, miners):
    print("[TEST] Starting transaction simulation")
    clients = list(wallets.keys())
    
    for i in range(NUM_TRANSACTIONS):
        sender = clients[i % NUM_CLIENTS]
        receiver = clients[(i + 1) % NUM_CLIENTS]
        amount = (i % 4) + 1
        
        print(f"[TEST] Transaction {i+1}/{NUM_TRANSACTIONS}: {sender} -> {receiver}, Amount: {amount}")
        success = wallets[sender].send_transaction(receiver, amount)
        
        if success:
            print(f"[WALLET {sender}] Transaction sent successfully to {receiver}")
        else:
            print(f"[ERROR] Transaction failed from {sender} to {receiver}")
        
        time.sleep(1)
        
        if (i + 1) % TRANS_PER_BLOCK == 0:
            print(f"[TEST] Reached {i+1} transactions - pausing for network sync")
            time.sleep(3)
            print_mempools(miners)
            print_blockchains(miners)
            time.sleep(2)

def print_mempools(miners, top_n=5):
    print("[TEST] Checking miner mempools")
    for miner in miners:
        mempool = miner.mempool[:top_n]
        print(f"[MINER {miner.port}] Mempool size: {len(miner.mempool)} transactions")
        for tx in mempool:
            print(f"[MINER {miner.port}] Transaction: {tx.sender} -> {tx.receiver}, Amount: {tx.amount}")

def print_blockchains(miners):
    print("[TEST] Checking miner blockchains")
    for miner in miners:
        print(f"[MINER {miner.port}] Blockchain length: {len(miner.blockchain)} blocks")
        for block in miner.blockchain:
            print(f"[MINER {miner.port}] Block: {block.hash[:16]}... with {len(block.transactions)} transactions")

def mine_block(miner):
    print(f"[TEST] Starting mining process on miner {miner.port}")
    print(f"[MINER {miner.port}] Mempool size before mining: {len(miner.mempool)}")
    
    block = miner.produce_block()
    
    if block:
        print(f"[MINER {miner.port}] Block successfully mined")
        print(f"[MINER {miner.port}] Block hash: {block.hash}")
        print(f"[MINER {miner.port}] Transactions in block: {len(block.transactions)}")
        print("[TEST] Waiting for block to propagate")
        time.sleep(5)
        
        print("[TEST] Blockchain status after mining")
        for m in [miner]:
            print(f"[MINER {m.port}] Blockchain length: {len(m.blockchain)}")
            for idx, b in enumerate(m.blockchain, 1):
                print(f"[MINER {m.port}] Block {idx}: {b.hash[:16]}... with {len(b.transactions)} transactions")
    else:
        print(f"[ERROR] Mining failed on miner {miner.port} - not enough transactions")

def update_wallet_balances(wallets):
    print("[TEST] Updating wallet balances")
    
    for wallet in wallets.values():
        wallet.update_balance()
        time.sleep(0.5)
    
    print("[TEST] Final wallet balances")
    for name, wallet in sorted(wallets.items()):
        print(f"[WALLET {name}] Final balance: {wallet.balance}")

def shutdown(miners, bootstrap):
    print("[TEST] Shutting down system")
    for miner in miners:
        miner.stop()
        print(f"[MINER {miner.port}] Miner stopped")
        time.sleep(0.5)
    
    print("[BOOTSTRAP NODE] Stopping bootstrap node")
    try:
        bootstrap.running = False
        bootstrap.server.close()
    except:
        pass
    
    time.sleep(2)
    print("[TEST] Shutdown complete")

def test_blockchain():
    # Start logging
    logger = start_logging("blockchain_logs.txt")
    
    print("[TEST] Blockchain test starting")
    time.sleep(2)
    
    bootstrap = start_bootstrap()
    time.sleep(2)
    
    miners = start_miners()
    time.sleep(2)
    
    wallets = setup_wallets()
    time.sleep(2)
    
    simulate_transactions(wallets, miners)
    time.sleep(3)
    
    print("[TEST] Final mempool state before mining")
    print_mempools(miners)
    time.sleep(3)
    
    mine_block(miners[0])
    time.sleep(3)
    
    print("[TEST] All miner blockchains")
    print_blockchains(miners)
    time.sleep(2)
    
    update_wallet_balances(wallets)
    time.sleep(2)
    
    shutdown(miners, bootstrap)
    
    # Stop logging
    stop_logging(logger)
    print("[TEST] Log file saved to blockchain_logs.txt")

if __name__ == "__main__":
    print("[TEST] Make sure previous miners/servers are fully stopped")
    time.sleep(2)
    test_blockchain()