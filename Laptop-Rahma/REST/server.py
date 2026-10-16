"""REST server (Flask), modified from the reference repository widhi/distributed-system.

Changes from the original:
  * the original /add and /mul endpoints are kept (old client still works)
  * POST /suhu   : receives a sensor reading, records t_recv the moment the request
                   arrives, then appends one row to the CSV log
  * GET  /latest : used by dashboards (polling consumers, Block E)
  * GET  /health : quick reachability check from other laptops
  * binds to 0.0.0.0 so other laptops on the network can reach it

Example:
  python REST/server.py --block B --condition N3
"""
import argparse
import json
import logging
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, request  # noqa: E402

from common import config  # noqa: E402
from common.csvlog import RECV_COLUMNS, CsvLog  # noqa: E402

app = Flask(__name__)
logging.getLogger("werkzeug").setLevel(logging.ERROR)  # no per-request access log

STATE = {"log": None, "receiver_id": "server", "count": 0}
MESSAGES = []
LOCK = threading.Lock()


# ---------- original endpoints from the reference repository ----------
@app.route("/add", methods=["GET"])
def add_numbers():
    try:
        a = int(request.args.get("a"))
        b = int(request.args.get("b"))
        return jsonify({"result": a + b})
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid input"}), 400


@app.route("/mul", methods=["GET"])
def mul_numbers():
    try:
        a = int(request.args.get("a"))
        b = int(request.args.get("b"))
        return jsonify({"result": a * b})
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid input"}), 400


# ---------- experiment endpoints ----------
@app.route("/suhu", methods=["POST"])
def receive_temperature():
    t_recv = config.now_ms()  # taken first, before any parsing
    raw = request.get_data()
    try:
        data = json.loads(raw)
    except ValueError:
        return jsonify({"error": "Invalid JSON"}), 400

    if data.get("run_id") == 0:
        # run_id 0 = probe request from tools/overhead_calc.py, not logged
        return jsonify({"status": "ok", "t_recv_ms": t_recv, "index": 0})

    row = {
        "timestamp_iso": config.iso_now(),
        "node_id": data.get("node_id"),
        "protocol": "rest",
        "t_send_ms": data.get("t_send_ms"),
        "t_recv_ms": t_recv,
        "payload_bytes": len(raw),
        "suhu": data.get("suhu"),
        "sequence_no": data.get("sequence_no"),
        "run_id": data.get("run_id"),
        "receiver_id": STATE["receiver_id"],
    }
    STATE["log"].write(row)
    with LOCK:
        data["t_server_ms"] = t_recv
        MESSAGES.append(data)
        idx = len(MESSAGES)
        STATE["count"] += 1
    return jsonify({"status": "ok", "t_recv_ms": t_recv, "index": idx})


@app.route("/latest", methods=["GET"])
def latest():
    """?after=<index> returns messages after that index. after=-1 returns only the current position."""
    try:
        after = int(request.args.get("after", 0))
    except ValueError:
        after = 0
    with LOCK:
        if after < 0:
            return jsonify({"next": len(MESSAGES), "items": []})
        items = MESSAGES[after:after + 1000]
        nxt = after + len(items)
    return jsonify({"next": nxt, "items": items})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "received": STATE["count"], "t_ms": config.now_ms()})


def main():
    p = argparse.ArgumentParser(description="REST server that logs temperature readings")
    p.add_argument("--port", type=int, default=int(config.env("REST_PORT", config.REST_PORT_DEFAULT)))
    p.add_argument("--block", default="A")
    p.add_argument("--condition", default="single")
    p.add_argument("--receiver-id", default=config.env("LAPTOP", "server"))
    p.add_argument("--session", default=None)
    args = p.parse_args()

    STATE["receiver_id"] = args.receiver_id
    path = config.log_path(args.block, args.condition, "rest", "recv", args.receiver_id, args.session)
    STATE["log"] = CsvLog(path, RECV_COLUMNS)
    print("[REST server] log : {}".format(path))
    print("[REST server] URL : http://{}:{}/suhu  (LAN)".format(config.local_ip(), args.port))
    print("[REST server] pid : {}".format(os.getpid()))
    print("[REST server] press Ctrl+C to stop")
    try:
        app.run(host="0.0.0.0", port=args.port, debug=False, threaded=True, use_reloader=False)
    finally:
        STATE["log"].close()


if __name__ == "__main__":
    main()
