"""PLAYGROUND - experiment launcher for the MQTT vs REST lab on 4 laptops.

Every laptop runs the same command. The role of each laptop in each block is
defined in the tables below, so you only pick the laptop, block, protocol and
condition.

  python play.py                         # interactive menu
  python play.py --check                 # readiness check for this laptop
  python play.py johan B rest N3         # run directly
  python play.py johan B rest N3 --start-at 14:30:00
  python play.py wedanta A both single --dry-run   # only show what would run

Roles (see also laptops/<name>/ROLE.md):
  wedanta : COLLECTOR  - REST server, MQTT subscriber, local broker, Wireshark, analysis
  johan   : node 2     - sender; Wi-Fi is switched off on this laptop in Block D; consumer 1 in Block E
  nofa    : node 3     - sender; consumer 2 in Block E
  rahma   : node 4     - sender; consumer 3 in Block E
"""
import argparse
import os
import shutil
import socket
import subprocess
import sys
import threading
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

LAPTOPS = ["wedanta", "johan", "nofa", "rahma"]
COLLECTOR = "wedanta"
FAULT_NODE = "johan"
CONSUMER_ORDER = ["johan", "nofa", "rahma"]           # consumers 1, 2, 3 in Block E
SENDERS_BY_N = {"N2": ["johan"], "N3": ["johan", "nofa"], "N4": ["johan", "nofa", "rahma"]}

BLOCKS = {
    "A": {"title": "Functional validation (1 laptop)", "conditions": ["single"], "protocols": ["both", "rest", "mqtt"],
          "runs": 1, "duration": 300},
    "B": {"title": "Node scalability (2/3/4 laptops, campus Wi-Fi, 1 consumer)", "conditions": ["N2", "N3", "N4"],
          "protocols": ["rest", "mqtt"], "runs": 10, "duration": 60},
    "C": {"title": "Network quality and overhead (4 laptops)", "conditions": ["lan", "wifi", "limited"],
          "protocols": ["rest", "mqtt"], "runs": 10, "duration": 60},
    "D": {"title": "Resilience / fault injection (4 laptops)", "conditions": ["fault"], "protocols": ["rest", "mqtt"],
          "runs": 5, "duration": 90},
    "E": {"title": "Consumer fan-out (3 fixed senders)", "conditions": ["C1", "C2", "C3"],
          "protocols": ["rest", "mqtt"], "runs": 10, "duration": 60},
    "F": {"title": "MQTT QoS (optional, limited Wi-Fi)", "conditions": ["qos0", "qos1", "qos2"], "protocols": ["mqtt"],
          "runs": 10, "duration": 60},
}


def py(script, *a):
    return [sys.executable, "-u", os.path.join(ROOT, script)] + [str(x) for x in a]


def find_mosquitto():
    cand = [shutil.which("mosquitto"), r"C:\Program Files\mosquitto\mosquitto.exe",
            "/opt/homebrew/sbin/mosquitto", "/usr/local/sbin/mosquitto", "/usr/sbin/mosquitto"]
    for c in cand:
        if c and os.path.exists(c):
            return c
    return None


