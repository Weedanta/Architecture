# MQTT vs REST Lab Playground: Distributed Temperature Sensors

Group repository for the LKM *Sensor Suhu Terdistribusi: Perbandingan MQTT dan REST*
(Distributed Systems, S2). The base code comes from the lecturer's reference repository
`filkom.ub.ac.id/git/widhi/distributed-system` (the `REST/` and `MQTT/` folders). It was
modified as required by Step 1 of the LKM, and `play.py` was added so the same experiment
can be launched on four laptops.

Members and laptops:

| Laptop | Owner | Main role | Role sheet |
|---|---|---|---|
| 1 | Wedanta | **Collector**: REST server, MQTT subscriber, local broker (Block E), Wireshark, ngrok, analysis | [laptops/wedanta/ROLE.md](laptops/wedanta/ROLE.md) |
| 2 | Johan | Sender node 2, fault-injection laptop (Block D), consumer 1 (Block E) | [laptops/johan/ROLE.md](laptops/johan/ROLE.md) |
| 3 | Nofa | Sender node 3, consumer 2 (Block E) | [laptops/nofa/ROLE.md](laptops/nofa/ROLE.md) |
| 4 | Rahma | Sender node 4, consumer 3 (Block E) | [laptops/rahma/ROLE.md](laptops/rahma/ROLE.md) |

```
                       +---------------------------+
   Johan  (node 2) --->|                           |
   Nofa   (node 3) --->|  Wedanta (collector)      |---> logs/*.csv ---> analysis/analyze.py
   Rahma  (node 4) --->|  REST server :5151        |
        REST: POST /suhu  MQTT sub / broker :1883  |
        MQTT: publish ----> HiveMQ Cloud :8883 ----+  (lecturer's cloud broker, TLS)
                       +---------------------------+
```

## 1. Setup (every laptop)

```bash
git clone <group-repo-url>
cd sister-mqtt-rest-playground
pip install -r requirements.txt          # paho-mqtt 2.x, requests, flask, psutil, ntplib, pandas, matplotlib
copy MQTT\.env.example MQTT\.env         # macOS/Linux: cp MQTT/.env.example MQTT/.env
```

1. Put the lecturer's credentials in `MQTT/.env`. The file is in `.gitignore`; **do not commit it**.
2. Wedanta runs `ipconfig` (Windows) or `ifconfig` (macOS). Everyone writes that IP into
   `COLLECTOR_IP` in `laptops/common.env`, or runs `python tools/set_collector.py`.
3. Wedanta allows Python (port 5151) and Mosquitto (port 1883) through Windows Firewall.
   Choose **Allow** the first time Windows asks.
4. Check each laptop with `python play.py <name> --check`. It verifies the libraries, `.env`,
   access to the broker and the collector, and the **NTP clock offset**.
5. Sync the clock if the offset is above 50 ms (Windows: *Settings > Time & language > Sync now*).
   If that does not work, use RTT mode (section 6).

## 2. Running an experiment

One launcher for every laptop. The role of each laptop in each block is set automatically.

```bash
python play.py                                    # interactive menu
python play.py <laptop> <block> <protocol> <condition> [--start-at HH:MM:SS]
python play.py johan B rest N3 --start-at 14:30:00
python play.py wedanta C mqtt wifi --dry-run      # only print the processes that would run
```

Order for each condition:

1. **Wedanta** starts first (receiver side).
2. Agree on a start time, for example one minute from now. **Johan, Nofa and Rahma** start
   their command with the same `--start-at`.
3. Senders run every run automatically (default 10 runs x 60 s, 5 s apart) and then stop.
4. When all senders are done, Wedanta presses Ctrl+C. Move on to the next condition.

