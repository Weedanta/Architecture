#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Oct 27 17:03:26 2024

@author: widhi
"""

from kazoo.client import KazooClient

# Inisialisasi klien ZooKeeper
zk = KazooClient(hosts='127.0.0.1:2181')
zk.start()

# Node yang menyimpan saldo
balance_node = "/balance"

# Inisialisasi saldo awal
initial_balance = 1000

# Buat node /balance jika belum ada dan set saldo awal
if not zk.exists(balance_node):
    zk.create(balance_node, str(initial_balance).encode('utf-8'))
    print(f"Saldo awal diset ke: {initial_balance}")
else:
    print("Node /balance sudah ada.")

# Stop ZooKeeper client
zk.stop()