def build(laptop, block, proto, condition, o):
    """Return (receivers, senders, notes) for this laptop."""
    from common import config
    recv, send, notes = [], [], []
    b = BLOCKS[block]
    runs = o.runs or b["runs"]
    dur = o.duration or b["duration"]
    common_send = ["--block", block, "--condition", condition, "--runs", runs, "--duration", dur,
                   "--run-start", o.run_start]
    if o.interval:
        common_send += ["--interval", o.interval]
    if o.start_at:
        common_send += ["--start-at", o.start_at]
    tag = ["--block", block, "--condition", condition]

    broker = o.broker or ("local" if block == "E" else "cloud")
    mq = ["--broker", broker]
    # the collector reaches its own local broker through 127.0.0.1, whatever COLLECTOR_IP says
    mq_self = mq + (["--host", "127.0.0.1"] if broker == "local" else [])
    qos = []
    if block == "D":
        qos = ["--qos", 1, "--persistent", "--keepalive", 10]
    if block == "F":
        qos = ["--qos", int(condition.replace("qos", ""))]

    url = "http://{}:{}".format(config.collector_ip(), config.env("REST_PORT", 5151))
    if block == "C" and config.env("REST_PUBLIC_URL"):
        url = config.env("REST_PUBLIC_URL")
        notes.append("REST goes through ngrok: {}".format(url))
    if block == "A":
        url = "http://127.0.0.1:{}".format(config.env("REST_PORT", 5151))

    protos = ["rest", "mqtt"] if proto == "both" else [proto]

    # ---------------- collector ----------------
    if laptop == COLLECTOR:
        for p in protos:
            if p == "rest":
                recv.append(("REST-server", py("REST/server.py", *tag, "--receiver-id", laptop)))
                if block == "E":
                    recv.append(("CPU", py("tools/cpu_monitor.py", "--match", "REST/server.py", "--label", "rest", *tag)))
            else:
                if broker == "local":
                    m = find_mosquitto()
                    if m:
                        recv.append(("mosquitto", [m, "-c", os.path.join(ROOT, "broker", "mosquitto.conf")]))
                    else:
                        notes.append("Mosquitto not found. Install it from https://mosquitto.org/download/ "
                                     "then run: mosquitto -c broker/mosquitto.conf -v")
                    if block == "E":
                        recv.append(("CPU", py("tools/cpu_monitor.py", "--match", "mosquitto", "--label", "mqtt", *tag)))
                if block != "E":
                    recv.append(("MQTT-sub", py("MQTT/sub.py", *tag, "--consumer-id", laptop, *mq_self, *qos)))
        if block == "A":
            for p in protos:
                if p == "rest":
                    send.append(("REST-client", py("REST/client.py", "--node-id", laptop, "--server", url, *common_send)))
                else:
                    send.append(("MQTT-pub", py("MQTT/pub.py", "--node-id", laptop, *mq_self, *common_send)))
        if block == "C":
            notes.append("Wireshark filters: 'tcp.port == 5151' (REST LAN), 'tcp.port == 8883' (MQTT cloud), "
                         "'tcp.port == 1883' (local MQTT). For ngrok, capture on a sender laptop: 'tcp.port == 443'.")
        return recv, send, notes

    # ---------------- sender nodes ----------------
    if block == "A":
        notes.append("Block A only runs on {}'s laptop.".format(COLLECTOR.capitalize()))
        return recv, send, notes
    if block == "B" and laptop not in SENDERS_BY_N[condition]:
        notes.append("Laptop {} does NOT take part in {} (rest).".format(laptop, condition))
        return recv, send, notes

    for p in protos:
        if p == "rest":
            send.append(("REST-client", py("REST/client.py", "--node-id", laptop, "--server", url, *common_send)))
        else:
            send.append(("MQTT-pub", py("MQTT/pub.py", "--node-id", laptop, *mq, *qos, *common_send)))

    if block == "D" and laptop == FAULT_NODE:
        target = "{}:{}".format(config.collector_ip(), 5151) if proto == "rest" else (
            "1.1.1.1:443" if broker == "cloud" else "{}:1883".format(config.collector_ip()))
        recv.append(("link-watch", py("tools/link_watch.py", "--target", target, *tag)))
        notes.append("Each run lasts 90 s: around second 30, switch Wi-Fi off in the OS settings for 15 seconds, "
                     "then switch it back on. Do NOT close the Python window. link_watch records the down/up times.")

    if block == "E":
        k = int(condition.replace("C", ""))
        if laptop in CONSUMER_ORDER[:k]:
            for p in protos:
                if p == "rest":
                    recv.append(("dashboard", py("REST/dashboard.py", "--consumer-id", "dash-" + laptop,
                                                 "--server", url, *tag)))
                else:
                    recv.append(("MQTT-sub", py("MQTT/sub.py", "--consumer-id", "sub-" + laptop, *mq, *tag)))
    return recv, send, notes


def pump(label, proc):
    for line in proc.stdout:
        sys.stdout.write("[{:<11}] {}".format(label, line))
        sys.stdout.flush()


def run(recv, send):
    procs = []
    env = dict(os.environ, PYTHONIOENCODING="utf-8")

    def start(label, cmd):
        p = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, bufsize=1, env=env, encoding="utf-8", errors="replace")
        threading.Thread(target=pump, args=(label, p), daemon=True).start()
        procs.append((label, p))
        return p

    try:
        for label, cmd in recv:
            start(label, cmd)
        if recv:
            time.sleep(3)
        senders = [start(label, cmd) for label, cmd in send]
        for p in senders:
            p.wait()
        if recv:
            if senders:
                print("\n>>> All sender runs on this laptop are done. Receivers keep running; press Ctrl+C to stop.")
            while any(p.poll() is None for _, p in procs):
                time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n>>> Stopping all processes ...")
    finally:
        deadline = time.time() + 5
        for _, p in procs:
            while p.poll() is None and time.time() < deadline:
                time.sleep(0.1)
            if p.poll() is None:
                p.terminate()


