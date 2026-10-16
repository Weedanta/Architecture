"""Set the collector laptop's IP (Wedanta) and the ngrok URL in laptops/common.env.

Examples:
  python tools/set_collector.py                    (interactive)
  python tools/set_collector.py 192.168.1.23
  python tools/set_collector.py 192.168.1.23 https://abcd.ngrok-free.app
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "laptops", "common.env")


def set_key(text, key, value):
    pat = re.compile(r"^{}=.*$".format(key), re.M)
    line = "{}={}".format(key, value)
    return pat.sub(line, text) if pat.search(text) else text.rstrip("\n") + "\n" + line + "\n"


def main():
    with open(PATH, encoding="utf-8") as f:
        text = f.read()
    cur_ip = re.search(r"^COLLECTOR_IP=(.*)$", text, re.M)
    cur_url = re.search(r"^REST_PUBLIC_URL=(.*)$", text, re.M)
    cur_ip = cur_ip.group(1).strip() if cur_ip else ""
    cur_url = cur_url.group(1).strip() if cur_url else ""

    if len(sys.argv) > 1:
        ip = sys.argv[1]
        url = sys.argv[2] if len(sys.argv) > 2 else cur_url
    else:
        print("Current collector IP : {}".format(cur_ip or "-"))
        ip = input("Wedanta's laptop IP (Enter = keep): ").strip() or cur_ip
        print("Current ngrok URL    : {}".format(cur_url or "-"))
        url = input("ngrok URL for Block C (Enter = keep, '-' = clear): ").strip()
        url = "" if url == "-" else (url or cur_url)

    if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ip):
        sys.exit("Invalid IP: {}".format(ip))
    text = set_key(text, "COLLECTOR_IP", ip)
    text = set_key(text, "REST_PUBLIC_URL", url.rstrip("/"))
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print("Saved: COLLECTOR_IP={}  REST_PUBLIC_URL={}".format(ip, url.rstrip("/") or "(empty)"))


if __name__ == "__main__":
    main()
