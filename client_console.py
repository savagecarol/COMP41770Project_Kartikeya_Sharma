import json
import socket

def send_command_to_miner(command_json, miner_ip, miner_port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((miner_ip, miner_port))
            s.sendall(b"WALLET\n")
            s.sendall(json.dumps(command_json).encode() + b"\n")
            data = ""
            while True:
                part = s.recv(1024).decode()
                if not part:
                    break
                data += part
                if "\n" in data:
                    line, _ = data.split("\n", 1)
                    return json.loads(line)
    except Exception as e:
        print(f"Error communicating with miner: {e}")
        return None

def display_blockchain(blocks):
    if not blocks:
        print("Blockchain is empty")
        return
        
    print(f"\nBlockchain ({len(blocks)} blocks):")
    print("-" * 50)
    for i, block in enumerate(blocks):
        print(f"Block #{i}:")
        print(f"  Hash: {block['hash'][:16]}...")
        print(f"  Previous Hash: {block['previous_hash'][:16]}...")
        print(f"  Timestamp: {block['timestamp']}")
        print(f"  Nonce: {block['nonce']}")
        print(f"  Merkle Root: {block['merkle_root'][:16]}...")
        print(f"  Transactions ({len(block['transactions'])}):")
        for j, tx in enumerate(block['transactions']):
            print(f"    {j+1}. {tx['sender']} -> {tx['receiver']}: {tx['amount']} (Fee: {tx['transaction_fees']})")
        print()

def display_mempool(mempool):
    if not mempool:
        print("Mempool is empty")
        return
        
    print(f"\nMempool ({len(mempool)} transactions):")
    print("-" * 30)
    for i, tx in enumerate(mempool):
        print(f"{i+1}. {tx['sender']} -> {tx['receiver']}: {tx['amount']} (Fee: {tx['transaction_fees']})")
    print()

def main():
    print("\nClient console ready. Enter commands:")
    print("1: send transaction")
    print("2: show blockchain (from miner)")
    print("3: show mempool (from miner)")
    print("4: check balance")
    print("5: exit\n")

    while True:
        cmd = input("Enter command: ").strip()

        if cmd == "1":
            sender = input("Sender wallet name: ")
            receiver = input("Receiver wallet name: ")
            amount = float(input("Amount: "))
            fee = float(input("Transaction fee: "))

            tx_command = {
                "type": "TRANSACTION",
                "sender": sender,
                "receiver": receiver,
                "amount": amount,
                "fee": fee
            }

            miner_ip = "127.0.0.1"
            miner_port = int(input("Miner port to send to: "))

            response = send_command_to_miner(tx_command, miner_ip, miner_port)
            if response:
                print("Miner response:", response)
            else:
                print("Failed to communicate with miner")

        elif cmd == "2":
            miner_ip = "127.0.0.1"
            miner_port = int(input("Miner port to query blockchain from: "))

            query_command = {"type": "GET_BLOCKCHAIN"}

            response = send_command_to_miner(query_command, miner_ip, miner_port)
            if response and response.get("status") == "success":
                display_blockchain(response.get("blockchain", []))
            elif response:
                print("Error:", response)
            else:
                print("Failed to communicate with miner")

        elif cmd == "3":
            miner_ip = "127.0.0.1"
            miner_port = int(input("Miner port to query mempool from: "))

            query_command = {"type": "GET_MEMPOOL"}

            response = send_command_to_miner(query_command, miner_ip, miner_port)
            if response and response.get("status") == "success":
                display_mempool(response.get("mempool", []))
            elif response:
                print("Error:", response)
            else:
                print("Failed to communicate with miner")

        elif cmd == "4":
            wallet_name = input("Wallet name: ")
            miner_ip = "127.0.0.1"
            miner_port = int(input("Miner port to query: "))

            query_command = {
                "type": "GET_BALANCE",
                "wallet": wallet_name
            }

            response = send_command_to_miner(query_command, miner_ip, miner_port)
            if response and response.get("status") == "success":
                print(f"Balance for {wallet_name}: {response.get('balance', 0)}")
            elif response:
                print("Error:", response)
            else:
                print("Failed to communicate with miner")

        elif cmd == "5":
            print("Exiting client.")
            break

        else:
            print("Unknown command.")

if __name__ == "__main__":
    main()