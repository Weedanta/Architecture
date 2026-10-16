# Role: Nofa (laptop 3)

Role: sender node 3. This laptop starts sending in Block B condition N = 3. In Block E it is also consumer 2.

Run every command from the project root. Add `--start-at HH:MM:SS` (the same time on every laptop) so the runs start together. The step-by-step guide is `GUIDE.md` in the Playground folder.

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
| REST | N3 | `python play.py nofa B rest N3` | REST-client |
| REST | N4 | `python play.py nofa B rest N4` | REST-client |
| MQTT | N2 | not taking part | - |
| MQTT | N3 | `python play.py nofa B mqtt N3` | MQTT-pub |
| MQTT | N4 | `python play.py nofa B mqtt N4` | MQTT-pub |

### Block C: Network quality and overhead (4 laptops)

Network quality and overhead with 4 laptops. Three conditions: lan (everyone on LAN cables), wifi (campus Wi-Fi), limited (throttled Wi-Fi). If REST_PUBLIC_URL (ngrok) is set, REST goes through ngrok.

| Protocol | Condition | Command | What runs |
|---|---|---|---|
| REST | lan | `python play.py nofa C rest lan` | REST-client |
| REST | wifi | `python play.py nofa C rest wifi` | REST-client |
| REST | limited | `python play.py nofa C rest limited` | REST-client |
| MQTT | lan | `python play.py nofa C mqtt lan` | MQTT-pub |
| MQTT | wifi | `python play.py nofa C mqtt wifi` | MQTT-pub |
| MQTT | limited | `python play.py nofa C mqtt limited` | MQTT-pub |

### Block D: Resilience / fault injection (4 laptops)

Resilience. 5 runs x 90 seconds per protocol. In every run, around second 30, Johan switches his Wi-Fi off for 15 seconds and back on (the Python window stays open).

| Protocol | Condition | Command | What runs |
|---|---|---|---|
| REST | fault | `python play.py nofa D rest fault` | REST-client |
| MQTT | fault | `python play.py nofa D mqtt fault` | MQTT-pub |

### Block E: Consumer fan-out (3 fixed senders)

Consumer fan-out. Johan, Nofa and Rahma keep sending. Consumers are added one at a time: C1 = Johan, C2 = + Nofa, C3 = + Rahma. MQTT uses the local Mosquitto broker on Wedanta's laptop.

**Your task:** Besides sending, Nofa's laptop runs consumer 2 in C2 and C3.

| Protocol | Condition | Command | What runs |
|---|---|---|---|
| REST | C1 | `python play.py nofa E rest C1` | REST-client |
| REST | C2 | `python play.py nofa E rest C2` | dashboard, REST-client |
| REST | C3 | `python play.py nofa E rest C3` | dashboard, REST-client |
| MQTT | C1 | `python play.py nofa E mqtt C1` | MQTT-pub |
| MQTT | C2 | `python play.py nofa E mqtt C2` | MQTT-sub, MQTT-pub |
| MQTT | C3 | `python play.py nofa E mqtt C3` | MQTT-sub, MQTT-pub |

### Block F: MQTT QoS (optional, limited Wi-Fi)

Optional: MQTT QoS 0, 1 and 2 on throttled Wi-Fi.

| Protocol | Condition | Command | What runs |
|---|---|---|---|
| MQTT | qos0 | `python play.py nofa F mqtt qos0` | MQTT-pub |
| MQTT | qos1 | `python play.py nofa F mqtt qos1` | MQTT-pub |
| MQTT | qos2 | `python play.py nofa F mqtt qos2` | MQTT-pub |
