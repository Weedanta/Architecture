"""Shared configuration for every script in the playground.

Value sources, first match wins:
  1. existing environment variables
  2. MQTT/.env                     (broker credentials from the lecturer, never committed)
  3. laptops/<LAPTOP>/laptop.env   (identity of this laptop)
  4. laptops/common.env            (group-wide settings: collector IP, group name, run timing)
"""
import os
import pathlib
import socket
import time
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs"

# Cloud broker from the lecturer's reference repository (HiveMQ Cloud, TLS on 8883)
CLOUD_BROKER_HOST = "fec429b2a5b94f3096cda8a658769824.s1.eu.hivemq.cloud"
CLOUD_BROKER_PORT = 8883
LOCAL_BROKER_PORT = 1883
REST_PORT_DEFAULT = 5151


def load_dotenv(path):
    """Minimal .env parser, same behaviour as the reference repository
    (never overrides variables that are already set)."""
    path = pathlib.Path(path)
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _remembered_laptop():
    f = ROOT / ".laptop"
    if f.exists():
        return f.read_text(encoding="utf-8").strip()
    return ""


def load_all():
    load_dotenv(ROOT / "MQTT" / ".env")
    laptop = os.environ.get("LAPTOP") or _remembered_laptop()
    if laptop:
        os.environ.setdefault("LAPTOP", laptop)
        load_dotenv(ROOT / "laptops" / laptop / "laptop.env")
    load_dotenv(ROOT / "laptops" / "common.env")


load_all()


def env(name, default=None):
    v = os.environ.get(name)
    return v if v not in (None, "") else default


def group():
    return env("GROUP", "kelompok-jnrw")


def data_topic_base():
    return "sister/temp/{}".format(group())


def data_topic(node_id):
    return "{}/{}".format(data_topic_base(), node_id)


def echo_topic(node_id):
    return "sister/echo/{}/{}".format(group(), node_id)


def collector_ip():
    return env("COLLECTOR_IP", "127.0.0.1")


def rest_url_default():
    return env("SERVER_URL", "http://{}:{}".format(collector_ip(), env("REST_PORT", REST_PORT_DEFAULT)))


def now_ms():
    """Epoch time in milliseconds (int)."""
    return time.time_ns() // 1_000_000


def iso_now():
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def local_ip():
    """Local IP used for outbound traffic (no packet is actually sent)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def log_path(block, condition, protocol, kind, ident, session=None):
    """logs/block<X>/<condition>/<protocol>_<kind>_<ident>_<session>.csv"""
    session = session or env("SESSION", datetime.now().strftime("%Y%m%d"))
    d = LOG_DIR / "block{}".format(block) / str(condition)
    d.mkdir(parents=True, exist_ok=True)
    return d / "{}_{}_{}_{}.csv".format(protocol, kind, ident, session)


def wait_until(start_at):
    """start_at is HH:MM:SS local time, so every laptop can start together."""
    if not start_at:
        return
    now = datetime.now()
    h, m, s = [int(x) for x in start_at.split(":")]
    target = now.replace(hour=h, minute=m, second=s, microsecond=0)
    delta = (target - now).total_seconds()
    if delta < 0:
        print("[info] start time {} already passed, starting now.".format(start_at))
        return
    print("[info] waiting {:.1f} s until {} ...".format(delta, start_at))
    time.sleep(delta)
