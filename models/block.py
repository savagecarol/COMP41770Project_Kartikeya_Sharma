import hashlib
import time
import json


class Block:
    def __init__(self, transactions, previous_hash):
        self.transactions = transactions
        self.timestamp = time.time()
        self.previous_hash = previous_hash
        self.merkle_root = self.build_merkle_root()
        self.nonce = 0
        self.hash = self.compute_hash()

    def compute_hash(self):
        block_data = {
            "transactions": [tx.tx_to_dict() for tx in self.transactions],
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "merkle_root": self.merkle_root,
            "nonce": self.nonce
        }
        block_string = json.dumps(block_data, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def build_merkle_root(self):
        if not self.transactions:
            return ""
        layer = [
            hashlib.sha256(
                json.dumps(tx.tx_to_dict(), sort_keys=True).encode()
            ).hexdigest()
            for tx in self.transactions
        ]

        while len(layer) > 1:
            new_layer = []
            for i in range(0, len(layer), 2):
                left = layer[i]
                right = layer[i + 1] if i + 1 < len(layer) else left
                combined = hashlib.sha256((left + right).encode()).hexdigest()
                new_layer.append(combined)
            layer = new_layer

        return layer[0]

    def mine_block(self, difficulty):
        target = "0" * difficulty
        while True:
            self.hash = self.compute_hash()
            if self.hash.startswith(target):
                print(f"Block mined: {self.hash}")
                break
            self.nonce += 1
    

    def to_dict(self):
        """Serialize the block for broadcasting."""
        return {
            "transactions": [tx.tx_to_dict() for tx in self.transactions],
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "merkle_root": self.merkle_root,
            "nonce": self.nonce,
            "hash": self.hash
        }

    @staticmethod
    def from_dict(data):
        """Reconstruct a Block object from a dict."""
        transactions = [Transaction.from_dict(tx) for tx in data["transactions"]]
        block = Block(transactions, data["previous_hash"])
        block.timestamp = data["timestamp"]
        block.nonce = data["nonce"]
        block.merkle_root = data["merkle_root"]
        block.hash = data["hash"]
        return block