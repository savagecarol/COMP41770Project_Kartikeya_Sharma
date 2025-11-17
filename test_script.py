import threading
import time
from models.wallet import Wallet
from models.Miner import Miner
from models.bootstrapNode import BootstrapNode
from utils.constants import MINER_PORT, TRANS_PER_BLOCK

def test_blockchain():
    # -------------------------------
    # Start the bootstrap node
    # -------------------------------
    bootstrap = BootstrapNode("127.0.0.1", 5500)
    bootstrap_thread = threading.Thread(target=bootstrap.start, daemon=True)
    bootstrap_thread.start()
    print("[TEST] Bootstrap node started")
    time.sleep(2)

    # -------------------------------
    # Start miners
    # -------------------------------
    miners = []
    for port in MINER_PORT:
        miner = Miner("127.0.0.1", port, "127.0.0.1", 5500)
        miner.start()
        miners.append(miner)
        print(f"[TEST] Miner started on port {port}")

    # -------------------------------
    # Wait for miners to connect to each other
    # -------------------------------
    print("[TEST] Waiting for all miners to establish connections...")
    time.sleep(5)  # allow connections
    print("[TEST] Miner connections established")

    # -------------------------------
    # Show miner connections
    # -------------------------------
    print("\n======================================")
    print("MINER CONNECTION GRAPH")
    print("======================================")
    for miner in miners:
        print(f"Miner {miner.port}:")
        if len(miner.miner_connections) == 0:
            print("   No connections")
        else:
            for conn in miner.miner_connections:
                try:
                    ip, port = conn.getpeername()
                    print(f"   -> Connected to {ip}:{port}")
                except:
                    print("   -> Bad connection object")
    print("======================================\n")

    # -------------------------------
    # Start wallets
    # -------------------------------
    wallet1 = Wallet("Client1", 100)
    wallet2 = Wallet("Client2", 100)
    wallet1.connect_to_bootstrap("127.0.0.1", 5500)
    wallet2.connect_to_bootstrap("127.0.0.1", 5500)
    print("[TEST] Wallets connected to bootstrap")

    # -------------------------------
    # Send enough transactions to allow mining
    # -------------------------------
    print(f"[TEST] Sending {TRANS_PER_BLOCK} transactions from Client1 to Client2")
    for i in range(TRANS_PER_BLOCK):
        wallet1.send_transaction("Client2", 10)
        time.sleep(0.5)

    # Wait for transaction propagation
    time.sleep(3)

    # -------------------------------
    # Check mempool of all miners
    # -------------------------------
    for miner in miners:
        print(f"[TEST] Mempool of miner {miner.port}: {len(miner.mempool)} tx")
        for tx in miner.mempool:
            print(f"   {tx.sender} -> {tx.receiver}, Amount: {tx.amount}, Fee: {tx.transaction_fees}")

    # -------------------------------
    # Mine a block on the first miner
    # -------------------------------
    print("[TEST] Mining a block on miner", miners[0].port)
    block = miners[0].produce_block()
    time.sleep(3)

    # -------------------------------
    # Check blockchain of all miners
    # -------------------------------
    for miner in miners:
        print(f"[TEST] Blockchain of miner {miner.port}: {len(miner.blockchain)} blocks")
        for block in miner.blockchain:
            print(f"   Block Hash: {block.hash}, Transactions: {len(block.transactions)}")

    # -------------------------------
    # Update wallet balances
    # -------------------------------
    wallet1.update_balance()
    wallet2.update_balance()
    print(f"[TEST] Client1 Balance: {wallet1.balance}")
    print(f"[TEST] Client2 Balance: {wallet2.balance}")

    # -------------------------------
    # Graceful shutdown of miners
    # -------------------------------
    for miner in miners:
        miner.stop()

    print("[TEST] Stopped all miners")

    # -------------------------------
    # Stop bootstrap node
    # -------------------------------
    try:
        bootstrap.running = False
        bootstrap.server.close()
    except:
        pass
    bootstrap_thread.join(timeout=1)
    print("[TEST] Bootstrap stopped, all threads finished")


if __name__ == "__main__":
    test_blockchain()
