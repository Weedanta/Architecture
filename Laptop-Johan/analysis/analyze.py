"""Raw logs -> LKM tables + charts.

Reads every file under logs/ (merged from all four laptops), then:
  * computes p50/p95/p99 latency, throughput and % lost messages per run
  * drops warm-up runs (runs 1 and 2 by default) for Blocks B, C, E, F
  * summarises across runs with median and IQR (Q3 - Q1)
  * writes results/summary.md (ready to copy into the LKM tables),
    results/per_run.csv and charts in figures/

Examples:
  python analysis/analyze.py
  python analysis/analyze.py --clock-correction    (use NTP offsets from logs/clock/)
  python analysis/analyze.py --fault-node johan    (laptop whose Wi-Fi is cut in Block D)
"""
import argparse
import pathlib
import re
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOGS = ROOT / "logs"
RESULTS = ROOT / "results"
FIGS = ROOT / "figures"
WARMUP_BLOCKS = {"B", "C", "E", "F"}
NAME_RE = re.compile(r"^(?P<proto>[a-z]+)_(?P<kind>[a-z]+)_(?P<ident>.+?)_(?P<session>[^_]+)\.csv$")


def read_kind(kind):
    frames = []
    for f in LOGS.glob("block*/*/*_{}_*.csv".format(kind)):
        m = NAME_RE.match(f.name)
        if not m:
            continue
        try:
            df = pd.read_csv(f)
        except pd.errors.EmptyDataError:
            continue
        if df.empty:
            continue
        df["block"] = f.parent.parent.name.replace("block", "")
        df["condition"] = f.parent.name
        df["proto"] = m["proto"]
        df["ident"] = m["ident"]
        df["session"] = m["session"]
        df["file"] = str(f.relative_to(ROOT))
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def laptop_of(ident):
    return str(ident).replace("dash-", "").replace("sub-", "")


def load_offsets():
    off = {}
    for f in (LOGS / "clock").glob("*.csv"):
        df = pd.read_csv(f)
        if not df.empty:
            off[str(df.iloc[-1]["laptop"])] = float(df.iloc[-1]["offset_ms"])
    return off


def q(s, p):
    return float(s.quantile(p)) if len(s) else float("nan")


def throughput(g):
    """Sum of per-node rates (messages/second). Computed per node so the result is
    not biased when laptops do not start at exactly the same moment."""
    tot = 0.0
    for _, gn in g.groupby("node_id"):
        span = (gn["t_recv_ms"].max() - gn["t_recv_ms"].min()) / 1000.0
        if span > 0:
            tot += (len(gn) - 1) / span
    return tot if tot > 0 else float("nan")


def per_run(recv, send, warmup):
    rows = []
    keys = ["block", "condition", "proto", "receiver_id", "run_id"]
    for k, g in recv.groupby(keys):
        block, condition, proto, rid, run = k
        lat = g["latency_ms"].dropna()
        sg = send[(send["block"] == block) & (send["condition"] == condition) & (send["proto"] == proto)
                  & (send["run_id"] == run)] if not send.empty else pd.DataFrame()
        if not sg.empty:
            generated = len(sg.drop_duplicates(["node_id", "sequence_no"]))
            nodes = sg["node_id"].unique()
            received = len(g[g["node_id"].isin(nodes)].drop_duplicates(["node_id", "sequence_no"]))
        else:
            generated = int(g.groupby("node_id")["sequence_no"].max().sum())
            received = len(g.drop_duplicates(["node_id", "sequence_no"]))
        lost = max(0, generated - received)
        rows.append({
            "block": block, "condition": condition, "protocol": proto, "receiver_id": rid, "run_id": run,
            "n_recv": len(g), "n_nodes": g["node_id"].nunique(),
            "p50_ms": q(lat, .5), "p95_ms": q(lat, .95), "p99_ms": q(lat, .99),
            "mean_ms": float(lat.mean()), "std_ms": float(lat.std()),
            "throughput_msg_s": throughput(g),
            "generated": generated, "received": received, "lost": lost,
            "loss_pct": 100.0 * lost / generated if generated else float("nan"),
            "warmup": (block in WARMUP_BLOCKS and run <= warmup),
        })
    return pd.DataFrame(rows)


def med_iqr(s):
    s = s.dropna()
    if s.empty:
        return "-"
    return "{:.1f} ({:.1f})".format(s.median(), s.quantile(.75) - s.quantile(.25))


def md_table(df, cols):
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(out)


def condition_order(k):
    m = re.search(r"(\d+)", str(k))
    order = {"lan": 0, "wifi": 1, "limited": 2, "single": 0, "fault": 0}
    return (order.get(str(k), 9), int(m.group(1)) if m else 0, str(k))


def sorted_groups(df, keys):
    return sorted(df.groupby(keys), key=lambda x: (x[0][0], condition_order(x[0][1])))


