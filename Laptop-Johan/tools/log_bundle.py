"""Move logs between laptops.

  python tools/log_bundle.py pack    -> creates logs_<laptop>.zip from this laptop's logs/ folder
                                        (send that file to Wedanta)
  python tools/log_bundle.py merge   -> (on Wedanta's laptop) extracts every logs_*.zip found in the
                                        project root or in received_logs/ into logs/
Log file names are unique per laptop, so merging never overwrites anything.
"""
import glob
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def pack():
    from common import config
    laptop = config.env("LAPTOP", "laptop")
    out = os.path.join(ROOT, "logs_{}.zip".format(laptop))
    n = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for path in glob.glob(os.path.join(ROOT, "logs", "**", "*.csv"), recursive=True):
            z.write(path, os.path.relpath(path, ROOT))
            n += 1
    print("{} log files packed into {}".format(n, out))
    print("Send this file to Wedanta (WhatsApp, Drive or a flash drive).")


def merge():
    zips = glob.glob(os.path.join(ROOT, "logs_*.zip")) + glob.glob(os.path.join(ROOT, "received_logs", "*.zip"))
    if not zips:
        print("No logs_*.zip found. Put your teammates' zip files in this folder or in received_logs/.")
        return
    for zp in zips:
        with zipfile.ZipFile(zp) as z:
            names = [n for n in z.namelist() if n.startswith("logs/") and n.endswith(".csv") and ".." not in n]
            for n in names:
                z.extract(n, ROOT)
        print("{}: {} log files merged".format(os.path.basename(zp), len(names)))
    print("Done. Run the analysis next: python analysis/analyze.py")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("pack", "merge"):
        print(__doc__)
        sys.exit(1)
    pack() if sys.argv[1] == "pack" else merge()
