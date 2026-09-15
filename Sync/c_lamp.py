import socket
import json  # Menggunakan JSON untuk format pesan

class ProcessB:
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
            self.balance = balance  # Update saldo dengan yang terbaru dari Proses A
            print(f"Received: {message} | Updated balance: {self.balance} | Updated clock: {self.logical_clock}")
        except ValueError:
            print("Error: Received data in unexpected format.")
            return

    def subtract_balance(self, amount):
        self.balance -= amount
        print(f"New balance after subtracting {amount}: {self.balance}")


def main():
    process_b = ProcessB()

    # Membuat socket client dan menghubungkan ke Proses A
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('localhost', 12345))
    print("Connected to Process A")

    # Terima pesan dari Proses A
    process_b.receive_message(client_socket)

    # Kurangi saldo dan kirim pesan ke Proses A
    process_b.subtract_balance(50)
    process_b.send_message(f"Subtract $50", client_socket)

    client_socket.close()

if __name__ == "__main__":
    main()
