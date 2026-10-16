"""Check this laptop's clock offset against an NTP server.

One-way latency is only valid when the offset is below 50 ms. Results are saved
to logs/clock/<laptop>.csv and used by analysis/analyze.py --clock-correction.

Example:
  python tools/clock_check.py
"""
import argparse
import csv
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import config  # noqa: E402

try:
    import ntplib
except ImportError:
    print("pip install ntplib")
    sys.exit(1)

SERVERS = ["time.google.com", "id.pool.ntp.org", "pool.ntp.org", "time.windows.com"]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--laptop", default=config.env("LAPTOP", "unknown"))
    p.add_argument("--samples", type=int, default=5)
    p.add_argument("--limit-ms", type=float, default=50.0)
    args = p.parse_args()

    c = ntplib.NTPClient()
    offsets, delays, used = [], [], None
    for srv in SERVERS:
        try:
            for _ in range(args.samples):
                r = c.request(srv, version=3, timeout=2)
                offsets.append(r.offset * 1000.0)
                delays.append(r.delay * 1000.0)
            used = srv
            break
        except Exception as e:  # noqa: BLE001
            print("  {} failed: {}".format(srv, e))
            offsets, delays = [], []
    if not offsets:
        print("No NTP server reachable. Use RTT mode instead (pub.py --rtt / sub.py --echo).")
        sys.exit(2)

    off = statistics.median(offsets)
    dly = statistics.median(delays)
    ok = abs(off) < args.limit_ms
    print("Laptop {} | server {} | median offset {:+.1f} ms | delay {:.1f} ms | {}".format(
        args.laptop, used, off, dly, "OK (< {} ms)".format(args.limit_ms) if ok else "NEEDS SYNC"))
    if not ok:
        print("  Windows: Settings > Time & language > Date & time > Sync now")
        print("           or (as Administrator) w32tm /resync /force")
        print("  macOS  : sudo sntp -sS time.apple.com")
        print("  Linux  : sudo chronyc makestep  /  sudo timedatectl set-ntp true")

    d = config.LOG_DIR / "clock"
    d.mkdir(parents=True, exist_ok=True)
    path = d / "{}.csv".format(args.laptop)
    new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["timestamp_iso", "laptop", "server", "offset_ms", "delay_ms", "ok"])
        w.writerow([config.iso_now(), args.laptop, used, round(off, 2), round(dly, 2), ok])
    print("  saved to {}".format(path))


if __name__ == "__main__":
    main()
