#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REST konsumen (dashboard) untuk Blok E: polling GET /data secara berkala.
Setiap konsumen = satu proses poller.py dengan --consumer berbeda.

Contoh:
  python REST/poller.py --consumer c1 --url http://192.168.1.10:5151 --interval 0.5
"""
import argparse
import os
import sys
import time

import requests

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from logutil import CsvLog, now_ms, pace  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="REST poller (konsumen dashboard)")
    ap.add_argument("--consumer", required=True, help="ID konsumen, misal c1, c2, c3")
    ap.add_argument("--url", default="http://127.0.0.1:5151")
    ap.add_argument("--interval", type=float, default=0.5, help="Jeda antar-polling (detik)")
    args = ap.parse_args()

    endpoint = args.url.rstrip("/") + "/data"
    headers = {"ngrok-skip-browser-warning": "1"}
    log = CsvLog(f"poll_rest_{args.consumer}.csv")
    session = requests.Session()

    # Mulai dari data terbaru, bukan dari awal buffer server
    after = session.get(endpoint, params={"peek": 1}, headers=headers, timeout=3).json()["next"]
    print(f"Konsumen {args.consumer} polling {endpoint} tiap {args.interval} s")

    n_poll, n_items = 0, 0
    next_t = time.time()
    try:
        while True:
            try:
                r = session.get(endpoint, params={"after": after}, headers=headers, timeout=3)
                t_recv = now_ms()
                d = r.json()
                for it in d["items"]:
                    log.write(exp=it.get("exp"), run=it.get("run"), node_id=it.get("node_id"),
                              protocol="rest", t_send_ms=it.get("t_send"), t_recv_ms=t_recv,
                              payload_bytes=it.get("payload_bytes"), suhu=it.get("suhu"),
                              sequence_no=it.get("sequence_no"), status=f"poll:{args.consumer}")
                after = d["next"]
                n_poll += 1
                n_items += len(d["items"])
                if n_poll % 20 == 0:
                    print(f"  {n_poll} polling, {n_items} item diterima")
            except (requests.RequestException, ValueError) as e:
                print(f"  polling gagal: {type(e).__name__}")
            next_t = pace(next_t, args.interval)
    except KeyboardInterrupt:
        print("Poller dihentikan.")
    finally:
        log.close()


if __name__ == "__main__":
    main()