def tcp_ok(host, port, timeout=2):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def check():
    from common import config
    print("Laptop          :", config.env("LAPTOP", "(not selected)"))
    print("Local IP        :", config.local_ip())
    print("COLLECTOR_IP    :", config.collector_ip())
    print("Group / topic   :", config.group(), "/", config.data_topic_base() + "/#")
    print("Python          :", sys.version.split()[0])
    for mod in ("paho.mqtt", "requests", "flask", "psutil", "ntplib", "pandas", "matplotlib"):
        try:
            m = __import__(mod, fromlist=["x"])
            print("  [OK] {:<11} {}".format(mod, getattr(m, "__version__", "")))
        except ImportError:
            print("  [--] {:<11} not installed (run 0_INSTALL.bat or pip install -r requirements.txt)".format(mod))
    try:
        import paho.mqtt as pm
        if not pm.__version__.startswith("2"):
            print("  [!!] paho-mqtt must be version 2.x (pip install -U paho-mqtt)")
    except ImportError:
        pass
    envf = os.path.join(ROOT, "MQTT", ".env")
    print("MQTT/.env       :", "present" if os.path.exists(envf) else "MISSING (copy MQTT/.env.example)")
    print("Cloud broker    :", "reachable" if tcp_ok(config.CLOUD_BROKER_HOST, 8883) else "NOT reachable")
    print("REST collector  :", "reachable" if tcp_ok(config.collector_ip(), 5151) else
          "not reachable (normal if the server is not running yet, or blocked by a firewall)")
    print("Local broker    :", "reachable" if tcp_ok(config.collector_ip(), 1883) else "not reachable")
    print("Local mosquitto :", find_mosquitto() or "-")
    print("\nClock check (NTP):")
    subprocess.call([sys.executable, os.path.join(ROOT, "tools", "clock_check.py")], cwd=ROOT)


def ask(prompt, choices, default=None):
    while True:
        s = input("{} {}{}: ".format(prompt, "/".join(choices), " [{}]".format(default) if default else "")).strip()
        if not s and default:
            return default
        if s in choices:
            return s
        print("  choose one of:", ", ".join(choices))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("laptop", nargs="?", choices=LAPTOPS)
    ap.add_argument("block", nargs="?", choices=list(BLOCKS))
    ap.add_argument("protocol", nargs="?", choices=["rest", "mqtt", "both"])
    ap.add_argument("condition", nargs="?")
    ap.add_argument("--start-at", default="", help="HH:MM:SS, the same on every laptop")
    ap.add_argument("--runs", type=int)
    ap.add_argument("--run-start", type=int, default=1)
    ap.add_argument("--duration", type=float)
    ap.add_argument("--interval", type=float)
    ap.add_argument("--broker", choices=["cloud", "local"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    remembered = os.path.join(ROOT, ".laptop")
    if not a.laptop:
        default = open(remembered).read().strip() if os.path.exists(remembered) else None
        a.laptop = ask("This laptop belongs to", LAPTOPS, default)
    with open(remembered, "w") as f:
        f.write(a.laptop)
    os.environ["LAPTOP"] = a.laptop
    from common import config
    config.load_dotenv(os.path.join(ROOT, "laptops", a.laptop, "laptop.env"))
    config.load_dotenv(os.path.join(ROOT, "laptops", "common.env"))

    if a.check:
        check()
        return
    if not a.block:
        for k, v in BLOCKS.items():
            print("  {}  {}".format(k, v["title"]))
        a.block = ask("Block", list(BLOCKS))
    b = BLOCKS[a.block]
    if not a.protocol:
        a.protocol = ask("Protocol", b["protocols"], b["protocols"][0])
    if a.protocol not in b["protocols"]:
        sys.exit("Protocol {} is not available in Block {}".format(a.protocol, a.block))
    if not a.condition:
        a.condition = ask("Condition", b["conditions"], b["conditions"][0])
    if a.condition not in b["conditions"]:
        sys.exit("Conditions for Block {}: {}".format(a.block, ", ".join(b["conditions"])))
    if not a.start_at and not a.dry_run and sys.stdin.isatty() and a.laptop != COLLECTOR:
        a.start_at = input("Synchronised start time (HH:MM:SS, empty = now): ").strip()

    recv, send, notes = build(a.laptop, a.block, a.protocol, a.condition, a)
    print("=" * 78)
    print("Laptop {} | Block {} ({}) | {} | condition {}".format(a.laptop, a.block, b["title"], a.protocol, a.condition))
    print("=" * 78)
    for n in notes:
        print("NOTE:", n)
    for label, cmd in recv + send:
        shown = " ".join('"{}"'.format(c) if " " in str(c) else str(c) for c in cmd)
        print("  [{}] {}".format(label, shown.replace(sys.executable, "python").replace(ROOT + os.sep, "")))
    if a.dry_run or not (recv or send):
        return
    run(recv, send)


if __name__ == "__main__":
    main()
