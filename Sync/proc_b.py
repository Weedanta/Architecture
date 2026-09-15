import socket

class ProcessB:
    def __init__(self):
        self.balance = 1000  # Saldo awal

    def send_message(self, message, conn):
        conn.sendall(message.encode())
        print(f"Sent: {message}")

    def receive_message(self, conn):
        data = conn.recv(1024).decode()
        print(f"Received: {data}")

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
    process_b.send_message(f"Subtract $50 - New balance: {process_b.balance}", client_socket)

    client_socket.close()

if __name__ == "__main__":
    main()
