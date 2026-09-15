import socket
import json  # Menggunakan JSON untuk format pesan

class ProcessA:
    def __init__(self):
        self.logical_clock = 0
        self.balance = 1000  # Saldo awal

    def increment_clock(self):
        self.logical_clock += 1

    def send_message(self, message, conn):
        self.increment_clock()
        message_dict = {
            "message": message,
            "balance": self.balance,
            "timestamp": self.logical_clock
        }
        message_with_timestamp = json.dumps(message_dict)  # Convert ke JSON
        conn.sendall(message_with_timestamp.encode())
        print(f"Sent: {message_with_timestamp}")

    def receive_message(self, conn):
        data = conn.recv(1024).decode()
        print(f"Raw received data: {data}")  # Debugging line
        try:
            message_dict = json.loads(data)  # Parse JSON
            message = message_dict["message"]
            balance = message_dict["balance"]
            timestamp = message_dict["timestamp"]
            self.logical_clock = max(self.logical_clock, timestamp) + 1
            self.balance = balance  # Update saldo dengan yang terbaru dari Proses B
            print(f"Received: {message} | Updated balance: {self.balance} | Updated clock: {self.logical_clock}")
        except ValueError:
            print("Error: Received data in unexpected format.")
            return

    def add_balance(self, amount):
        self.balance += amount
        print(f"New balance after adding {amount}: {self.balance}")


def main():
    process_a = ProcessA()

    # Membuat socket server
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('localhost', 12345))
    server_socket.listen(1)
    print("Process A is listening...")

    conn, addr = server_socket.accept()
    print(f"Connected by {addr}")

    # Tambah saldo dan kirim pesan ke Proses B
    process_a.add_balance(100)
    process_a.send_message(f"Add $100", conn)

    # Terima pesan dari Proses B
    process_a.receive_message(conn)

    conn.close()

if __name__ == "__main__":
    main()
