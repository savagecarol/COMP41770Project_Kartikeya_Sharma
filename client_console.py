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

def main():
    print("\nClient console ready. Enter commands:")
    print("1: send transaction")
    print("2: show blockchain (from miner)")
    print("3: show mempool (from miner)")
    print("4: exit\n")

    while True:
        cmd = input("Enter command: ").strip()

        if cmd == "1":
            sender = input("Sender wallet name: ")
            receiver = input("Receiver wallet name: ")
            amount = float(input("Amount: "))

            tx_command = {
                "type": "TRANSACTION",
                "sender": sender,
                "receiver": receiver,
                "amount": amount,
                "fee": 0
            }

            miner_ip = "127.0.0.1"
            miner_port = int(input("Miner port to send to: "))

            response = send_command_to_miner(tx_command, miner_ip, miner_port)
            print("Miner response:", response)

        elif cmd == "2":
            miner_ip = "127.0.0.1"
            miner_port = int(input("Miner port to query blockchain from: "))

            query_command = {"type": "GET_BLOCKCHAIN"}

            response = send_command_to_miner(query_command, miner_ip, miner_port)
            print("Blockchain data:", response)

        elif cmd == "3":
            miner_ip = "127.0.0.1"
            miner_port = int(input("Miner port to query mempool from: "))

            query_command = {"type": "GET_MEMPOOL"}

            response = send_command_to_miner(query_command, miner_ip, miner_port)
            print("Mempool data:", response)

        elif cmd == "4":
            print("Exiting client.")
            break

        else:
            print("Unknown command.")

if __name__ == "__main__":
    main()
