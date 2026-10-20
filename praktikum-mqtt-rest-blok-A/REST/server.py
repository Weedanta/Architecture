#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REST server untuk eksperimen sensor suhu (versi termodifikasi).

Perubahan dari versi awal:
- Endpoint baru POST /suhu untuk menerima data sensor (JSON).
- Mencatat t_recv (epoch ms) saat permintaan diterima, lalu menulis
  satu baris ke log CSV per permintaan.
- Endpoint GET /suhu/terbaru untuk konsumen yang melakukan polling (Blok E).
- Endpoint lama /add dan /mul tetap ada.

Contoh menjalankan:
    python server.py
    python server.py --log logs/rest_blokA.csv --host 0.0.0.0
"""

import argparse
import csv
import os
import threading
import time
from datetime import datetime, timezone

from flask import Flask, request, jsonify

app = Flask(__name__)

CSV_COLUMNS = ['timestamp_iso', 'node_id', 'protocol', 't_send_ms', 't_recv_ms',
               'payload_bytes', 'suhu', 'sequence_no']

log_lock = threading.Lock()
log_path = None
latest = {}            # data terbaru per node_id, untuk polling konsumen
latest_lock = threading.Lock()


def now_ms():
    return int(time.time() * 1000)


def write_log(row):
    with log_lock:
        new_file = not os.path.exists(log_path) or os.path.getsize(log_path) == 0
        with open(log_path, 'a', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            if new_file:
                w.writeheader()
            w.writerow(row)


@app.route('/suhu', methods=['POST'])
def terima_suhu():
    t_recv = now_ms()                       # dicatat paling awal
    raw = request.get_data()
    data = request.get_json(silent=True)
    if not data or not all(k in data for k in ('node_id', 't_send', 'suhu', 'sequence_no')):
        return jsonify({'error': 'Invalid input'}), 400

    row = {
        'timestamp_iso': datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
        'node_id': data['node_id'],
        'protocol': 'rest',
        't_send_ms': int(data['t_send']),
        't_recv_ms': t_recv,
        'payload_bytes': len(raw),
        'suhu': float(data['suhu']),
        'sequence_no': int(data['sequence_no']),
    }
    write_log(row)
    with latest_lock:
        latest[row['node_id']] = row
    # t_send dikembalikan agar client bisa menghitung RTT
    return jsonify({'status': 'ok', 't_send': row['t_send_ms'], 't_recv': t_recv})


@app.route('/suhu/terbaru', methods=['GET'])
def suhu_terbaru():
    with latest_lock:
        return jsonify(list(latest.values()))


@app.route('/add', methods=['GET'])
def add():
    try:
        a = int(request.args.get('a'))
        b = int(request.args.get('b'))
        return jsonify({'result': a + b})
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid input'}), 400


@app.route('/mul', methods=['GET'])
def mul():
    try:
        a = int(request.args.get('a'))
        b = int(request.args.get('b'))
        return jsonify({'result': a * b})
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid input'}), 400


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='REST server sensor suhu')
    p.add_argument('--host', default='0.0.0.0',
                   help='0.0.0.0 agar bisa diakses laptop lain (default)')
    p.add_argument('--port', type=int, default=5151)
    p.add_argument('--log', default='logs/rest_server.csv', help='berkas log CSV')
    args = p.parse_args()

    log_path = args.log
    os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
    print('REST server di port', args.port, '| log:', log_path)
    # debug=False supaya tidak ada proses reloader ganda yang mengganggu log
    app.run(host=args.host, port=args.port, debug=False, threaded=True)