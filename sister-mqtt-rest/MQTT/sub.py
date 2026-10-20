#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MQTT subscriber = konsumen/dashboard.
Dimodifikasi dari kode asli (widhi, 2024): mencatat t_recv, menulis log CSV,
QoS dan sesi persisten, serta echo balik ke publisher untuk mengukur RTT.

Hanya SATU subscriber yang boleh memakai --echo (subscriber utama), supaya
publisher tidak menerima echo ganda.

Contoh:
  python MQTT/sub.py --consumer main --echo --qos 1
  python MQTT/sub.py --consumer c2 --qos 1          (konsumen tambahan Blok E)
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mqttcommon import TOPIC_ACK, TOPIC_DATA, connect, make_client  # noqa: E402
from logutil import CsvLog, now_ms  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="MQTT subscriber (konsumen)")
    ap.add_argument("--consumer", default="main", help="ID konsumen, misal main, c2, c3")
    ap.add_argument("--qos", type=int, default=1, choices=[0, 1, 2])
    ap.add_argument("--echo", action="store_true", help="Kirim echo untuk RTT (hanya 1 subscriber)")
    ap.add_argument("--clean", action="store_true",
                    help="Pakai sesi bersih. Default: sesi persisten (broker menyimpan pesan saat putus)")
    ap.add_argument("--quiet", action="store_true", help="Jangan print setiap pesan")
    ap.add_argument("--env", default=".env", help="File env di folder MQTT, misal .env.local")
    args = ap.parse_args()

    log = CsvLog(f"recv_mqtt_{args.consumer}.csv")
    count = {"n": 0}

    def on_connect(client, userdata, flags, rc, properties=None):
        if rc == 0:
            print(f"[{time.strftime('%H:%M:%S')}] Terhubung. session_present={flags.session_present}")
            client.subscribe(f"{TOPIC_DATA}/+", qos=args.qos)
            print(f"Berlangganan {TOPIC_DATA}/+ (QoS {args.qos})")
        else:
            print(f"Gagal terhubung, kode: {rc}")

    def on_disconnect(client, userdata, flags, rc, properties=None):
        print(f"[{time.strftime('%H:%M:%S')}] TERPUTUS (rc={rc}), mencoba reconnect...")

    def on_message(client, userdata, msg):
        t_recv = now_ms()  # dicatat paling awal
        try:
            d = json.loads(msg.payload)
        except ValueError:
            return
        log.write(exp=d.get("exp"), run=d.get("run"), node_id=d.get("node_id"), protocol="mqtt",
                  t_send_ms=d.get("t_send"), t_recv_ms=t_recv, payload_bytes=len(msg.payload),
                  suhu=d.get("suhu"), sequence_no=d.get("sequence_no"),
                  status=f"recv:{args.consumer}:dup" if msg.dup else f"recv:{args.consumer}")
        if args.echo:
            ack = json.dumps({"exp": d.get("exp"), "run": d.get("run"),
                              "t_send": d.get("t_send"), "sequence_no": d.get("sequence_no")})
            client.publish(f"{TOPIC_ACK}/{d.get('node_id')}", ack, qos=0)
        count["n"] += 1
        if not args.quiet:
            print(f"{d.get('node_id')} seq={d.get('sequence_no')} suhu={d.get('suhu')}")
        elif count["n"] % 100 == 0:
            print(f"  {count['n']} pesan diterima")

    # client_id tetap (tanpa PID) agar sesi persisten bisa dilanjutkan setelah putus
    client = make_client(f"sub-{args.consumer}", clean_session=args.clean)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    connect(client)
    try:
        print("Menunggu pesan... (Ctrl+C untuk keluar)")
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nSubscriber dihentikan.")
    finally:
        client.disconnect()
        log.close()


if __name__ == "__main__":
    main()
