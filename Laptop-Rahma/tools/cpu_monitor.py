"""CPU monitor for the server / broker process (Block E).

Finds the process by --pid or by part of its name / command line and logs
cpu% (normalised to the number of cores) once per second.

Examples (on the collector laptop):
  python tools/cpu_monitor.py --match REST/server.py --label rest --block E --condition C2
  python tools/cpu_monitor.py --match mosquitto     --label mqtt --block E --condition C2
"""
import argparse
import csv
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psutil  # noqa: E402

from common import config  # noqa: E402


def find_proc(match):
    me = os.getpid()
    m = match.lower().replace("\\", "/")
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        if p.info["pid"] == me:
            continue
        cmd = " ".join(p.info["cmdline"] or []).lower().replace("\\", "/")
        name = (p.info["name"] or "").lower()
        if m in name or m in cmd:
            return p
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int)
    ap.add_argument("--match", help="e.g. REST/server.py or mosquitto")
    ap.add_argument("--label", required=True, help="rest / mqtt")
    ap.add_argument("--interval", type=float, default=1.0)
    ap.add_argument("--block", default="E")
    ap.add_argument("--condition", default="C1")
    ap.add_argument("--session", default=None)
    a = ap.parse_args()

    proc = psutil.Process(a.pid) if a.pid else None
    while proc is None:
        proc = find_proc(a.match or "")
        if proc is None:
            print("waiting for process '{}' ...".format(a.match))
            time.sleep(2)
    ncpu = psutil.cpu_count() or 1
    path = config.log_path(a.block, a.condition, a.label, "cpu", config.env("LAPTOP", "host"), a.session)
    new = not path.exists()
    f = open(path, "a", newline="", encoding="utf-8")
    w = csv.writer(f)
    if new:
        w.writerow(["timestamp_iso", "t_ms", "pid", "proc_cpu_pct", "proc_cpu_pct_1core", "system_cpu_pct", "rss_mb"])
    print("monitoring pid {} ({}) -> {}".format(proc.pid, proc.name(), path))
    proc.cpu_percent(None)
    psutil.cpu_percent(None)
    try:
        while True:
            time.sleep(a.interval)
            c1 = proc.cpu_percent(None)
            w.writerow([config.iso_now(), config.now_ms(), proc.pid, round(c1 / ncpu, 2), round(c1, 2),
                        psutil.cpu_percent(None), round(proc.memory_info().rss / 1e6, 1)])
            f.flush()
    except (KeyboardInterrupt, psutil.NoSuchProcess):
        print("monitor stopped")
    finally:
        f.close()


if __name__ == "__main__":
    main()
