import socket
import threading
import json

from utils.constants import QUEUED_CONNECTION

class BootstrapNode:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.registered_miners = {}  # Key: (ip, port), Value: {"ip": ip, "port": port}
        self.lock = threading.Lock()
        self.running = True
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def start(self):
        self.server.bind((self.host, self.port))
        self.server.listen(QUEUED_CONNECTION)
        print(f"[BOOTSTRAP NODE] Listening on {self.host}:{self.port}")

        self.server.settimeout(1)
        while self.running:
            try:
                client_socket, addr = self.server.accept()
                threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()
            except socket.timeout:
                continue
            except OSError:
                break

    def handle_client(self, client_socket):
        try:
            request = self.receive_json_line(client_socket)
            if not request:
                client_socket.close()
                return

            req_type = request.get("type")

            if req_type == "REGISTER_MINER":
                ip = request.get("ip")
                port = request.get("port")
                key = (ip, port)
                with self.lock:
                    self.registered_miners[key] = {"ip": ip, "port": port}
                response = {
                    "status": "registered",
                    "miners": list(self.registered_miners.values())
                }
                self.send_json_line(client_socket, response)
                print(f"[BOOTSTRAP NODE] Miner registered: {ip}:{port}")

            elif req_type == "GET_MINERS":
                with self.lock:
                    miners_list = list(self.registered_miners.values())
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
            try:
                data = sock.recv(1024).decode()
                if not data:
                    break
                buffer += data
                if "\n" in buffer:
                    line, _ = buffer.split("\n", 1)
                    return json.loads(line.strip())
            except Exception:
                break
        return None

    def send_json_line(self, sock, data):
        message = json.dumps(data) + "\n"
        try:
            sock.sendall(message.encode())
        except Exception as e:
            print(f"[BOOTSTRAP NODE ERROR] send_json_line: {e}")
