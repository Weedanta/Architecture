#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analisis log mentah -> tabel per-run, ringkasan (median + IQR), dan grafik.

Cara pakai:
  1. Kumpulkan folder logs/ dari setiap laptop ke logs_all/<nama>/
     (misal logs_all/johan/, logs_all/nova/, ...).
  2. python analysis/analyze.py --logs logs_all --out hasil

Keluaran (folder hasil/):
  per_run.csv    : satu baris per (exp, protocol, run, penerima)
  per_node.csv   : terkirim/diterima/hilang per node (tabel Blok D)
  ringkasan.csv  : median dan IQR antar-run per (exp, protocol)
  grafik_<blok>.png
"""
import argparse
import glob
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402


def kind_of(fname):
    base = os.path.basename(fname)
    for k in ("send_", "ack_", "recv_", "poll_", "cpu_"):
        if base.startswith(k):
            return k[:-1]
    return None


def load(logs_dir):
    frames = []
    for f in glob.glob(os.path.join(logs_dir, "**", "*.csv"), recursive=True):
        k = kind_of(f)
        if k in (None, "cpu"):
            continue
        df = pd.read_csv(f)
        if df.empty:
            continue
        df["kind"] = k
        df["receiver"] = os.path.splitext(os.path.basename(f))[0] if k in ("recv", "poll") else ""
        df["source_file"] = os.path.relpath(f, logs_dir)
        frames.append(df)
    if not frames:
        raise SystemExit(f"Tidak ada log CSV di {logs_dir}")
    df = pd.concat(frames, ignore_index=True)
    df = df.dropna(subset=["exp", "run"])
    df["run"] = df["run"].astype(int)
    for c in ("t_send_ms", "t_recv_ms", "rtt_ms", "sequence_no", "payload_bytes"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def pct(s, q):
    s = s.dropna()
    return float(np.percentile(s, q)) if len(s) else np.nan


def per_run(df):
    rows = []
    send = df[df.kind == "send"]
    for (exp, proto, run), g in df.groupby(["exp", "protocol", "run"]):
        s = send[(send.exp == exp) & (send.protocol == proto) & (send.run == run)]
        n_sent = len(s.drop_duplicates(["node_id", "sequence_no"]))
        # RTT: REST dari log pengirim (status ok), MQTT dari log echo
        if proto == "rest":
            rtt = s.loc[s.status == "ok", "rtt_ms"]
        else:
            rtt = g.loc[g.kind == "ack", "rtt_ms"]
        recv = g[g.kind.isin(["recv", "poll"])]
        receivers = recv.receiver.unique() if len(recv) else [""]
        for rc in receivers:
            r = recv[recv.receiver == rc]
            first = r.sort_values("t_recv_ms").drop_duplicates(["node_id", "sequence_no"])
            n_recv = len(first)
            span = (first.t_recv_ms.max() - first.t_recv_ms.min()) / 1000 if n_recv > 1 else np.nan
            oneway = first.t_recv_ms - first.t_send_ms
            rows.append({
                "exp": exp, "protocol": proto, "run": run, "receiver": rc,
                "n_nodes": s.node_id.nunique(),
                "sent": n_sent, "received": n_recv, "lost": max(n_sent - n_recv, 0),
                "loss_pct": 100 * max(n_sent - n_recv, 0) / n_sent if n_sent else np.nan,
                "duplicates": len(r) - n_recv,
                "rtt_p50": pct(rtt, 50), "rtt_p95": pct(rtt, 95), "rtt_p99": pct(rtt, 99),
                "oneway_p50": pct(oneway, 50), "oneway_p95": pct(oneway, 95),
                "oneway_p99": pct(oneway, 99),
                "throughput_msg_s": n_recv / span if span and span > 0 else np.nan,
                "payload_bytes_mean": r.payload_bytes.mean(),
            })
    return pd.DataFrame(rows)


def per_node(df):
    """Pesan terkirim/diterima/hilang per node (untuk tabel Blok D)."""
    rows = []
    send = df[df.kind == "send"]
    recv = df[df.kind.isin(["recv", "poll"])]
    for (exp, proto, run, node), s in send.groupby(["exp", "protocol", "run", "node_id"]):
        n_sent = len(s.drop_duplicates("sequence_no"))
        r_all = recv[(recv.exp == exp) & (recv.protocol == proto) & (recv.run == run)
                     & (recv.node_id == node)]
        for rc, r in r_all.groupby("receiver"):
            n_recv = r.sequence_no.nunique()
            rows.append({"exp": exp, "protocol": proto, "run": run, "node_id": node,
                         "receiver": rc, "sent": n_sent, "received": n_recv,
                         "lost": max(n_sent - n_recv, 0),
                         "not_sent_immediately": int((~s.status.isin(["ok", "sent"])).sum())})
    return pd.DataFrame(rows)


def summarize(pr, warmup, no_warmup_prefix):
    metrics = ["rtt_p50", "rtt_p95", "rtt_p99", "oneway_p50", "oneway_p95", "oneway_p99",
               "throughput_msg_s", "loss_pct"]
    out = []
    for (exp, proto), g in pr.groupby(["exp", "protocol"]):
        if not str(exp).startswith(tuple(no_warmup_prefix)):
            g = g[g.run > warmup]  # buang run warm-up
        row = {"exp": exp, "protocol": proto, "n_runs": g.run.nunique()}
        for m in metrics:
            v = g[m].dropna()
            row[f"{m}_median"] = v.median() if len(v) else np.nan
            row[f"{m}_iqr"] = (v.quantile(.75) - v.quantile(.25)) if len(v) else np.nan
        out.append(row)
    return pd.DataFrame(out)


def plot(summary, out_dir, latency):
    summary = summary.copy()
    summary["blok"] = summary.exp.astype(str).str.split("_").str[0]
    for blok, g in summary.groupby("blok"):
        exps = sorted(g.exp.unique())
        x = np.arange(len(exps))
        fig, ax = plt.subplots(figsize=(max(6, 1.3 * len(exps)), 4))
        for i, proto in enumerate(["rest", "mqtt"]):
            h = g[g.protocol == proto].set_index("exp").reindex(exps)
            ax.bar(x + (i - 0.5) * 0.38, h[f"{latency}_p50_median"], 0.38,
                   yerr=h[f"{latency}_p50_iqr"] / 2, capsize=3, label=proto.upper())
        ax.set_xticks(x, exps)
        ax.set_ylabel(f"Latensi {latency} p50 (ms), median antar-run")
        ax.set_title(f"Blok {blok}: latensi p50 (garis = IQR)")
        ax.legend()
        fig.tight_layout()
        fig.savefig(os.path.join(out_dir, f"grafik_{blok}.png"), dpi=150)
        plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", default="logs_all")
    ap.add_argument("--out", default="hasil")
    ap.add_argument("--warmup", type=int, default=2, help="Jumlah run awal yang dibuang")
    ap.add_argument("--no-warmup", default="A,D",
                    help="Prefiks exp yang tidak dibuang warm-up-nya (dipisah koma)")
    ap.add_argument("--latency", default="rtt", choices=["rtt", "oneway"],
                    help="Latensi untuk grafik. Pakai oneway hanya jika jam sudah sinkron")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    df = load(args.logs)
    pr = per_run(df)
    pr.to_csv(os.path.join(args.out, "per_run.csv"), index=False)
    per_node(df).to_csv(os.path.join(args.out, "per_node.csv"), index=False)
    sm = summarize(pr, args.warmup, args.no_warmup.split(","))
    sm.to_csv(os.path.join(args.out, "ringkasan.csv"), index=False)
    plot(sm, args.out, args.latency)

    pd.set_option("display.width", 200)
    cols = ["exp", "protocol", "n_runs", f"{args.latency}_p50_median", f"{args.latency}_p95_median",
            f"{args.latency}_p99_median", "throughput_msg_s_median", "loss_pct_median"]
    print(sm[cols].round(2).to_string(index=False))
    print(f"\nTersimpan di folder {args.out}/")


if __name__ == "__main__":
    main()
