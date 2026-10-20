#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cek selisih jam laptop terhadap server NTP (tanpa dependency tambahan).
Syarat LKM: selisih < 50 ms agar latensi satu arah valid.

  python tools/check_clock.py
"""
import socket
import struct
import time

NTP_DELTA = 2208988800  # selisih epoch 1900 dan 1970


def query(host):
    pkt = b"\x1b" + 47 * b"\0"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(3)
        t1 = time.time()
        s.sendto(pkt, (host, 123))
        data, _ = s.recvfrom(48)
        t4 = time.time()
    def ts(off):
        sec, frac = struct.unpack("!II", data[off:off + 8])
        return sec - NTP_DELTA + frac / 2**32
    t2, t3 = ts(32), ts(40)
    offset = ((t2 - t1) + (t3 - t4)) / 2
    delay = (t4 - t1) - (t3 - t2)
    return offset * 1000, delay * 1000


for host in ["time.google.com", "pool.ntp.org", "id.pool.ntp.org"]:
    try:
        off, delay = query(host)
        ok = "OK" if abs(off) < 50 else "PERLU SINKRON ULANG"
        print(f"{host:18s} offset {off:+8.1f} ms  (delay {delay:.0f} ms)  -> {ok}")
    except OSError as e:
        print(f"{host:18s} gagal: {e}")
