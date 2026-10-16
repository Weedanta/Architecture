"""Records when the network goes down and comes back (Block D).

Run it on the laptop whose Wi-Fi gets switched off. It opens a TCP connection
to the target every 0.25 s and logs every UP -> DOWN -> UP transition.

Examples:
  python tools/link_watch.py --target 192.168.1.10:5151 --block D
  python tools/link_watch.py --target 1.1.1.1:443        --block D   (internet check, for the MQTT cloud broker)
"""
import argparse
import csv
import os
import socket
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import config  # noqa: E402


def probe(host, port, timeout):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="{}:{}".format(config.collector_ip(), config.REST_PORT_DEFAULT),
                    help="host:port to probe")
    ap.add_argument("--period", type=float, default=0.25)
    ap.add_argument("--timeout", type=float, default=0.5)
    ap.add_argument("--block", default="D")
    ap.add_argument("--condition", default="fault")
    ap.add_argument("--session", default=None)
    a = ap.parse_args()

    host, port = a.target.rsplit(":", 1)
    port = int(port)
    path = config.log_path(a.block, a.condition, "net", "linkwatch", config.env("LAPTOP", "host"), a.session)
    new = not path.exists()
    f = open(path, "a", newline="", encoding="utf-8")
    w = csv.writer(f)
    if new:
        w.writerow(["timestamp_iso", "t_ms", "event", "down_duration_s"])
    state = None
    t_down = None
    print("watching {}:{} -> {}  (Ctrl+C to stop)".format(host, port, path))
    try:
        while True:
            up = probe(host, port, a.timeout)
            now = config.now_ms()
            if up != state:
                if state is not None:
                    if not up:
                        t_down = now
                        w.writerow([config.iso_now(), now, "DOWN", ""])
                        print("[{}] DOWN".format(config.iso_now()), flush=True)
                    else:
                        dur = (now - t_down) / 1000.0 if t_down else ""
                        w.writerow([config.iso_now(), now, "UP", dur])
                        print("[{}] UP again after {} s".format(config.iso_now(), dur), flush=True)
                    f.flush()
                else:
                    print("[{}] initial state: {}".format(config.iso_now(), "UP" if up else "DOWN"))
                state = up
            time.sleep(a.period)
    except KeyboardInterrupt:
        pass
    finally:
        f.close()


if __name__ == "__main__":
    main()
