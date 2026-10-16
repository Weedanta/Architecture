"""Simulated temperature sensor (the laptops have no physical sensor).

Readings stay around 26-30 degrees C with a slow drift and a little noise,
and each node gets its own baseline."""
import math
import random
import time
import zlib


class TemperatureSensor:
    def __init__(self, node_id, base=28.0):
        self.rng = random.Random(zlib.crc32(node_id.encode()))
        self.base = base + self.rng.uniform(-1.0, 1.0)
        self.t0 = time.time()

    def read(self):
        t = time.time() - self.t0
        drift = 1.2 * math.sin(2 * math.pi * t / 300.0)  # 5-minute cycle
        return round(self.base + drift + self.rng.gauss(0, 0.15), 2)


def build_payload(node_id, protocol, seq, run_id, temperature, t_send_ms):
    """Same JSON payload for REST and MQTT, so the application payload is identical.
    The key "suhu" follows the CSV schema in the LKM."""
    return {
        "node_id": node_id,
        "protocol": protocol,
        "t_send_ms": t_send_ms,
        "suhu": temperature,
        "sequence_no": seq,
        "run_id": run_id,
    }
