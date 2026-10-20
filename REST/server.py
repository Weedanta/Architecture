#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REST server penerima data suhu.
Dimodifikasi dari kode asli (widhi, 2024): menambah endpoint /data,
pencatatan t_recv, dan log CSV.

Endpoint:
  POST /data            -> node pengirim mengirim satu pembacaan suhu
  GET  /data?after=k    -> konsumen (dashboard) polling data baru (Blok E)
  GET  /add, GET /mul   -> endpoint asli, tetap dipertahankan
"""
import argparse
import json
import logging
import os
import sys
import threading

from flask import Flask, jsonify, request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from logutil import CsvLog, now_ms  # noqa: E402

app = Flask(__name__)
log = None
buffer = []          # semua pesan yang diterima, untuk dibaca konsumen polling
buf_lock = threading.Lock()


@app.route("/data", methods=["POST"])
def receive_data():
    t_recv = now_ms()  # dicatat paling awal agar akurat
    raw = request.get_data()
    try:
        d = json.loads(raw)
    except ValueError:
        return jsonify({"error": "JSON tidak valid"}), 400

    item = {
        "exp": d.get("exp"),
        "run": d.get("run"),
        "node_id": d.get("node_id"),
        "t_send": d.get("t_send"),
        "suhu": d.get("suhu"),
        "sequence_no": d.get("sequence_no"),
        "payload_bytes": len(raw),
    }
    log.write(
        exp=item["exp"], run=item["run"], node_id=item["node_id"], protocol="rest",
        t_send_ms=item["t_send"], t_recv_ms=t_recv, payload_bytes=len(raw),
        suhu=item["suhu"], sequence_no=item["sequence_no"], status="ok",
    )
    with buf_lock:
        buffer.append(item)
    return jsonify({"ok": True, "t_recv_ms": t_recv})


@app.route("/data", methods=["GET"])
def poll_data():
    """Konsumen mengirim indeks terakhir yang sudah dibaca, server mengembalikan sisanya."""
    with buf_lock:
        total = len(buffer)
        if request.args.get("peek"):
            return jsonify({"items": [], "next": total})
        after = int(request.args.get("after", 0))
        items = buffer[after:total]
    return jsonify({"items": items, "next": total})


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


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="REST server penerima data suhu")
    ap.add_argument("--port", type=int, default=5151)
    ap.add_argument("--host", default="0.0.0.0", help="0.0.0.0 agar bisa diakses laptop lain")
    args = ap.parse_args()

    log = CsvLog("recv_rest_server.csv")
    # Matikan log akses per-request agar print tidak membebani server
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    print(f"PID server: {os.getpid()}  (pakai untuk tools/monitor_cpu.py)")
    print(f"Server jalan di http://{args.host}:{args.port}")
    # debug=False: reloader debug akan menjalankan dua proses dan mengacaukan log
    app.run(host=args.host, port=args.port, threaded=True, debug=False)
