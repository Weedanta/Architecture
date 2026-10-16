# Laptop 4 Guide (Rahma)

This folder is already configured for Rahma's laptop. Copy the whole folder to Rahma's laptop (Documents is fine) and keep it separate from the other laptops' folders.

Your role: sender node 4. This laptop sends in Block B condition N = 4. In Block E it is also consumer 3.

## One-time setup (before lab day)

1. Install Python 3.9 or newer from python.org. Tick *Add Python to PATH* during installation.
2. Double-click `0_INSTALL.bat` and wait for it to finish.
3. In the `MQTT` folder, copy `.env.example` to `.env` and fill in `MQTT_USERNAME` and `MQTT_PASSWORD` from the lecturer. Do not share this file with other groups or commit it.
4. Double-click `1_CHECK_READINESS.bat`. All libraries should be OK, the cloud broker reachable, and the clock offset below 50 ms. If the offset is large: *Settings > Time & language > Date & time > Sync now*.

## On lab day

1. Wait for Wedanta's IP in the group chat, then double-click `2_SET_COLLECTOR_IP.bat` and enter it (do it again if the network changes, for example from Wi-Fi to LAN).
2. For each condition: wait until Wedanta is ready, double-click `3_RUN_EXPERIMENT.bat`, pick the same block, protocol and condition, then enter the announced start time (HH:MM:SS).
3. The program stops by itself after the last run. If a consumer process is running, press Ctrl+C once Wedanta says the condition is finished.

You can also type the command yourself in a Command Prompt opened in this folder: `python play.py rahma <block> <protocol> <condition> --start-at HH:MM:SS`.

### Block A: Functional validation (1 laptop)

Functional validation on a single laptop (Wedanta). Everything runs on one machine for 5 minutes.

| Protocol | Condition | Command | What runs |
|---|---|---|---|
| BOTH | single | not taking part | - |

### Block B: Node scalability (2/3/4 laptops, campus Wi-Fi, 1 consumer)

Node scalability on campus Wi-Fi with one consumer. N2 = Wedanta + Johan, N3 = + Nofa, N4 = + Rahma. Each condition is 10 runs x 60 seconds for REST, then the same for MQTT.

| Protocol | Condition | Command | What runs |
|---|---|---|---|
| REST | N2 | not taking part | - |
| REST | N3 | not taking part | - |
| REST | N4 | `python play.py rahma B rest N4` | REST-client |
| MQTT | N2 | not taking part | - |
| MQTT | N3 | not taking part | - |
| MQTT | N4 | `python play.py rahma B mqtt N4` | MQTT-pub |

### Block C: Network quality and overhead (4 laptops)

Network quality and overhead with 4 laptops. Three conditions: lan (everyone on LAN cables), wifi (campus Wi-Fi), limited (throttled Wi-Fi). If REST_PUBLIC_URL (ngrok) is set, REST goes through ngrok.

| Protocol | Condition | Command | What runs |
|---|---|---|---|
| REST | lan | `python play.py rahma C rest lan` | REST-client |
| REST | wifi | `python play.py rahma C rest wifi` | REST-client |
| REST | limited | `python play.py rahma C rest limited` | REST-client |
| MQTT | lan | `python play.py rahma C mqtt lan` | MQTT-pub |
| MQTT | wifi | `python play.py rahma C mqtt wifi` | MQTT-pub |
| MQTT | limited | `python play.py rahma C mqtt limited` | MQTT-pub |

### Block D: Resilience / fault injection (4 laptops)

Resilience. 5 runs x 90 seconds per protocol. In every run, around second 30, Johan switches his Wi-Fi off for 15 seconds and back on (the Python window stays open).

| Protocol | Condition | Command | What runs |
|---|---|---|---|
| REST | fault | `python play.py rahma D rest fault` | REST-client |
| MQTT | fault | `python play.py rahma D mqtt fault` | MQTT-pub |

### Block E: Consumer fan-out (3 fixed senders)

Consumer fan-out. Johan, Nofa and Rahma keep sending. Consumers are added one at a time: C1 = Johan, C2 = + Nofa, C3 = + Rahma. MQTT uses the local Mosquitto broker on Wedanta's laptop.

**Your task:** Besides sending, Rahma's laptop runs consumer 3 in C3.

| Protocol | Condition | Command | What runs |
|---|---|---|---|
| REST | C1 | `python play.py rahma E rest C1` | REST-client |
| REST | C2 | `python play.py rahma E rest C2` | REST-client |
| REST | C3 | `python play.py rahma E rest C3` | dashboard, REST-client |
| MQTT | C1 | `python play.py rahma E mqtt C1` | MQTT-pub |
| MQTT | C2 | `python play.py rahma E mqtt C2` | MQTT-pub |
| MQTT | C3 | `python play.py rahma E mqtt C3` | MQTT-sub, MQTT-pub |

### Block F: MQTT QoS (optional, limited Wi-Fi)

Optional: MQTT QoS 0, 1 and 2 on throttled Wi-Fi.

| Protocol | Condition | Command | What runs |
|---|---|---|---|
| MQTT | qos0 | `python play.py rahma F mqtt qos0` | MQTT-pub |
| MQTT | qos1 | `python play.py rahma F mqtt qos1` | MQTT-pub |
| MQTT | qos2 | `python play.py rahma F mqtt qos2` | MQTT-pub |

## After the lab

1. Double-click `4_PACK_LOGS.bat`. A file named `logs_rahma.zip` appears in this folder.
2. Send that file to Wedanta (WhatsApp, Drive or a flash drive).

Full technical details are in `README.md`.
