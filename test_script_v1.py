import threading
import time
from models.wallet import Wallet
from models.Miner import Miner
from models.bootstrapNode import BootstrapNode
from utils.constants import MINER_PORT, TRANS_PER_BLOCK

BOOTSTRAP_IP = "127.0.0.1"
BOOTSTRAP_PORT = 5500
NUM_CLIENTS = 10
NUM_TRANSACTIONS = 50

def print_separator(title=""):
    """Print a nice separator for better readability"""
    print("\n" + "="*80)
    if title:
        print(f"  {title}")
        print("="*80)
    else:
        print("="*80)

def start_bootstrap():
    print_separator("STARTING BOOTSTRAP NODE")
    bootstrap = BootstrapNode(BOOTSTRAP_IP, BOOTSTRAP_PORT)
    threading.Thread(target=bootstrap.start, daemon=True).start()
    time.sleep(2)
    print("[TEST] Bootstrap node started and ready")
    return bootstrap

def start_miners():
    print_separator("STARTING MINERS")
    miners = []
    for port in MINER_PORT:
        try:
            miner = Miner(BOOTSTRAP_IP, port, BOOTSTRAP_IP, BOOTSTRAP_PORT)
            miner.start()
            miners.append(miner)
            print(f"[TEST] ✓ Miner started on port {port}")
            time.sleep(2)  # Increased delay between miner starts
        except OSError as e:
            print(f"[ERROR] ✗ Could not start miner on port {port}: {e}")
    
    print("\n[TEST] Waiting for miners to connect to each other...")
    time.sleep(8)  # Increased delay for miner connections
    print("[TEST] ✓ Miner connections established\n")
    return miners

def setup_wallets():
    print_separator("SETTING UP WALLETS")
    wallets = {}
    for i in range(NUM_CLIENTS):
        client_name = f"Client{i+1}"
        wallet = Wallet(client_name, 100)
        wallet.connect_to_bootstrap(BOOTSTRAP_IP, BOOTSTRAP_PORT)
        wallets[client_name] = wallet
        print(f"[TEST] ✓ Wallet {client_name} connected (Balance: 100)")
        time.sleep(1)  # Increased delay between wallet setups
    print()
    return wallets

def simulate_transactions(wallets, miners):
    print_separator("SIMULATING TRANSACTIONS")
    clients = list(wallets.keys())
    
    for i in range(NUM_TRANSACTIONS):
        sender = clients[i % NUM_CLIENTS]
        receiver = clients[(i + 1) % NUM_CLIENTS]
        amount = (i % 4) + 1  # always less than 5
        
        print(f"\n[TEST] Transaction {i+1}/{NUM_TRANSACTIONS}: {sender} → {receiver}, Amount: {amount}")
        success = wallets[sender].send_transaction(receiver, amount)
        
        if success:
            print(f"[TEST] ✓ Transaction confirmed")
        else:
            print(f"[TEST] ✗ Transaction failed")
        
        time.sleep(1)  # Increased delay between transactions
        
        # Print status every TRANS_PER_BLOCK transactions
        if (i + 1) % TRANS_PER_BLOCK == 0:
            print(f"\n[TEST] Reached {i+1} transactions - pausing for network sync...")
            time.sleep(3)  # Increased delay for network stability
            print_mempools(miners)
            print_blockchains(miners)
            time.sleep(2)

def print_mempools(miners, top_n=5):
    print_separator("MINER MEMPOOLS STATUS")
    for miner in miners:
        mempool = miner.mempool[:top_n]
        print(f"\n[Miner {miner.port}] Total transactions: {len(miner.mempool)}")
        if mempool:
            for idx, tx in enumerate(mempool, 1):
                print(f"   {idx}. {tx.sender} → {tx.receiver}, Amount: {tx.amount}, Fee: {tx.transaction_fees}")
        else:
            print("   (empty)")

def print_blockchains(miners):
    print_separator("BLOCKCHAIN STATUS")
    for miner in miners:
        print(f"\n[Miner {miner.port}] Blockchain length: {len(miner.blockchain)} blocks")
        if miner.blockchain:
            for idx, block in enumerate(miner.blockchain, 1):
                print(f"   Block {idx}:")
                print(f"      Hash: {block.hash[:16]}...")
                print(f"      Previous: {block.previous_hash[:16]}...")
                print(f"      Transactions: {len(block.transactions)}")
                print(f"      Nonce: {block.nonce}")
        else:
            print("   (no blocks yet)")

def mine_block(miner):
    print_separator(f"MINING BLOCK ON MINER {miner.port}")
    print(f"[TEST] Starting mining process...")
    print(f"[TEST] Mempool size before mining: {len(miner.mempool)}")
    
    block = miner.produce_block()
    
    if block:
        print(f"[TEST] ✓ Block successfully mined!")
        print(f"[TEST] Block hash: {block.hash}")
        print(f"[TEST] Transactions in block: {len(block.transactions)}")
        print(f"\n[TEST] Waiting for block to propagate to other miners...")
        time.sleep(5)  # Increased delay for block propagation
        
        print_separator("BLOCKCHAIN AFTER MINING")
        for m in [miner]:  # Show detailed info for mining miner
            print(f"\n[Miner {m.port}] Blockchain length: {len(m.blockchain)}")
            for idx, b in enumerate(m.blockchain, 1):
                print(f"   Block {idx}: Hash={b.hash[:16]}..., Txs={len(b.transactions)}, Nonce={b.nonce}")
    else:
        print(f"[TEST] ✗ Mining failed - not enough transactions")

def update_wallet_balances(wallets):
    print_separator("UPDATING WALLET BALANCES")
    print("[TEST] Querying miners for final balances...\n")
    
    for wallet in wallets.values():
        wallet.update_balance()
        time.sleep(0.5)
    
    print("\n[TEST] Final Balances:")
    print("-" * 40)
    for name, wallet in sorted(wallets.items()):
        print(f"   {name:12s}: {wallet.balance:6.1f}")
    print("-" * 40)

def shutdown(miners, bootstrap):
    print_separator("SHUTTING DOWN")
    print("[TEST] Stopping all miners...")
    for miner in miners:
        miner.stop()
        time.sleep(0.5)
    
    print("[TEST] Stopping bootstrap node...")
    try:
        bootstrap.running = False
        bootstrap.server.close()
    except:
        pass
    
    time.sleep(2)
    print("[TEST] ✓ Shutdown complete")
    print_separator()

def test_blockchain():
    print("\n" + "╔" + "="*78 + "╗")
    print("║" + " "*20 + "BLOCKCHAIN TEST STARTING" + " "*34 + "║")
    print("╚" + "="*78 + "╝")
    print("\n[INFO] Make sure previous miners/servers are fully stopped!")
    time.sleep(2)
    
    # Start infrastructure
    bootstrap = start_bootstrap()
    time.sleep(2)
    
    miners = start_miners()
    time.sleep(2)
    
    wallets = setup_wallets()
    time.sleep(2)
    
    # Run transactions
    simulate_transactions(wallets, miners)
    time.sleep(3)
    
    # Show final mempool state
    print_separator("FINAL MEMPOOL STATE BEFORE MINING")
    print_mempools(miners)
    time.sleep(3)
    
    # Mine a block
    mine_block(miners[0])
    time.sleep(3)
    
    # Show all blockchains
    print_separator("ALL MINER BLOCKCHAINS")
    print_blockchains(miners)
    time.sleep(2)
    
    # Update balances
    update_wallet_balances(wallets)
    time.sleep(2)
    
    # Shutdown
    shutdown(miners, bootstrap)

if __name__ == "__main__":
    test_blockchain()