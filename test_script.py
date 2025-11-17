import threading  # Add this import
import time
from models.wallet import Wallet
from models.Miner import Miner
from models.bootstrapNode import BootstrapNode
from utils.constants import MINER_PORT

def test_blockchain():
    # Start the bootstrap node
    bootstrap = BootstrapNode("127.0.0.1", 5500)
    bootstrap_thread = threading.Thread(target=bootstrap.start, daemon=True)
    bootstrap_thread.start()
    print("[TEST] Bootstrap node started")
    time.sleep(2)

    # Start miners
    miners = []
    for port in MINER_PORT:
        miner = Miner("127.0.0.1", port, "127.0.0.1", 5500)
        miner.start()
        miners.append(miner)
        print(f"[TEST] Miner started on port {port}")
    time.sleep(5)

    # Start wallets
    wallet1 = Wallet("Client1", 100)  # Explicitly set balance to 100
    wallet2 = Wallet("Client2", 100)  # Explicitly set balance to 100
    wallet1.connect_to_bootstrap("127.0.0.1", 5500)
    wallet2.connect_to_bootstrap("127.0.0.1", 5500)
    print("[TEST] Wallets connected to bootstrap")

    # Send a transaction from wallet1 to wallet2
    print("[TEST] Sending transaction from Client1 to Client2")
    if wallet1.send_transaction("Client2", 10):
        print("[TEST] Transaction sent successfully")
    else:
        print("[TEST] Transaction failed")
    time.sleep(5)  # Allow time for miners to process the transaction

    # Check mempool of all miners
    for miner in miners:
        print(f"[TEST] Checking mempool of miner on port {miner.port}")
        mempool = miner.mempool
        print(f"Mempool size: {len(mempool)}")
        for tx in mempool:
            print(f"Transaction: {tx.sender} -> {tx.receiver}, Amount: {tx.amount}, Fee: {tx.transaction_fees}")

    # Mine a block on the first miner
    print("[TEST] Mining a block on the first miner")
    miners[0].produce_block()
    time.sleep(5)

    # Check blockchain of all miners
    for miner in miners:
        print(f"[TEST] Checking blockchain of miner on port {miner.port}")
        blockchain = miner.blockchain
        print(f"Blockchain size: {len(blockchain)}")
        for block in blockchain:
            print(f"Block Hash: {block.hash}, Transactions: {len(block.transactions)}")

    # Check wallet balances
    print("[TEST] Checking wallet balances")
    wallet1.update_balance()
    wallet2.update_balance()
    print(f"Client1 Balance: {wallet1.balance}")
    print(f"Client2 Balance: {wallet2.balance}")

    # Stop all miners
    for miner in miners:
        miner.stop()
    print("[TEST] Stopped all miners")

    # Wait for all threads to finish
    bootstrap_thread.join()
    for miner in miners:
        miner.running = False
    print("[TEST] All threads stopped")

if __name__ == "__main__":
    test_blockchain()