| Block | Conditions | Runs x duration | Senders | Receivers |
|---|---|---|---|---|
| A | `single` | 1 x 300 s | Wedanta (REST + MQTT) | Wedanta |
| B | `N2`, `N3`, `N4` | 10 x 60 s | N2: Johan; N3: + Nofa; N4: + Rahma | Wedanta (1 consumer) |
| C | `lan`, `wifi`, `limited` | 10 x 60 s | Johan, Nofa, Rahma | Wedanta (+ Wireshark) |
| D | `fault` | 5 x 90 s | Johan, Nofa, Rahma (Johan's Wi-Fi off for 15 s) | Wedanta |
| E | `C1`, `C2`, `C3` | 10 x 60 s | Johan, Nofa, Rahma | consumers: C1 Johan, C2 + Nofa, C3 + Rahma; CPU measured on Wedanta |
| F | `qos0`, `qos1`, `qos2` | 10 x 60 s | Johan, Nofa, Rahma | Wedanta (limited Wi-Fi) |

"Number of laptops N" in Block B includes the collector (N2 = Wedanta + Johan).
The first two runs of each condition are dropped as warm-up during analysis (Blocks B, C, E, F).

## 3. Network conditions (Blocks C and F)

| Condition | How |
|---|---|
| `lan` | All four laptops on LAN cables to the same switch or router, Wi-Fi off. |
| `wifi` | All laptops on the same campus Wi-Fi. |
| `limited` | A phone hotspot with weak signal or a small data quota, **or** on Windows [clumsy](https://jagt.github.io/clumsy/) (e.g. 100 ms lag, 5 % drop), on macOS Network Link Conditioner, on Linux `tc qdisc add dev wlan0 root netem delay 100ms loss 5%`. Write down the settings you used. |

Across networks, MQTT always goes through HiveMQ Cloud. To keep REST comparable, Wedanta runs
`ngrok http 5151` and every laptop sets `REST_PUBLIC_URL` in `laptops/common.env`.
When `REST_PUBLIC_URL` is set, REST senders in Block C use that URL automatically.

## 4. Measuring overhead with Wireshark (Block C)

* Filters: `tcp.port == 5151` (REST on LAN), `tcp.port == 443` (REST through ngrok, capture on a sender),
  `tcp.port == 8883` (MQTT cloud, TLS), `tcp.port == 1883` (local MQTT broker, headers in plain text).
* **Bytes per message** = total frame bytes of that conversation in both directions
  (*Statistics > Conversations > TCP*) divided by the number of messages in the capture. For REST,
  include the TCP handshake and FIN packets, because the Flask server closes the connection after every response.
* Put the numbers in `results/overhead_wireshark.csv`; `analyze.py` adds them to the Block C table.
* Application-layer comparison without Wireshark: `python tools/overhead_calc.py --server http://<COLLECTOR_IP>:5151`.

## 5. Collecting logs and analysis

Raw logs are written to `logs/block<X>/<condition>/<protocol>_<send|recv|cpu|linkwatch>_<id>_<date>.csv`.
File names are unique per laptop, so each member can commit their own `logs/` folder and push
without conflicts. Without git, use `python tools/log_bundle.py pack` on each sender laptop and
`python tools/log_bundle.py merge` on Wedanta's laptop. Once every log is on one laptop:

```bash
python analysis/analyze.py                     # tables -> results/summary.md, per run -> results/per_run.csv, charts -> figures/
python analysis/analyze.py --clock-correction  # correct latency with the NTP offsets in logs/clock/
```

Cells in the summary are **median (IQR)** across runs and can be copied straight into the LKM tables.

## 6. RTT mode (when clocks cannot be synchronised)

* REST: `t_ack_ms - t_send_ms` in the sender log is already the RTT.
* MQTT: start the subscriber with `--echo` and the publisher with `--rtt`; results go to
  `logs/.../mqtt_rtt_<node>_*.csv`.

## 7. Log schema

Receiver logs (`*_recv_*.csv`) follow the LKM schema, with `run_id` and `receiver_id` appended:

`timestamp_iso, node_id, protocol, t_send_ms, t_recv_ms, payload_bytes, suhu, sequence_no, run_id, receiver_id`

Sender logs (`*_send_*.csv`): `timestamp_iso, node_id, protocol, t_send_ms, t_ack_ms, payload_bytes, suhu, sequence_no, run_id, status`

* `t_ack_ms`: REST = when the HTTP response arrived; MQTT = the `on_publish` callback (QoS 0: written to the socket, QoS 1: PUBACK, QoS 2: PUBCOMP). `-1` if it failed.
* `status`: `ok`, `fail:<Exception>` (REST), `queued` (MQTT QoS > 0 while disconnected, resent later), `noack:*`.

The column name `suhu` (temperature) is kept as written in the LKM schema.

## 8. Code changes (LKM Step 1)

| File | Change |
|---|---|
| `REST/client.py` | Periodic `POST /suhu` loop; payload with `node_id`, `t_send_ms`, `suhu`, `sequence_no`, `run_id`; sender log; no retry by default. |
| `REST/server.py` | Original `/add` and `/mul` endpoints kept; `POST /suhu` records `t_recv` on arrival and appends a CSV row; `GET /latest` for polling dashboards; binds to `0.0.0.0`. |
| `REST/dashboard.py` | New: polling consumer for Block E. |
| `MQTT/pub.py` | JSON payload with `node_id`, `t_send_ms`, `sequence_no`; topic `sister/temp/<GROUP>/<node>`; configurable QoS, keepalive and persistent session; sender log. |
| `MQTT/sub.py` | Subscribes to `sister/temp/<GROUP>/#`; records `t_recv` on arrival and appends a CSV row; QoS and persistent session; `--echo` option. |
| Both paths | `sequence_no` increases with every message and restarts at 1 for each run, so lost messages can be detected. |

## 9. Design decisions to mention in the methodology chapter

* The JSON payload is identical for REST and MQTT (about 110-117 bytes, depending on the length of node_id and sequence_no), so differences in overhead come from the protocols alone.
* The temperature sensor is simulated (26-30 degrees C with noise) because the laptops have no physical sensor.
* REST runs without retry and without keep-alive (Flask's Werkzeug server answers `Connection: close`).
* Block D: MQTT uses QoS 1, a persistent session and a 10 s keepalive; REST has no retry and a 2 s timeout.
* Block E: MQTT uses a local Mosquitto broker on Wedanta's laptop so broker CPU can be measured
  (HiveMQ Cloud CPU is not accessible). REST dashboards poll every 0.2 s.
* The MQTT topic includes the group name so our traffic does not mix with other groups on the same broker.

## Repository layout

```
REST/        server.py, client.py, dashboard.py
MQTT/        pub.py, sub.py, .env.example
common/      config, CSV logger, simulated sensor, run scheduler, MQTT client factory
tools/       clock_check.py, cpu_monitor.py, link_watch.py, overhead_calc.py,
             set_collector.py (collector IP / ngrok URL), log_bundle.py (pack and merge logs)
broker/      mosquitto.conf (local broker for Block E)
analysis/    analyze.py (tables and charts from raw logs)
laptops/     common.env + one folder per laptop (laptop.env, ROLE.md)
logs/ results/ figures/ wireshark/
play.py      playground launcher
```
