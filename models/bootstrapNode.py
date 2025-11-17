import socket
import threading
import json

from utils.constants import QUEUED_CONNECTION


class BootstrapNode:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.registered_miners = {}
        self.lock = threading.Lock()
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = True

    def start(self):
        self.server.bind((self.host, self.port))
        self.server.listen(QUEUED_CONNECTION)
        print(f"[BOOTSTRAP NODE] Listening on {self.host}:{self.port}")

        while self.running:
            client_socket, addr = self.server.accept()
            threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()

    def handle_client(self, client_socket):
        try:
            request = self.receive_json_line(client_socket)
            if not request:
                client_socket.close()
                return

            req_type = request.get("type")

            if req_type == "REGISTER_MINER":
                miner_id = request.get("id")
                ip = request.get("ip")
                port = request.get("port")
                with self.lock:
                    self.registered_miners[miner_id] = (ip, port)
                response = {"status": "registered"}
                self.send_json_line(client_socket, response)
                print(f"[BOOTSTRAP NODE] Miner registered: {miner_id} @ {ip}:{port}")

            elif req_type == "get_miners":
                with self.lock:
                    miners_list = [{"ip": ip, "port": port} for ip, port in self.registered_miners.values()]
                self.send_json_line(client_socket, miners_list)
                print(f"[BOOTSTRAP NODE] Sent miners list to client")

            else:
                self.send_json_line(client_socket, {"error": "unknown request"})

            client_socket.close()
        except Exception as e:
            print(f"[BOOTSTRAP NODE ERROR] {e}")
            client_socket.close()

    def receive_json_line(self, sock):
        buffer = ""
        while True:
            data = sock.recv(1024).decode()
            if not data:
                break
            buffer += data
            if "\n" in buffer:
                line, _ = buffer.split("\n", 1)
                return json.loads(line.strip())
        return None

    def send_json_line(self, sock, data):
        message = json.dumps(data) + "\n"
        sock.sendall(message.encode())
