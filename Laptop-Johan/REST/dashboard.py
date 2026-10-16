"""REST dashboard: a consumer that POLLS the server (Block E).

Every --interval seconds the dashboard calls GET /latest?after=<cursor>.
New messages are logged with t_recv = the moment the poll response arrives,
so consumer latency = send latency + time spent waiting for the next poll.

Example:
  python REST/dashboard.py --consumer-id dash-johan --server http://192.168.1.10:5151 --block E --condition C2
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests  # noqa: E402

from common import config  # noqa: E402
from common.csvlog import RECV_COLUMNS, CsvLog  # noqa: E402


def main():
    p = argparse.ArgumentParser(description="REST dashboard (polling consumer)")
    p.add_argument("--consumer-id", default="dash-{}".format(config.env("LAPTOP", "1")))
    p.add_argument("--server", default=config.rest_url_default())
    p.add_argument("--interval", type=float, default=float(config.env("POLL_INTERVAL", 0.2)),
                   help="polling period in seconds (default 0.2)")
    p.add_argument("--timeout", type=float, default=2.0)
    p.add_argument("--no-keepalive", action="store_true")
    p.add_argument("--block", default="E")
    p.add_argument("--condition", default="C1")
    p.add_argument("--session", default=None)
    args = p.parse_args()

    base = args.server.rstrip("/")
    path = config.log_path(args.block, args.condition, "rest", "recv", args.consumer_id, args.session)
    log = CsvLog(path, RECV_COLUMNS)
    http = requests if args.no_keepalive else requests.Session()
    headers = {"ngrok-skip-browser-warning": "1"} if "ngrok" in base else {}

    cursor = -1
    polls = 0
    got = 0
    print("[dashboard] {} polling {} every {} s".format(args.consumer_id, base, args.interval))
    print("[dashboard] log: {}".format(path))
    try:
        while True:
            t_start = time.time()
            try:
                r = http.get(base + "/latest", params={"after": cursor}, headers=headers, timeout=args.timeout)
                t_recv = config.now_ms()
                polls += 1
                data = r.json()
                for it in data.get("items", []):
                    log.write({
                        "timestamp_iso": config.iso_now(), "node_id": it.get("node_id"),
                        "protocol": "rest", "t_send_ms": it.get("t_send_ms"), "t_recv_ms": t_recv,
                        "payload_bytes": len(r.content) // max(1, len(data["items"])),
                        "suhu": it.get("suhu"), "sequence_no": it.get("sequence_no"),
                        "run_id": it.get("run_id"), "receiver_id": args.consumer_id,
                    })
                    got += 1
                cursor = data.get("next", cursor)
            except (requests.RequestException, ValueError) as e:
                print("  poll failed: {}".format(type(e).__name__), flush=True)
            if polls % 50 == 0:
                print("  polls={} messages={}".format(polls, got), flush=True)
            remaining = args.interval - (time.time() - t_start)
            if remaining > 0:
                time.sleep(remaining)
    except KeyboardInterrupt:
        print("\n[dashboard] stopped. polls={} messages={}".format(polls, got))
    finally:
        log.close()


if __name__ == "__main__":
    main()
