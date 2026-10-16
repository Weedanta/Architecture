"""MQTT publisher (sensor / sender), modified from the reference repository.

Changes from the original (publishing "Suhu: 28C" to sister/temp every second):
  * JSON payload: node_id, t_send (epoch ms), suhu, sequence_no, run_id
  * per-group, per-node topic: sister/temp/<GROUP>/<node_id> (no clash with other groups)
  * configurable QoS, keepalive and persistent session (Blocks D and F)
  * sender log: t_ack_ms = on_publish callback (QoS 0: written to socket, QoS 1: PUBACK, QoS 2: PUBCOMP)
  * --rtt: measure round trip through an echo from sub.py --echo (when clocks are not in sync)

Examples:
  python MQTT/pub.py --node-id johan --runs 10 --block B --condition N2
  python MQTT/pub.py --node-id johan --qos 1 --persistent --keepalive 10 --block D --condition fault --runs 5 --duration 90
"""
import argparse
import json
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paho.mqtt.client as mqtt  # noqa: E402

from common import config  # noqa: E402
from common.csvlog import RTT_COLUMNS, SEND_COLUMNS, CsvLog  # noqa: E402
from common.mqttconn import add_broker_args, make_client  # noqa: E402
from common.runner import add_run_args, run_loop  # noqa: E402
from common.sensor import TemperatureSensor, build_payload  # noqa: E402


def main():
    p = argparse.ArgumentParser(description="Periodic MQTT publisher")
    add_run_args(p)
    add_broker_args(p)
    p.add_argument("--rtt", action="store_true", help="listen for echoes from sub.py --echo")
    p.add_argument("--ack-wait", type=float, default=3.0, help="seconds to wait for acks at the end of a run")
    args = p.parse_args()

    topic = config.data_topic(args.node_id)
    client_id = "pub-{}-{}".format(config.group(), args.node_id)
    client, host, port = make_client(args, client_id)
    sensor = TemperatureSensor(args.node_id)

    path = config.log_path(args.block, args.condition, "mqtt", "send", args.node_id, args.session)
    log = CsvLog(path, SEND_COLUMNS)
    rtt_log = None
    if args.rtt:
        rtt_log = CsvLog(config.log_path(args.block, args.condition, "mqtt", "rtt", args.node_id, args.session),
                         RTT_COLUMNS)

    lock = threading.RLock()
    pending = {}          # mid -> row
    early_acks = {}       # mid -> t_ack (callback fired before the mid was stored)
    connected = threading.Event()
    stats = {"ok": 0, "noack": 0, "err": 0}

    def on_connect(c, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print("[{}] connected to {}:{} (session_present={})".format(
                config.iso_now(), host, port, flags.session_present), flush=True)
            connected.set()
            if args.rtt:
                c.subscribe(config.echo_topic(args.node_id), qos=0)
        else:
            print("[pub] connection failed: {}".format(reason_code), flush=True)

    def on_disconnect(c, userdata, flags, reason_code, properties):
        connected.clear()
        print("[{}] DISCONNECTED from broker (rc={}), paho will reconnect automatically".format(
            config.iso_now(), reason_code), flush=True)

    def on_publish(c, userdata, mid, reason_code, properties):
        t_ack = config.now_ms()
        with lock:
            row = pending.pop(mid, None)
            if row is None:
                early_acks[mid] = t_ack
                return
        row["t_ack_ms"] = t_ack
        log.write(row)
        stats["ok"] += 1

    def on_message(c, userdata, msg):
        t_echo = config.now_ms()
        try:
            d = json.loads(msg.payload)
        except ValueError:
            return
        rtt_log.write({
            "timestamp_iso": config.iso_now(), "node_id": d.get("node_id"), "protocol": "mqtt",
            "sequence_no": d.get("sequence_no"), "run_id": d.get("run_id"),
            "t_send_ms": d.get("t_send_ms"), "t_echo_ms": t_echo, "rtt_ms": t_echo - d.get("t_send_ms", t_echo),
        })

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_publish = on_publish
    client.on_message = on_message

    print("[MQTT pub] node={} topic={} qos={} broker={}:{} persistent={}".format(
        args.node_id, topic, args.qos, host, port, args.persistent))
    print("[MQTT pub] log : {}".format(path))
    client.connect_async(host, port, keepalive=args.keepalive)
    client.loop_start()
    if not connected.wait(20):
        print("ERROR: could not connect to the broker within 20 seconds.")
        client.loop_stop()
        sys.exit(1)

    def send_one(run_id, seq):
        temperature = sensor.read()
        with lock:
            t_send = config.now_ms()
            body = json.dumps(build_payload(args.node_id, "mqtt", seq, run_id, temperature, t_send)).encode()
            info = client.publish(topic, body, qos=args.qos)
            if info.rc == 0:
                status = "ok"
            elif args.qos > 0 and info.rc == mqtt.MQTT_ERR_NO_CONN:
                status = "queued"  # QoS > 0: kept in the client queue, resent after reconnect
            else:
                status = "rc{}".format(info.rc)
            row = {
                "timestamp_iso": config.iso_now(), "node_id": args.node_id, "protocol": "mqtt",
                "t_send_ms": t_send, "t_ack_ms": -1, "payload_bytes": len(body), "suhu": temperature,
                "sequence_no": seq, "run_id": run_id, "status": status,
            }
            if info.rc != 0 and args.qos == 0:
                # QoS 0 while disconnected: the client drops the message
                log.write(row)
                stats["err"] += 1
            elif info.mid in early_acks:
                row["t_ack_ms"] = early_acks.pop(info.mid)
                log.write(row)
                stats["ok"] += 1
            else:
                pending[info.mid] = row
        if seq % 10 == 0 or info.rc != 0:
            print("  run {} seq {:4d} temp {:5.2f} rc {} pending {}".format(
                run_id, seq, temperature, info.rc, len(pending)), flush=True)

    def on_run_end(run_id):
        t_end = time.time() + args.ack_wait
        while time.time() < t_end:
            with lock:
                if not any(r["run_id"] == run_id for r in pending.values()):
                    break
            time.sleep(0.1)

    try:
        run_loop(args, send_one, on_run_end)
    except KeyboardInterrupt:
        print("\n[MQTT pub] stopped.")
    finally:
        time.sleep(0.5)
        with lock:
            for row in pending.values():
                row["status"] = "noack:" + row["status"]
                log.write(row)
                stats["noack"] += 1
            pending.clear()
        client.loop_stop()
        client.disconnect()
        log.close()
        print("[MQTT pub] acked={} not_acked={} errors={}".format(stats["ok"], stats["noack"], stats["err"]))


if __name__ == "__main__":
    main()
