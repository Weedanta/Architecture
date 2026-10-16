"""Thread-safe CSV writer that flushes every row, so logs survive a forced stop."""
import csv
import threading

# Schema required by the LKM, plus run_id and receiver_id appended at the end
RECV_COLUMNS = [
    "timestamp_iso", "node_id", "protocol", "t_send_ms", "t_recv_ms",
    "payload_bytes", "suhu", "sequence_no", "run_id", "receiver_id",
]

# Sender log: t_ack_ms = HTTP response time (REST) or on_publish callback (MQTT)
SEND_COLUMNS = [
    "timestamp_iso", "node_id", "protocol", "t_send_ms", "t_ack_ms",
    "payload_bytes", "suhu", "sequence_no", "run_id", "status",
]

RTT_COLUMNS = ["timestamp_iso", "node_id", "protocol", "sequence_no", "run_id",
               "t_send_ms", "t_echo_ms", "rtt_ms"]


class CsvLog:
    def __init__(self, path, columns):
        self.path = path
        self.columns = columns
        self._lock = threading.Lock()
        new = not path.exists() or path.stat().st_size == 0
        self._f = open(path, "a", newline="", encoding="utf-8")
        self._w = csv.DictWriter(self._f, fieldnames=columns, extrasaction="ignore")
        if new:
            self._w.writeheader()
            self._f.flush()

    def write(self, row):
        with self._lock:
            self._w.writerow(row)
            self._f.flush()

    def close(self):
        with self._lock:
            self._f.close()
