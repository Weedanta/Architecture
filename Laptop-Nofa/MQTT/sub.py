"""MQTT subscriber (consumer), modified from the reference repository.

Changes from the original (which only printed the payload):
  * subscribes to sister/temp/<GROUP>/# (every node of this group)
  * records t_recv the moment a message arrives, then appends a CSV row
  * configurable QoS and persistent session
  * --echo: bounces each message back to its sender (for RTT measurement)

Example:
  python MQTT/sub.py --consumer-id wedanta --block B --condition N3
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import config  # noqa: E402
from common.csvlog import RECV_COLUMNS, CsvLog  # noqa: E402
from common.mqttconn import add_broker_args, make_client  # noqa: E402


def main():
    p = argparse.ArgumentParser(description="MQTT subscriber that logs temperature readings")
    add_broker_args(p)
    p.add_argument("--consumer-id", default=config.env("LAPTOP", "sub"))
    p.add_argument("--echo", action="store_true", help="bounce messages to sister/echo/<group>/<node>")
    p.add_argument("--block", default="A")
    p.add_argument("--condition", default="single")
    p.add_argument("--session", default=None)
    args = p.parse_args()

    topic = config.data_topic_base() + "/#"
    client_id = "sub-{}-{}".format(config.group(), args.consumer_id)
    client, host, port = make_client(args, client_id)
    path = config.log_path(args.block, args.condition, "mqtt", "recv", args.consumer_id, args.session)
    log = CsvLog(path, RECV_COLUMNS)
    count = {"n": 0}

    def on_connect(c, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print("[{}] connected to {}:{} (session_present={}), subscribing {} qos {}".format(
                config.iso_now(), host, port, flags.session_present, topic, args.qos), flush=True)
            c.subscribe(topic, qos=args.qos)
        else:
            print("Connection failed, code: {}".format(reason_code))
            sys.exit(1)

    def on_disconnect(c, userdata, flags, reason_code, properties):
        print("[{}] disconnected (rc={})".format(config.iso_now(), reason_code), flush=True)

    def on_message(c, userdata, msg):
        t_recv = config.now_ms()  # taken first
        try:
            d = json.loads(msg.payload)
        except ValueError:
            print("  non-JSON payload on {}: {!r}".format(msg.topic, msg.payload[:60]))
            return
        log.write({
            "timestamp_iso": config.iso_now(), "node_id": d.get("node_id"), "protocol": "mqtt",
            "t_send_ms": d.get("t_send_ms"), "t_recv_ms": t_recv, "payload_bytes": len(msg.payload),
            "suhu": d.get("suhu"), "sequence_no": d.get("sequence_no"), "run_id": d.get("run_id"),
            "receiver_id": args.consumer_id,
        })
        if args.echo and d.get("node_id"):
            c.publish(config.echo_topic(d["node_id"]), msg.payload, qos=0)
        count["n"] += 1
        if count["n"] % 20 == 0:
            print("  received {} messages (last: {} seq {} temp {})".format(
                count["n"], d.get("node_id"), d.get("sequence_no"), d.get("suhu")), flush=True)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    print("[MQTT sub] id={} broker={}:{} persistent={}".format(args.consumer_id, host, port, args.persistent))
    print("[MQTT sub] log: {}".format(path))
    client.connect_async(host, port, keepalive=args.keepalive)
    try:
        # keeps retrying if the broker is not reachable yet, instead of crashing
        client.loop_forever(retry_first_connection=True)
    except KeyboardInterrupt:
        print("\n[MQTT sub] stopped. {} messages in total".format(count["n"]))
        client.disconnect()
    finally:
        log.close()


if __name__ == "__main__":
    main()
