"""MQTT client factory shared by pub.py and sub.py.

--broker cloud : the lecturer's HiveMQ Cloud broker (TLS 8883, needs MQTT/.env)
--broker local : Mosquitto on the collector laptop (1883, no TLS). Used in Block E
                 so broker CPU can be measured, and to inspect plain MQTT headers
                 in Wireshark.
"""
import sys

import paho.mqtt.client as mqtt

from common import config


def add_broker_args(p):
    p.add_argument("--broker", choices=["cloud", "local"], default=config.env("MQTT_BROKER", "cloud"))
    p.add_argument("--host", default=None, help="override broker hostname")
    p.add_argument("--port", type=int, default=None)
    p.add_argument("--qos", type=int, choices=[0, 1, 2], default=int(config.env("MQTT_QOS", 0)))
    p.add_argument("--keepalive", type=int, default=60)
    p.add_argument("--persistent", action="store_true",
                   help="persistent session (clean_session=False, fixed client_id)")


def make_client(args, client_id):
    c = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=client_id,
        clean_session=not args.persistent,
        protocol=mqtt.MQTTv311,
    )
    if args.broker == "cloud":
        user = config.env("MQTT_USERNAME")
        pw = config.env("MQTT_PASSWORD")
        if not user or not pw:
            print("ERROR: MQTT_USERNAME / MQTT_PASSWORD missing. Create MQTT/.env (see MQTT/.env.example).")
            sys.exit(1)
        c.username_pw_set(user, pw)
        c.tls_set()
        host = args.host or config.CLOUD_BROKER_HOST
        port = args.port or config.CLOUD_BROKER_PORT
    else:
        user = config.env("LOCAL_MQTT_USERNAME")
        if user:
            c.username_pw_set(user, config.env("LOCAL_MQTT_PASSWORD", ""))
        host = args.host or config.env("LOCAL_BROKER_IP", config.collector_ip())
        port = args.port or config.LOCAL_BROKER_PORT
    c.reconnect_delay_set(min_delay=1, max_delay=5)
    c.max_queued_messages_set(0)  # unlimited queue while disconnected (QoS > 0)
    return c, host, port
