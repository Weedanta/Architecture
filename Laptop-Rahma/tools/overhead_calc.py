"""Per-message overhead at the application layer (no Wireshark needed).

* REST : rebuilds the exact HTTP request bytes that `requests` sends and, when
         --server is given, sends them over a raw socket to measure the HTTP
         response bytes from the running Flask server.
* MQTT : computes PUBLISH (+ PUBACK / PUBREC-PUBREL-PUBCOMP) sizes from the
         MQTT 3.1.1 specification with the same topic and payload.

These numbers are a lower bound (TCP/IP, TLS and handshakes are not included);
Wireshark is still used for on-the-wire numbers in Block C.

Examples:
  python tools/overhead_calc.py
  python tools/overhead_calc.py --server http://127.0.0.1:5151
"""
import argparse
import json
import os
import socket
import sys
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests  # noqa: E402

from common import config  # noqa: E402
from common.sensor import build_payload  # noqa: E402


def http_request_bytes(url, body):
    s = requests.Session()
    prep = s.prepare_request(requests.Request("POST", url, data=body,
                                              headers={"Content-Type": "application/json"}))
    u = urlparse(url)
    lines = ["POST {} HTTP/1.1".format(u.path or "/"), "Host: {}".format(u.netloc)]
    for k, v in prep.headers.items():
        lines.append("{}: {}".format(k, v))
    head = ("\r\n".join(lines) + "\r\n\r\n").encode()
    return head, head + body


def http_response_bytes(url, raw_request):
    u = urlparse(url)
    port = u.port or 80
    with socket.create_connection((u.hostname, port), timeout=3) as s:
        s.sendall(raw_request)
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = s.recv(4096)
            if not chunk:
                break
            data += chunk
        head, _, rest = data.partition(b"\r\n\r\n")
        clen = 0
        for line in head.split(b"\r\n"):
            if line.lower().startswith(b"content-length:"):
                clen = int(line.split(b":")[1])
        while len(rest) < clen:
            chunk = s.recv(4096)
            if not chunk:
                break
            rest += chunk
    return head + b"\r\n\r\n", rest[:clen]


def remaining_length_size(n):
    size = 1
    while n > 127:
        n //= 128
        size += 1
    return size


def mqtt_publish_size(topic, payload_len, qos):
    var = 2 + len(topic.encode()) + (2 if qos > 0 else 0)
    rem = var + payload_len
    return 1 + remaining_length_size(rem) + rem, 1 + remaining_length_size(rem) + var


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default=None, help="URL of a running REST server (optional)")
    ap.add_argument("--node-id", default="johan")
    a = ap.parse_args()

    url = (a.server or "http://192.168.1.10:5151").rstrip("/") + "/suhu"
    # run_id 0 marks a probe request: the server answers but does not log it
    payload = json.dumps(build_payload(a.node_id, "rest", 123, 0, 28.41, config.now_ms())).encode()
    payload_mqtt = json.dumps(build_payload(a.node_id, "mqtt", 123, 0, 28.41, config.now_ms())).encode()
    head, raw = http_request_bytes(url, payload)

    print("JSON payload (application)  : {} bytes".format(len(payload)))
    print("  sample: {}".format(payload.decode()))
    print()
    print("REST - HTTP request")
    print("  request line + headers     : {} bytes".format(len(head)))
    print("  total request              : {} bytes".format(len(raw)))
    resp_head = resp_body = None
    if a.server:
        try:
            resp_head, resp_body = http_response_bytes(url, raw)
            print("REST - HTTP response (measured from the server)")
            print("  response headers           : {} bytes".format(len(resp_head)))
            print("  response body              : {} bytes".format(len(resp_body)))
        except OSError as e:
            print("  (could not reach the server: {})".format(e))
    print("  --- raw request headers ---")
    print("  " + head.decode().replace("\r\n", "\n  "))
    if resp_head:
        print("  --- raw response headers ---")
        print("  " + resp_head.decode().replace("\r\n", "\n  "))

    topic = config.data_topic(a.node_id)
    print()
    print("MQTT - topic '{}' ({} bytes)".format(topic, len(topic)))
    for q in (0, 1, 2):
        total, hdr = mqtt_publish_size(topic, len(payload_mqtt), q)
        ctrl = {0: 0, 1: 4, 2: 12}[q]
        print("  QoS {}: PUBLISH {} bytes (header {} bytes) + control {} bytes = {} bytes per message".format(
            q, total, hdr, ctrl, total + ctrl))
    print()
    rest_total = len(raw) + (len(resp_head) + len(resp_body) if resp_head else 0)
    q0, h0 = mqtt_publish_size(topic, len(payload_mqtt), 0)
    print("SUMMARY, application layer only (no TCP/IP/TLS):")
    print("  REST request only          : {} bytes  (header overhead {} bytes)".format(len(raw), len(head)))
    if resp_head:
        print("  REST request + response    : {} bytes".format(rest_total))
    print("  MQTT QoS 0                 : {} bytes  (header overhead {} bytes)".format(q0, h0))
    print("  Ratio REST(req)/MQTT(QoS0) : {:.1f}x".format(len(raw) / q0))


if __name__ == "__main__":
    main()
