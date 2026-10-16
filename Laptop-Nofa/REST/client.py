"""REST client (sensor / sender), modified from the reference repository.

Changes from the original (a single GET /add call):
  * periodic loop of POST /suhu
  * payload carries node_id, t_send (epoch ms), suhu, sequence_no, run_id
  * every send is written to the sender log (status ok / fail)
  * NO retry by default (matches H3: "REST without retry"); --retry N for extra experiments
  * a new connection per request by default (like requests.get in the original).
    Note: Flask's built-in server (Werkzeug) answers with "Connection: close", so
    every REST message opens a fresh TCP connection (handshake + FIN).
    --keepalive only matters if the server supports keep-alive.

Example:
  python REST/client.py --node-id johan --server http://192.168.1.10:5151 --runs 10
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests  # noqa: E402

from common import config  # noqa: E402
from common.csvlog import SEND_COLUMNS, CsvLog  # noqa: E402
from common.runner import add_run_args, run_loop  # noqa: E402
from common.sensor import TemperatureSensor, build_payload  # noqa: E402


def main():
    p = argparse.ArgumentParser(description="Periodic REST client")
    add_run_args(p)
    p.add_argument("--server", default=config.rest_url_default(),
                   help="server base URL, e.g. http://192.168.1.10:5151 or an ngrok URL")
    p.add_argument("--timeout", type=float, default=2.0)
    p.add_argument("--retry", type=int, default=0, help="number of retries (default 0)")
    p.add_argument("--keepalive", action="store_true", help="reuse one persistent TCP connection")
    args = p.parse_args()

    url = args.server.rstrip("/") + "/suhu"
    sensor = TemperatureSensor(args.node_id)
    path = config.log_path(args.block, args.condition, "rest", "send", args.node_id, args.session)
    log = CsvLog(path, SEND_COLUMNS)
    sess = requests.Session() if args.keepalive else None
    headers = {"Content-Type": "application/json"}
    if "ngrok" in url:
        headers["ngrok-skip-browser-warning"] = "1"

    print("[REST client] node={} -> {}".format(args.node_id, url))
    print("[REST client] log : {}".format(path))
    stats = {"ok": 0, "fail": 0}

    def send_one(run_id, seq):
        temperature = sensor.read()
        status = "fail"
        t_ack = -1
        body = b""
        for _ in range(args.retry + 1):
            t_send = config.now_ms()
            body = json.dumps(build_payload(args.node_id, "rest", seq, run_id, temperature, t_send)).encode()
            try:
                poster = sess.post if sess else requests.post
                r = poster(url, data=body, headers=headers, timeout=args.timeout)
                t_ack = config.now_ms()
                status = "ok" if r.status_code == 200 else "http{}".format(r.status_code)
            except requests.RequestException as e:
                status = "fail:{}".format(type(e).__name__)
            if status == "ok":
                break
        stats["ok" if status == "ok" else "fail"] += 1
        log.write({
            "timestamp_iso": config.iso_now(), "node_id": args.node_id, "protocol": "rest",
            "t_send_ms": t_send, "t_ack_ms": t_ack, "payload_bytes": len(body), "suhu": temperature,
            "sequence_no": seq, "run_id": run_id, "status": status,
        })
        if seq % 10 == 0 or status != "ok":
            rtt = (t_ack - t_send) if t_ack > 0 else None
            print("  run {} seq {:4d} temp {:5.2f} status {} rtt {} ms".format(
                run_id, seq, temperature, status, rtt), flush=True)

    try:
        run_loop(args, send_one)
    except KeyboardInterrupt:
        print("\n[REST client] stopped.")
    finally:
        log.close()
        print("[REST client] ok={} failed={}".format(stats["ok"], stats["fail"]))


if __name__ == "__main__":
    main()
