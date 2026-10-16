"""Periodic run scheduler shared by REST/client.py and MQTT/pub.py.

One run sends a message every `interval` seconds for `duration` seconds, with
sequence_no starting at 1. Several runs are executed back to back with a
`gap` between them. Scheduling is fixed-rate, so drift does not accumulate."""
import argparse
import time

from common import config


def add_run_args(p: argparse.ArgumentParser):
    p.add_argument("--node-id", default=config.env("NODE_ID", config.env("LAPTOP", "node-1")))
    p.add_argument("--interval", type=float, default=float(config.env("INTERVAL", 1.0)),
                   help="seconds between messages (default 1.0)")
    p.add_argument("--duration", type=float, default=float(config.env("DURATION", 60)),
                   help="length of one run in seconds")
    p.add_argument("--runs", type=int, default=1, help="number of consecutive runs")
    p.add_argument("--run-start", type=int, default=1, help="number of the first run")
    p.add_argument("--gap", type=float, default=float(config.env("GAP", 5)),
                   help="pause between runs in seconds")
    p.add_argument("--block", default="A")
    p.add_argument("--condition", default="single")
    p.add_argument("--start-at", default="", help="HH:MM:SS, synchronised start across laptops")
    p.add_argument("--session", default=None, help="session tag used in log file names")


def run_loop(args, send_one, on_run_end=None):
    """Calls send_one(run_id, seq) on schedule.

    Run i starts at wall-clock time T0 + i*(duration+gap). When every laptop
    uses the same --start-at (and clocks are in sync), run i overlaps on all of them."""
    config.wait_until(args.start_at)
    T0 = time.time()
    period = args.duration + args.gap
    n_msgs = max(1, int(round(args.duration / args.interval)))
    for i in range(args.runs):
        run_id = args.run_start + i
        t0 = T0 + i * period
        delay = t0 - time.time()
        if delay > 0:
            time.sleep(delay)
        print("[run {}] start: {} messages, interval {} s".format(run_id, n_msgs, args.interval), flush=True)
        for seq in range(1, n_msgs + 1):
            target = t0 + (seq - 1) * args.interval
            delay = target - time.time()
            if delay > 0:
                time.sleep(delay)
            send_one(run_id, seq)
        if on_run_end:
            on_run_end(run_id)
        print("[run {}] done.".format(run_id), flush=True)
