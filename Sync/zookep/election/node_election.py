#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov  6 12:17:39 2024

@author: widhi
"""

from kazoo.client import KazooClient
from kazoo.recipe.election import Election
import time
import sys
import threading

# Konfigurasi ZooKeeper
ZOOKEEPER_SERVERS = '127.0.0.1:2181'
ELECTION_NODE = '/leader_election_tolerant'

def leader_task(leader_id):
    print(f"[{leader_id}] Saya adalah pemimpin sekarang. Melakukan tugas pemimpin...")
    try:
        while True:
            print(f"[{leader_id}] Melakukan tugas pemimpin...")
            time.sleep(5)
    except KeyboardInterrupt:
        print(f"[{leader_id}] Menghentikan tugas pemimpin.")

def watch_leader_change(client, leader_id):
    @client.ChildrenWatch(ELECTION_NODE)
    def watch(children):
        # Logika untuk memonitor perubahan pemimpin jika diperlukan
        print(f"[{leader_id}] Monitoring perubahan pemimpin. Current leaders: {children}")

def run_leader_election(client, leader_id):
    election = Election(client, ELECTION_NODE)
    # Jalankan election dalam thread terpisah
    election_thread = threading.Thread(target=election.run, args=(leader_task, leader_id))
    election_thread.start()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python leader_election_tolerant.py <leader_id>")
        sys.exit(1)

    leader_id = sys.argv[1]

    # Inisialisasi KazooClient dengan session timeout yang sesuai
    zk = KazooClient(hosts=ZOOKEEPER_SERVERS, timeout=10)
    zk.start()

    # Pastikan path election node ada
    zk.ensure_path(ELECTION_NODE)

    # Mulai pemilihan pemimpin
    run_leader_election(zk, leader_id)

    # Mulai watch untuk perubahan
    watch_leader_change(zk, leader_id)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"[{leader_id}] Mengakhiri proses.")
    finally:
        zk.stop()
