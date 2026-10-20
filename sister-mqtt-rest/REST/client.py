#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REST client = node sensor suhu.
Dimodifikasi dari kode asli (widhi, 2024): dari satu kali panggil menjadi loop
periodik, menambah node_id, t_send (epoch ms), sequence_no, dan log CSV.

Tanpa retry secara default (sesuai H3). Pesan yang gagal dicatat status=error.

Contoh:
  python REST/client.py --node johan --url http://192.168.1.10:5151 --exp B_N4 \
      --runs 10 --duration 60 --gap 10 --interval 0.1 --start-at 14:30
"""
import argparse
import json
import os
import random
import sys
import time

import requests

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from logutil import CsvLog, now_ms, pace, run_schedule, wait_until  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="REST client (node sensor suhu)")
    ap.add_argument("--node", required=True, help="ID node, misal: johan, nova, rahma, weda")
    ap.add_argument("--url", default="http://127.0.0.1:5151",
                    help="Alamat server, misal http://192.168.1.10:5151 atau URL ngrok")
    ap.add_argument("--exp", required=True, help="Label kondisi, misal A, B_N3, C_wifi, D, E_c2")
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--first-run", type=int, default=1, help="Nomor run pertama (untuk melanjutkan)")
    ap.add_argument("--duration", type=float, default=60, help="Lama satu run (detik)")
    ap.add_argument("--gap", type=float, default=10, help="Jeda antar-run (detik)")
    ap.add_argument("--interval", type=float, default=1.0, help="Jeda antar-pesan (detik)")
    ap.add_argument("--start-at", default=None, help="Jam mulai serentak HH:MM atau HH:MM:SS")
    ap.add_argument("--timeout", type=float, default=2.0, help="Timeout HTTP (detik)")
    ap.add_argument("--retry", type=int, default=0, help="Jumlah retry jika gagal (default 0)")
    args = ap.parse_args()

    endpoint = args.url.rstrip("/") + "/data"
    log = CsvLog(f"send_rest_{args.node}.csv")
    session = requests.Session()  # koneksi TCP dipakai ulang (keep-alive)
    # Header ini mencegah halaman peringatan ngrok; tidak berpengaruh di LAN
    headers = {"Content-Type": "application/json", "ngrok-skip-browser-warning": "1"}

    print(f"Node {args.node} -> {endpoint} | exp={args.exp}")
    try:
        for run, t_start in run_schedule(args.runs, args.duration, args.gap,
                                         args.start_at, args.first_run):
            wait_until(t_start)
            print(f"== Run {run} mulai ==")
            seq, ok, err = 0, 0, 0
            t_end = t_start + args.duration
            next_t = t_start
            while time.time() < t_end:
                suhu = round(random.gauss(28.0, 0.5), 2)
                t_send = now_ms()
                body = {"exp": args.exp, "run": run, "node_id": args.node,
                        "t_send": t_send, "sequence_no": seq, "suhu": suhu}
                data = json.dumps(body)
                status, rtt = "error", ""
                for _ in range(args.retry + 1):
                    try:
                        r = session.post(endpoint, data=data, headers=headers,
                                         timeout=args.timeout)
                        if r.status_code == 200:
                            status = "ok"
                            rtt = now_ms() - t_send
                            break
                        status = f"http_{r.status_code}"
                    except requests.RequestException as e:
                        status = "error:" + type(e).__name__
                log.write(exp=args.exp, run=run, node_id=args.node, protocol="rest",
                          t_send_ms=t_send, payload_bytes=len(data), suhu=suhu,
                          sequence_no=seq, status=status, rtt_ms=rtt)
                if status == "ok":
                    ok += 1
                else:
                    err += 1
                    print(f"  seq {seq}: {status}")
                seq += 1
                next_t = pace(next_t, args.interval)
            print(f"== Run {run} selesai: terkirim {ok}, gagal {err} ==")
    except KeyboardInterrupt:
        print("Client dihentikan.")
    finally:
        log.close()


if __name__ == "__main__":
    main()
