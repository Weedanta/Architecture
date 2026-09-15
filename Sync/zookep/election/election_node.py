# leader_election_periodic_check_fixed.py

from kazoo.client import KazooClient
from kazoo.exceptions import NodeExistsError
import time
import sys
import threading

# Konfigurasi ZooKeeper
ZOOKEEPER_SERVERS = '127.0.0.1:2181'
ELECTION_NODE = '/leader_election_priority'

class LeaderElection:
    def __init__(self, zk, node_id, check_interval=5):
        self.zk = zk
        self.node_id = node_id
        self.node_name = f"node-{node_id}"
        self.node_path = f"{ELECTION_NODE}/{self.node_name}"
        self.is_leader = False
        self.leader_thread = None
        self.stop_event = threading.Event()
        self.check_interval = check_interval  # Interval pengecekan dalam detik

    def get_node_priority(self, node_name):
        """
        Mengambil priority dari node berdasarkan node_id.
        """
        try:
            node_id = int(node_name.split('-')[1])
            return node_id
        except (IndexError, ValueError):
            return 0

    def get_sorted_children(self):
        """
        Mendapatkan daftar child nodes yang diurutkan berdasarkan priority (descending).
        """
        children = self.zk.get_children(ELECTION_NODE)
        sorted_children = sorted(children, key=lambda x: self.get_node_priority(x), reverse=True)
        return sorted_children

    def determine_leader(self):
        """
        Menentukan apakah node saat ini adalah pemimpin.
        """
        sorted_children = self.get_sorted_children()
        leader_node = sorted_children[0] if sorted_children else None
        if leader_node == self.node_name:
            return True, leader_node
        else:
            return False, leader_node

    def leader_task(self):
        """
        Tugas yang dijalankan oleh pemimpin.
        """
        print(f"[{self.node_id}] Saya adalah pemimpin sekarang. Melakukan tugas pemimpin...")
        try:
            while not self.stop_event.is_set():
                print(f"[{self.node_id}] Melakukan tugas pemimpin...")
                time.sleep(5)
        except KeyboardInterrupt:
            print(f"[{self.node_id}] Menghentikan tugas pemimpin.")
        finally:
            self.is_leader = False

    def run_leader_task(self):
        """
        Menjalankan tugas pemimpin dalam thread terpisah.
        """
        if not self.leader_thread or not self.leader_thread.is_alive():
            self.stop_event.clear()
            self.leader_thread = threading.Thread(target=self.leader_task)
            self.leader_thread.start()

    def stop_leader_task(self):
        """
        Menghentikan tugas pemimpin jika node tidak lagi menjadi pemimpin.
        """
        if self.is_leader:
            self.stop_event.set()
            if self.leader_thread:
                self.leader_thread.join()
            self.is_leader = False

    def evaluate_leader(self):
        """
        Mengevaluasi status pemimpin dan menjalankan atau menghentikan tugas pemimpin sesuai kebutuhan.
        """
        is_leader, leader_node = self.determine_leader()
        if is_leader:
            if not self.is_leader:
                print(f"[{self.node_id}] Saya sekarang pemimpin.")
                self.is_leader = True
                self.run_leader_task()
        else:
            if self.is_leader:
                print(f"[{self.node_id}] Saya tidak lagi pemimpin. Pemimpin sekarang: {leader_node}")
                self.stop_leader_task()
            print(f"[{self.node_id}] Pemimpin saat ini adalah {leader_node}")

    def periodic_check(self):
        """
        Melakukan pengecekan pemimpin secara berkala, memastikan bahwa node selalu memantau
        status pemimpin, bahkan jika ia bukan pemimpin.
        """
        while not self.stop_event.is_set():
            self.evaluate_leader()
            time.sleep(self.check_interval)

    def start_election(self):
        """
        Memulai proses pemilihan pemimpin dan memulai pengecekan berkala.
        """
        try:
            self.zk.create(self.node_path, b"", ephemeral=True)
            print(f"[{self.node_id}] Membuat node {self.node_path}")
        except NodeExistsError:
            print(f"[{self.node_id}] Node {self.node_path} sudah ada.")
            sys.exit(1)

        # Mulai thread pengecekan berkala
        self.check_thread = threading.Thread(target=self.periodic_check)
        self.check_thread.start()

    def stop(self):
        """
        Menghentikan semua thread dan tugas pemimpin jika aktif.
        """
        self.stop_event.set()
        self.stop_leader_task()
        if self.check_thread.is_alive():
            self.check_thread.join()

def main():
    if len(sys.argv) != 2:
        print("Usage: python leader_election_periodic_check_fixed.py <node_id>")
        sys.exit(1)

    node_id = sys.argv[1]

    # Validasi node_id sebagai integer
    try:
        node_id_int = int(node_id)
    except ValueError:
        print("node_id harus berupa integer.")
        sys.exit(1)

    # Inisialisasi KazooClient
    zk = KazooClient(hosts=ZOOKEEPER_SERVERS)
    zk.start()

    # Memastikan path election node ada
    zk.ensure_path(ELECTION_NODE)

    # Inisialisasi LeaderElection
    election = LeaderElection(zk, node_id_int)
    election.start_election()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"[{node_id}] Mengakhiri proses.")
    finally:
        election.stop()
        # Menghentikan koneksi ZooKeeper
        zk.stop()

if __name__ == "__main__":
    main()
