# Laptop 1 Guide (Wedanta)

This folder is already configured for Wedanta's laptop. Copy the whole folder to Wedanta's laptop (Documents is fine) and keep it separate from the other laptops' folders.

Your role: collector. This laptop receives all the data: REST server, MQTT subscriber, the local Mosquitto broker (Block E), the CPU monitor, Wireshark and ngrok (Block C). At the end, everyone's logs are merged here and analysed.

## One-time setup (before lab day)

1. Install Python 3.9 or newer from python.org. Tick *Add Python to PATH* during installation.
2. Double-click `0_INSTALL.bat` and wait for it to finish.
3. In the `MQTT` folder, copy `.env.example` to `.env` and fill in `MQTT_USERNAME` and `MQTT_PASSWORD` from the lecturer. Do not share this file with other groups or commit it.
4. Right-click `FIREWALL_ALLOW.bat` and choose *Run as administrator*. This opens port 5151 (REST) and 1883 (Mosquitto) so your teammates' laptops can connect.
5. Install Mosquitto (Block E), Wireshark (Block C) and ngrok (Block C, optional).
6. Double-click `1_CHECK_READINESS.bat`. All libraries should be OK, the cloud broker reachable, and the clock offset below 50 ms.

## On lab day

1. Connect to the network you are using and double-click `SHOW_MY_IP.bat`. Post that IP in the group chat.
2. Enter the same IP on your own laptop with `2_SET_COLLECTOR_IP.bat`.
3. For each condition: double-click `3_RUN_EXPERIMENT.bat` and pick the block, protocol and condition. Start before your teammates, then announce a start time (for example one minute from now).
4. When every sender is done, press Ctrl+C and move to the next condition.

You can also type the command yourself in a Command Prompt opened in this folder: `python play.py wedanta <block> <protocol> <condition> --start-at HH:MM:SS`.

### Block A: Functional validation (1 laptop)

Functional validation on a single laptop (Wedanta). Everything runs on one machine for 5 minutes.

**Your task:** Run it on your own. Leave it for 5 minutes until the senders finish, then press Ctrl+C.

| Protocol | Condition | Command | What runs |
|---|---|---|---|
| BOTH | single | `python play.py wedanta A both single` | REST-server, MQTT-sub, REST-client, MQTT-pub |

### Block B: Node scalability (2/3/4 laptops, campus Wi-Fi, 1 consumer)

Node scalability on campus Wi-Fi with one consumer. N2 = Wedanta + Johan, N3 = + Nofa, N4 = + Rahma. Each condition is 10 runs x 60 seconds for REST, then the same for MQTT.

**Your task:** Start the receiver first, post the start time in the group chat, wait until every sender is done, then press Ctrl+C.

| Protocol | Condition | Command | What runs |
|---|---|---|---|
| REST | N2 | `python play.py wedanta B rest N2` | REST-server |
| REST | N3 | `python play.py wedanta B rest N3` | REST-server |
| REST | N4 | `python play.py wedanta B rest N4` | REST-server |
| MQTT | N2 | `python play.py wedanta B mqtt N2` | MQTT-sub |
| MQTT | N3 | `python play.py wedanta B mqtt N3` | MQTT-sub |
| MQTT | N4 | `python play.py wedanta B mqtt N4` | MQTT-sub |

### Block C: Network quality and overhead (4 laptops)

Network quality and overhead with 4 laptops. Three conditions: lan (everyone on LAN cables), wifi (campus Wi-Fi), limited (throttled Wi-Fi). If REST_PUBLIC_URL (ngrok) is set, REST goes through ngrok.

**Your task:** Open Wireshark before the runs and save the captures in the wireshark/ folder. For the internet path, run `ngrok http 5151` and share the URL so everyone can enter it with 2_SET_COLLECTOR_IP.bat.

| Protocol | Condition | Command | What runs |
|---|---|---|---|
| REST | lan | `python play.py wedanta C rest lan` | REST-server |
| REST | wifi | `python play.py wedanta C rest wifi` | REST-server |
| REST | limited | `python play.py wedanta C rest limited` | REST-server |
| MQTT | lan | `python play.py wedanta C mqtt lan` | MQTT-sub |
| MQTT | wifi | `python play.py wedanta C mqtt wifi` | MQTT-sub |
| MQTT | limited | `python play.py wedanta C mqtt limited` | MQTT-sub |

### Block D: Resilience / fault injection (4 laptops)

Resilience. 5 runs x 90 seconds per protocol. In every run, around second 30, Johan switches his Wi-Fi off for 15 seconds and back on (the Python window stays open).

**Your task:** Start the receiver and keep an eye on it. Nothing needs to be switched off on this laptop.

| Protocol | Condition | Command | What runs |
|---|---|---|---|
| REST | fault | `python play.py wedanta D rest fault` | REST-server |
| MQTT | fault | `python play.py wedanta D mqtt fault` | MQTT-sub |

### Block E: Consumer fan-out (3 fixed senders)

Consumer fan-out. Johan, Nofa and Rahma keep sending. Consumers are added one at a time: C1 = Johan, C2 = + Nofa, C3 = + Rahma. MQTT uses the local Mosquitto broker on Wedanta's laptop.

**Your task:** For MQTT, Mosquitto must already be installed (https://mosquitto.org/download/). The playground starts Mosquitto and the CPU monitor for you.

| Protocol | Condition | Command | What runs |
|---|---|---|---|
| REST | C1 | `python play.py wedanta E rest C1` | REST-server, CPU |
| REST | C2 | `python play.py wedanta E rest C2` | REST-server, CPU |
| REST | C3 | `python play.py wedanta E rest C3` | REST-server, CPU |
| MQTT | C1 | `python play.py wedanta E mqtt C1` | mosquitto, CPU |
| MQTT | C2 | `python play.py wedanta E mqtt C2` | mosquitto, CPU |
| MQTT | C3 | `python play.py wedanta E mqtt C3` | mosquitto, CPU |

### Block F: MQTT QoS (optional, limited Wi-Fi)

Optional: MQTT QoS 0, 1 and 2 on throttled Wi-Fi.

| Protocol | Condition | Command | What runs |
|---|---|---|---|
| MQTT | qos0 | `python play.py wedanta F mqtt qos0` | MQTT-sub |
| MQTT | qos1 | `python play.py wedanta F mqtt qos1` | MQTT-sub |
| MQTT | qos2 | `python play.py wedanta F mqtt qos2` | MQTT-sub |

## After the lab

1. Collect `logs_johan.zip`, `logs_nofa.zip` and `logs_rahma.zip` from your teammates and put them in this folder or in `received_logs`.
2. Double-click `4_MERGE_LOGS.bat`, then `5_ANALYZE.bat`. The tables are in `results/summary.md` (ready to copy into the LKM) and the charts in `figures/`.
3. Enter the Wireshark numbers in `results/overhead_wireshark.csv`, then run `5_ANALYZE.bat` again.
4. Fill in the yellow parts of the LKM report with the numbers from `results/summary.md`.

Full technical details are in `README.md`.
