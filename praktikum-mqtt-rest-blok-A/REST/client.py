#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REST client sensor suhu (versi termodifikasi).

Perubahan dari versi awal:
- Mengirim data suhu secara periodik (loop), bukan satu kali panggil.
- Setiap pesan membawa node_id, t_send (epoch ms), suhu, dan sequence_no.
- Tanpa retry: jika gagal, pesan itu dianggap hilang (sesuai H3).
- Mencatat setiap pengiriman ke log CSV pengirim, termasuk status dan RTT.

Contoh menjalankan:
    python client.py --node-id laptop1
    python client.py --node-id laptop1 --url http://192.168.1.10:5151 --count 300
"""

import argparse
import csv
import os
import random
import time
from datetime import datetime, timezone

import requests

SEND_COLUMNS = ['timestamp_iso', 'node_id', 'protocol', 't_send_ms', 'suhu',
                'sequence_no', 'status', 'rtt_ms']


def now_ms():
    return int(time.time() * 1000)


def main():
    p = argparse.ArgumentParser(description='REST client sensor suhu')
    p.add_argument('--node-id', default='node1')
    p.add_argument('--url', default='http://127.0.0.1:5151', help='alamat server (atau URL ngrok)')
    p.add_argument('--interval', type=float, default=1.0, help='jeda antar-pesan (detik)')
    p.add_argument('--count', type=int, default=0, help='jumlah pesan, 0 = terus sampai Ctrl+C')
    p.add_argument('--timeout', type=float, default=5.0)
    p.add_argument('--log', default=None, help='log CSV pengirim (default logs/rest_send_<node>.csv)')
    args = p.parse_args()

    log_path = args.log or f'logs/rest_send_{args.node_id}.csv'
    os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
    new_file = not os.path.exists(log_path) or os.path.getsize(log_path) == 0
    f = open(log_path, 'a', newline='', encoding='utf-8')
    w = csv.DictWriter(f, fieldnames=SEND_COLUMNS)
    if new_file:
        w.writeheader()

    endpoint = args.url.rstrip('/') + '/suhu'
    seq = 0
    print(f'Mengirim ke {endpoint} sebagai {args.node_id} | log: {log_path}')
    try:
        while args.count == 0 or seq < args.count:
            seq += 1
            suhu = round(random.uniform(25.0, 32.0), 2)
            t_send = now_ms()
            payload = {'node_id': args.node_id, 't_send': t_send,
                       'suhu': suhu, 'sequence_no': seq}
            status, rtt = '', ''
            try:
                r = requests.post(endpoint, json=payload, timeout=args.timeout)
                rtt = now_ms() - t_send
                status = str(r.status_code)
            except requests.RequestException as e:
                status = 'error:' + type(e).__name__
            w.writerow({'timestamp_iso': datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
                        'node_id': args.node_id, 'protocol': 'rest', 't_send_ms': t_send,
                        'suhu': suhu, 'sequence_no': seq, 'status': status, 'rtt_ms': rtt})
            f.flush()
            print(f'seq={seq} suhu={suhu} status={status} rtt={rtt} ms')
            # jaga interval tetap meskipun permintaan makan waktu
            sisa = args.interval - (now_ms() - t_send) / 1000
            if sisa > 0:
                time.sleep(sisa)
    except KeyboardInterrupt:
        print('Berhenti')
    finally:
        f.close()


if __name__ == '__main__':
    main()