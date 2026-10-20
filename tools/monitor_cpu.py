#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memantau CPU (%) sebuah proses selama satu kondisi Blok E.
Cari proses lewat --pid, atau lewat --name (misal "mosquitto").

Contoh:
  python tools/monitor_cpu.py --pid 12345 --label E_rest_c2 --duration 120
  python tools/monitor_cpu.py --name mosquitto --label E_mqtt_c2 --duration 120
"""
import argparse
import csv
import os
import statistics
import time

import psutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def find_proc(args):
    if args.pid:
        return psutil.Process(args.pid)
    for p in psutil.process_iter(["name", "cmdline"]):
        text = (p.info["name"] or "") + " " + " ".join(p.info["cmdline"] or [])
        if args.name.lower() in text.lower() and p.pid != os.getpid():
            return p
    raise SystemExit(f"Proses '{args.name}' tidak ditemukan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int)
    ap.add_argument("--name")
    ap.add_argument("--label", required=True, help="Misal E_rest_c1, E_mqtt_c3")
    ap.add_argument("--duration", type=float, default=120)
    ap.add_argument("--interval", type=float, default=1.0)
    args = ap.parse_args()
    if not args.pid and not args.name:
        raise SystemExit("Isi --pid atau --name")

    proc = find_proc(args)
    print(f"Memantau PID {proc.pid} ({proc.name()}) selama {args.duration} s")
    os.makedirs(os.path.join(ROOT, "logs"), exist_ok=True)
    path = os.path.join(ROOT, "logs", f"cpu_{args.label}.csv")
    proc.cpu_percent(None)  # sampel pertama selalu 0, dibuang
    samples = []
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_ms", "label", "cpu_percent"])
        t_end = time.time() + args.duration
        while time.time() < t_end:
            time.sleep(args.interval)
            v = proc.cpu_percent(None)
            samples.append(v)
            w.writerow([int(time.time() * 1000), args.label, v])
    q = statistics.quantiles(samples, n=4) if len(samples) > 1 else [0, 0, 0]
    print(f"CPU {args.label}: rata-rata {statistics.mean(samples):.1f}%, "
          f"median {statistics.median(samples):.1f}%, IQR {q[2]-q[0]:.1f}")
    print(f"Disimpan ke {path}")


if __name__ == "__main__":
    main()
