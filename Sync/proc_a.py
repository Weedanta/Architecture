import socket

class ProcessA:
    def __init__(self):
        self.balance = 1000  # Saldo awal

    def send_message(self, message, conn):
        conn.sendall(message.encode())
        print(f"Sent: {message}")

    def receive_message(self, conn):
        data = conn.recv(1024).decode()
        print(f"Received: {data}")

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
    process_a.send_message(f"Add $100 - New balance: {process_a.balance}", conn)

    # Terima pesan dari Proses B
    process_a.receive_message(conn)

    conn.close()

if __name__ == "__main__":
    main()
