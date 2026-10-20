#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MQTT publisher = node sensor suhu.
Dimodifikasi dari kode asli (widhi, 2024): menambah node_id, t_send (epoch ms),
sequence_no, QoS, penjadwalan run, log CSV, dan pengukuran RTT lewat echo.

Catatan: kode asli tidak memanggil loop_start(), sehingga callback dan QoS 1/2
tidak pernah diproses. Di sini loop jaringan dijalankan di thread terpisah.

Contoh:
  python MQTT/pub.py --node johan --exp B_N4 --runs 10 --duration 60 --gap 10 \
      --interval 0.1 --qos 1 --start-at 14:30
"""
import argparse
import json
import os
import random
import sys
import time

import paho.mqtt.client as mqtt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mqttcommon import TOPIC_ACK, TOPIC_DATA, connect, make_client  # noqa: E402
from logutil import CsvLog, now_ms, pace, run_schedule, wait_until  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="MQTT publisher (node sensor suhu)")
    ap.add_argument("--node", required=True, help="ID node, misal: johan, nova, rahma, weda")
    ap.add_argument("--exp", required=True, help="Label kondisi, misal A, B_N3, C_wifi, D, F_q1")
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--first-run", type=int, default=1)
    ap.add_argument("--duration", type=float, default=60)
    ap.add_argument("--gap", type=float, default=10)
    ap.add_argument("--interval", type=float, default=1.0)
    ap.add_argument("--start-at", default=None)
    ap.add_argument("--qos", type=int, default=1, choices=[0, 1, 2])
    ap.add_argument("--env", default=".env", help="File env di folder MQTT, misal .env.local")
    args = ap.parse_args()

    send_log = CsvLog(f"send_mqtt_{args.node}.csv")
    ack_log = CsvLog(f"ack_mqtt_{args.node}.csv")
    topic = f"{TOPIC_DATA}/{args.node}"
    state = {"connected": False}

    def on_connect(client, userdata, flags, rc, properties=None):
        if rc == 0:
            state["connected"] = True
            client.subscribe(f"{TOPIC_ACK}/{args.node}", qos=0)
            print(f"[{time.strftime('%H:%M:%S')}] Terhubung ke broker")
        else:
            print(f"Gagal terhubung, kode: {rc}")

    def on_disconnect(client, userdata, flags, rc, properties=None):
        state["connected"] = False
        print(f"[{time.strftime('%H:%M:%S')}] TERPUTUS dari broker (rc={rc}), mencoba reconnect...")

    def on_message(client, userdata, msg):
        # Echo dari subscriber: hitung RTT = sekarang - t_send asli
        t = now_ms()
        try:
            d = json.loads(msg.payload)
        except ValueError:
            return
        ack_log.write(exp=d.get("exp"), run=d.get("run"), node_id=args.node, protocol="mqtt",
                      t_send_ms=d.get("t_send"), t_recv_ms=t, sequence_no=d.get("sequence_no"),
                      status="ack", rtt_ms=t - int(d.get("t_send", t)))

    client = make_client(f"{args.node}-pub-{os.getpid()}")
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.max_queued_messages_set(0)  # 0 = antrean offline tanpa batas
    connect(client)
    client.loop_start()

    print(f"Node {args.node} -> topik {topic} | exp={args.exp} | QoS {args.qos}")
    try:
        for run, t_start in run_schedule(args.runs, args.duration, args.gap,
                                         args.start_at, args.first_run):
            wait_until(t_start)
            print(f"== Run {run} mulai ==")
            seq, n_ok, n_other = 0, 0, 0
            t_end = t_start + args.duration
            next_t = t_start
            while time.time() < t_end:
                suhu = round(random.gauss(28.0, 0.5), 2)
                t_send = now_ms()
                body = {"exp": args.exp, "run": run, "node_id": args.node,
                        "t_send": t_send, "sequence_no": seq, "suhu": suhu, "qos": args.qos}
                data = json.dumps(body)
                info = client.publish(topic, data, qos=args.qos)
                if info.rc == mqtt.MQTT_ERR_SUCCESS and state["connected"]:
                    status = "sent"
                    n_ok += 1
                else:
                    # QoS 1/2 masuk antrean dan dikirim ulang setelah reconnect;
                    # QoS 0 tidak punya jaminan, jadi dianggap terbuang.
                    status = "queued" if args.qos > 0 else "dropped"
                    n_other += 1
                send_log.write(exp=args.exp, run=run, node_id=args.node, protocol="mqtt",
                               t_send_ms=t_send, payload_bytes=len(data), suhu=suhu,
                               sequence_no=seq, status=status)
                seq += 1
                next_t = pace(next_t, args.interval)
            print(f"== Run {run} selesai: langsung terkirim {n_ok}, antre/terbuang {n_other} ==")
        time.sleep(3)  # beri waktu sisa antrean dan echo terakhir
    except KeyboardInterrupt:
        print("Publisher dihentikan.")
    finally:
        client.loop_stop()
        client.disconnect()
        send_log.close()
        ack_log.close()


if __name__ == "__main__":
    main()
