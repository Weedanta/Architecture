#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilitas bersama: logging CSV, waktu, .env, dan penjadwalan run.
Dipakai oleh REST/*.py dan MQTT/*.py.
"""
import csv
import os
import threading
import time
from datetime import datetime

# Skema log LKM + 3 kolom tambahan (exp, run, status, rtt_ms) untuk analisis
FIELDS = [
    "timestamp_iso", "exp", "run", "node_id", "protocol",
    "t_send_ms", "t_recv_ms", "payload_bytes", "suhu", "sequence_no",
    "status", "rtt_ms",
]

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(ROOT, "logs")


def now_ms():
    """Waktu sekarang dalam epoch milidetik."""
    return int(time.time() * 1000)


def iso_now():
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def load_dotenv(path):
    """Muat KEY=VALUE dari file .env tanpa dependency tambahan."""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


class CsvLog:
    """Penulis CSV append-only yang aman dipakai banyak thread."""

    def __init__(self, filename):
        os.makedirs(LOG_DIR, exist_ok=True)
        self.path = os.path.join(LOG_DIR, filename)
        is_new = not os.path.exists(self.path) or os.path.getsize(self.path) == 0
        self._f = open(self.path, "a", newline="", encoding="utf-8")
        self._w = csv.DictWriter(self._f, fieldnames=FIELDS, extrasaction="ignore")
        if is_new:
            self._w.writeheader()
            self._f.flush()
        self._lock = threading.Lock()
        print(f"Log ditulis ke: {self.path}")

    def write(self, **row):
        row.setdefault("timestamp_iso", iso_now())
        with self._lock:
            self._w.writerow(row)
            self._f.flush()

    def close(self):
        self._f.close()


def run_schedule(runs, duration, gap, start_at=None, first_run=1):
    """
    Menghasilkan (nomor_run, epoch_mulai) untuk setiap run.
    Jika start_at ("HH:MM" atau "HH:MM:SS") diisi, semua laptop yang
    memakai jadwal yang sama akan mulai serentak (asal jam sudah sinkron).
    """
    if start_at:
        parts = [int(x) for x in start_at.split(":")]
        while len(parts) < 3:
            parts.append(0)
        now = datetime.now()
        base_dt = now.replace(hour=parts[0], minute=parts[1], second=parts[2], microsecond=0)
        if base_dt <= now:
            raise SystemExit(f"--start-at {start_at} sudah lewat. Pilih jam yang akan datang.")
        base = base_dt.timestamp()
    else:
        base = time.time() + 1
    for i in range(runs):
        yield first_run + i, base + i * (duration + gap)


def wait_until(t_epoch):
    while True:
        d = t_epoch - time.time()
        if d <= 0:
            return
        time.sleep(min(d, 0.5))


def pace(next_t, interval):
    """Tidur sampai jadwal kirim berikutnya; tidak menumpuk jika tertinggal."""
    next_t += interval
    now = time.time()
    if next_t < now:
        next_t = now
    else:
        time.sleep(next_t - now)
    return next_t