def summarize(pr, recv, send, cpu, link, args):
    md = ["# Experiment summary: MQTT vs REST",
          "", "Cell format: median (IQR) across runs, after dropping {} warm-up runs "
          "(Blocks B, C, E, F).".format(args.warmup), ""]
    use = pr[~pr["warmup"]]

    # ---------- Block A ----------
    a = recv[recv["block"] == "A"]
    if not a.empty:
        md += ["## Block A - Functional validation", ""]
        rows = []
        for proto, g in a.groupby("proto"):
            req = ["timestamp_iso", "node_id", "protocol", "t_send_ms", "t_recv_ms",
                   "payload_bytes", "suhu", "sequence_no"]
            empty = int(g[req].isna().sum().sum())
            gaps = 0
            for _, gg in g.groupby(["node_id", "run_id"]):
                s = sorted(gg["sequence_no"].unique())
                gaps += (s[-1] - s[0] + 1 - len(s)) if s else 0
            dur = (g["t_recv_ms"].max() - g["t_recv_ms"].min()) / 60000.0
            rows.append({"Protocol": proto.upper(), "Messages received": len(g), "Empty values": empty,
                         "sequence_no gaps": gaps, "Duration (min)": round(dur, 1)})
        md += [md_table(pd.DataFrame(rows), list(rows[0].keys())), ""]

    # ---------- Block B ----------
    b = use[use["block"] == "B"]
    if not b.empty:
        md += ["## Block B - Node scalability", ""]
        rows = []
        for (proto, k), g in sorted_groups(b, ["protocol", "condition"]):
            rows.append({"Protocol": proto.upper(), "N": k.replace("N", ""), "p50 (ms)": med_iqr(g["p50_ms"]),
                         "p95 (ms)": med_iqr(g["p95_ms"]), "p99 (ms)": med_iqr(g["p99_ms"]),
                         "Throughput (msg/s)": med_iqr(g["throughput_msg_s"]), "runs": len(g)})
        md += [md_table(pd.DataFrame(rows), list(rows[0].keys())), ""]

    # ---------- Block C ----------
    c = use[use["block"] == "C"]
    if not c.empty:
        md += ["## Block C - Network quality", ""]
        ov = {}
        ovf = RESULTS / "overhead_wireshark.csv"
        if ovf.exists():
            o = pd.read_csv(ovf)
            for _, r in o.iterrows():
                ov[(str(r["protocol"]).lower(), str(r["condition"]))] = r.get("bytes_per_message", "")
        rows = []
        for (proto, k), g in sorted_groups(c, ["protocol", "condition"]):
            rows.append({"Protocol": proto.upper(), "Condition": k, "Median latency (ms)": med_iqr(g["p50_ms"]),
                         "% lost": med_iqr(g["loss_pct"]),
                         "Overhead (bytes/msg)": ov.get((proto, k), "fill in from Wireshark"), "runs": len(g)})
        md += [md_table(pd.DataFrame(rows), list(rows[0].keys())), ""]

    # ---------- Block D ----------
    d_send = send[send["block"] == "D"] if not send.empty else pd.DataFrame()
    if not d_send.empty:
        md += ["## Block D - Resilience (node {})".format(args.fault_node), ""]
        rows = []
        dr = recv[recv["block"] == "D"]
        for (proto, run), g in d_send[d_send["node_id"] == args.fault_node].groupby(["proto", "run_id"]):
            t0, t1 = g["t_send_ms"].min(), g["t_send_ms"].max() + 5000
            down = up = "-"
            if not link.empty:
                ev = link[(link["t_ms"] >= t0) & (link["t_ms"] <= t1)]
                d_ = ev[ev["event"] == "DOWN"]
                u_ = ev[ev["event"] == "UP"]
                if not d_.empty:
                    down = str(d_.iloc[0]["timestamp_iso"])[11:23]
                if not u_.empty:
                    up = str(u_.iloc[-1]["timestamp_iso"])[11:23]
            gen = len(g)
            ok = int((g["status"] == "ok").sum()) if proto == "rest" else int((g["t_ack_ms"] > 0).sum())
            rr = dr[(dr["proto"] == proto) & (dr["run_id"] == run) & (dr["node_id"] == args.fault_node)]
            got = rr["sequence_no"].nunique()
            gaps = sorted(set(range(1, gen + 1)) - set(rr["sequence_no"].astype(int)))
            late = rr[rr["latency_ms"] > 2000]
            rows.append({"Protocol": proto.upper(), "Run": run, "Down at": down, "Up at": up,
                         "Generated": gen, "Sent/acked": ok, "Received": got, "Lost": gen - got,
                         "Delayed >2s": len(late),
                         "Lost seq": (str(gaps[0]) + "-" + str(gaps[-1])) if gaps else "-"})
        if rows:
            md += [md_table(pd.DataFrame(rows), list(rows[0].keys())), ""]

    # ---------- Block E ----------
    e = use[use["block"] == "E"]
    if not e.empty:
        md += ["## Block E - Consumer fan-out", ""]
        rows = []
        for (proto, k), g in sorted_groups(e, ["protocol", "condition"]):
            cpu_s = "-"
            if not cpu.empty:
                cc = cpu[(cpu["block"] == "E") & (cpu["condition"] == k) & (cpu["proto"] == proto)]
                if not cc.empty:
                    cpu_s = "{:.2f} (max {:.1f})".format(cc["proc_cpu_pct"].mean(), cc["proc_cpu_pct"].max())
            # consumers only (dashboard / subscriber), not the server's own POST log
            gg = g[g["receiver_id"].astype(str).str.startswith(("dash-", "sub-"))]
            gg = gg if not gg.empty else g
            rows.append({"Protocol": proto.upper(), "Consumers": k.replace("C", ""),
                         "Server/broker CPU (%)": cpu_s, "Median latency (ms)": med_iqr(gg["p50_ms"]),
                         "Throughput per consumer (msg/s)": med_iqr(gg["throughput_msg_s"]),
                         "Consumers in log": gg["receiver_id"].nunique()})
        md += [md_table(pd.DataFrame(rows), list(rows[0].keys())), ""]

    # ---------- Block F ----------
    f_ = use[use["block"] == "F"]
    if not f_.empty:
        md += ["## Block F - MQTT QoS", ""]
        rows = []
        for k, g in sorted(f_.groupby("condition"), key=lambda x: x[0]):
            rows.append({"QoS": k.replace("qos", ""), "Median latency (ms)": med_iqr(g["p50_ms"]),
                         "% lost": med_iqr(g["loss_pct"]), "runs": len(g)})
        md += [md_table(pd.DataFrame(rows), list(rows[0].keys())), ""]
    return "\n".join(md)


