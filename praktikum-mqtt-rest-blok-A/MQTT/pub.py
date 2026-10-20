#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MQTT publisher sensor suhu (versi termodifikasi).

Perubahan dari versi awal:
- Payload berupa JSON berisi node_id, t_send (epoch ms), suhu, dan sequence_no.
- QoS bisa dipilih (0, 1, 2) dan sesi persisten bisa diaktifkan (Blok D dan F).
- Topic diberi akhiran unik agar tidak tercampur data mahasiswa lain di broker yang sama.
- Mencatat setiap pengiriman ke log CSV pengirim.

Contoh menjalankan:
    python pub.py --node-id laptop1
    python pub.py --node-id laptop1 --qos 1 --persistent --count 300
"""

import argparse
import csv
import json
import os
import random
import sys
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

BROKER = 'fec429b2a5b94f3096cda8a658769824.s1.eu.hivemq.cloud'
PORT = 8883
DEFAULT_TOPIC = 'sister/temp/2646000119'
SEND_COLUMNS = ['timestamp_iso', 'node_id', 'protocol', 't_send_ms', 'suhu',
                'sequence_no', 'status', 'rtt_ms']


def load_dotenv(path):
    """Membaca berkas .env sederhana (KEY=VALUE per baris)."""
    if not os.path.exists(path):
        return
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            os.environ.setdefault(key.strip(), value.strip())


def now_ms():
    return int(time.time() * 1000)


def main():
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
    broker_default = os.environ.get('MQTT_BROKER', BROKER)
    port_default = int(os.environ.get('MQTT_PORT', PORT))
    p = argparse.ArgumentParser(description='MQTT publisher sensor suhu')
    p.add_argument('--node-id', default='node1')
    p.add_argument('--topic', default=DEFAULT_TOPIC)
    p.add_argument('--qos', type=int, choices=[0, 1, 2], default=0)
    p.add_argument('--persistent', action='store_true',
                   help='sesi persisten (clean_session=False, client_id tetap)')
    p.add_argument('--interval', type=float, default=1.0)
    p.add_argument('--count', type=int, default=0, help='0 = terus sampai Ctrl+C')
    p.add_argument('--broker', default=broker_default, help='default dari MQTT_BROKER di .env')
    p.add_argument('--port', type=int, default=port_default)
    p.add_argument('--no-tls', action='store_true', help='broker lokal tanpa TLS (sama dengan MQTT_TLS=0 di .env)')
    p.add_argument('--log', default=None, help='default logs/mqtt_send_<node>.csv')
    args = p.parse_args()

    use_tls = not args.no_tls and os.environ.get('MQTT_TLS', '1') != '0'
    username = os.environ.get('MQTT_USERNAME') or None
    password = os.environ.get('MQTT_PASSWORD') or None
    if use_tls and (not username or not password):
        print('MQTT_USERNAME dan MQTT_PASSWORD belum diatur di .env')
        sys.exit(1)

    log_path = args.log or f'logs/mqtt_send_{args.node_id}.csv'
    os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
    new_file = not os.path.exists(log_path) or os.path.getsize(log_path) == 0
    f = open(log_path, 'a', newline='', encoding='utf-8')
    w = csv.DictWriter(f, fieldnames=SEND_COLUMNS)
    if new_file:
        w.writeheader()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                         client_id=f'pub-{args.node_id}',
                         clean_session=not args.persistent)
    if username:
        client.username_pw_set(username, password)
    if use_tls:
        client.tls_set()
    client.reconnect_delay_set(min_delay=1, max_delay=5)

    def on_connect(c, userdata, flags, reason_code, properties):
        print('Terhubung ke broker' if reason_code == 0 else f'Gagal terhubung: {reason_code}')

    def on_disconnect(c, userdata, flags, reason_code, properties):
        if reason_code != 0:
            print(f'Terputus dari broker ({reason_code}), mencoba menyambung ulang...')

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.connect(args.broker, args.port, keepalive=60)
    client.loop_start()          # thread jaringan + reconnect otomatis
    time.sleep(1)

    seq = 0
    print(f'Publish ke {args.topic} sebagai {args.node_id}, QoS {args.qos} | log: {log_path}')
    try:
        while args.count == 0 or seq < args.count:
            seq += 1
            suhu = round(random.uniform(25.0, 32.0), 2)
            t_send = now_ms()
            payload = json.dumps({'node_id': args.node_id, 't_send': t_send,
                                  'suhu': suhu, 'sequence_no': seq})
            info = client.publish(args.topic, payload, qos=args.qos)
            # rc 0 = diterima paho (terkirim atau masuk antrean), selain itu gagal
            status = 'ok' if info.rc == mqtt.MQTT_ERR_SUCCESS else f'error:{info.rc}'
            w.writerow({'timestamp_iso': datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
                        'node_id': args.node_id, 'protocol': 'mqtt', 't_send_ms': t_send,
                        'suhu': suhu, 'sequence_no': seq, 'status': status, 'rtt_ms': ''})
            f.flush()
            print(f'seq={seq} suhu={suhu} status={status}')
            sisa = args.interval - (now_ms() - t_send) / 1000
            if sisa > 0:
                time.sleep(sisa)
        time.sleep(2)            # beri waktu pesan terakhir terkirim
    except KeyboardInterrupt:
        print('Berhenti')
    finally:
        client.loop_stop()
        client.disconnect()
        f.close()


if __name__ == '__main__':
    main()