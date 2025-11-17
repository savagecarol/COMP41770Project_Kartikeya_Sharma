import threading
import time
from models.Miner import Miner
from models.bootstrapNode import BootstrapNode
from models.wallet import Wallet
from utils.constants import MINER_PORT

def start_bootstrap():
    bootstrap = BootstrapNode("127.0.0.1", 5500)
    threading.Thread(target=bootstrap.start, daemon=True).start()
    print("[NODES] Bootstrap node started")
    return bootstrap

def start_miners():
    miners = []
    for i, port in enumerate(MINER_PORT, start=1):
        miner = Miner("127.0.0.1", port, "127.0.0.1", 5500)
        miner.start()
        miners.append(miner)
        print(f"[NODES] Miner {i} started on port {port}")
    return miners

def start_wallets():
    wallets = []
    for i in range(1, 6):
        wallet = Wallet(f"Client{i}")
        wallet.connect_to_bootstrap("127.0.0.1", 5500)
        wallets.append(wallet)
        print(f"[NODES] Wallet Client{i} started")
    return wallets

def start_mining_loop(miner):
    def mining_loop():
        while miner.running:
            block = miner.produce_block()
            if block:
                print(f"[NODES] Miner on port {miner.port} mined a block with hash: {block.hash}")
            time.sleep(10)

    threading.Thread(target=mining_loop, daemon=True).start()

def run_nodes():
    bootstrap = start_bootstrap()
    time.sleep(3)
    miners = start_miners()
    time.sleep(3)
    wallets = start_wallets()

    for miner in miners:
        start_mining_loop(miner)

    while True:
        time.sleep(1)

if __name__ == "__main__":
    run_nodes()