def plots(pr, recv):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed, skipping charts")
        return
    FIGS.mkdir(exist_ok=True)
    use = pr[~pr["warmup"]]
    b = use[use["block"] == "B"]
    if not b.empty:
        fig, ax = plt.subplots(figsize=(7, 4))
        for proto, g in b.groupby("protocol"):
            agg = g.groupby("condition")[["p50_ms", "p95_ms", "p99_ms"]].median()
            agg = agg.loc[sorted(agg.index, key=condition_order)]
            x = [int(k.replace("N", "")) for k in agg.index]
            for col, ls in (("p50_ms", "-"), ("p95_ms", "--"), ("p99_ms", ":")):
                ax.plot(x, agg[col], ls, marker="o", label="{} {}".format(proto.upper(), col[:3]))
        ax.set_xlabel("Number of laptops (N)")
        ax.set_ylabel("Latency (ms)")
        ax.set_title("Block B: latency percentiles vs N")
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(FIGS / "blockB_percentiles.png", dpi=150)
        plt.close(fig)
    for block in sorted(recv["block"].unique()):
        r = recv[(recv["block"] == block)]
        if block in WARMUP_BLOCKS:
            r = r[r["run_id"] > 2]
        if r.empty:
            continue
        groups = sorted(r.groupby(["proto", "condition"]), key=lambda x: (x[0][0], condition_order(x[0][1])))
        fig, ax = plt.subplots(figsize=(max(6, len(groups) * 1.1), 4))
        ax.boxplot([g["latency_ms"].dropna() for _, g in groups], showfliers=False)
        ax.set_xticks(range(1, len(groups) + 1))
        ax.set_xticklabels(["{}\n{}".format(p.upper(), k) for (p, k), _ in groups], fontsize=8)
        ax.set_ylabel("Latency (ms)")
        ax.set_title("Block {}: latency distribution (outliers hidden)".format(block))
        fig.tight_layout()
        fig.savefig(FIGS / "block{}_latency_boxplot.png".format(block), dpi=150)
        plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--warmup", type=int, default=2)
    ap.add_argument("--clock-correction", action="store_true")
    ap.add_argument("--fault-node", default="johan")
    args = ap.parse_args()

    recv = read_kind("recv")
    if recv.empty:
        print("No receiver logs in logs/ yet. Run the experiments first.")
        sys.exit(1)
    send = read_kind("send")
    cpu = read_kind("cpu")
    link = read_kind("linkwatch")

    recv = recv.drop_duplicates(["block", "condition", "proto", "receiver_id", "node_id", "run_id", "sequence_no"],
                                keep="last")
    if not send.empty:
        send = send.drop_duplicates(["block", "condition", "proto", "node_id", "run_id", "sequence_no"], keep="last")
    recv["latency_ms"] = recv["t_recv_ms"] - recv["t_send_ms"]
    if args.clock_correction:
        off = load_offsets()
        print("clock offsets (ms):", off)
        recv["latency_ms"] = (recv["latency_ms"]
                              + recv["receiver_id"].map(lambda r: off.get(laptop_of(r), 0.0))
                              - recv["node_id"].map(lambda n: off.get(laptop_of(n), 0.0)))

    pr = per_run(recv, send, args.warmup)
    RESULTS.mkdir(exist_ok=True)
    pr.sort_values(["block", "protocol", "condition", "receiver_id", "run_id"]).to_csv(
        RESULTS / "per_run.csv", index=False)
    md = summarize(pr, recv, send, cpu, link, args)
    (RESULTS / "summary.md").write_text(md, encoding="utf-8")
    plots(pr, recv)
    print(md)
    print("\nWritten: results/summary.md, results/per_run.csv, figures/*.png")


if __name__ == "__main__":
    main()
