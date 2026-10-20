#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pengaturan koneksi MQTT yang dipakai bersama oleh pub.py dan sub.py.
Semua nilai dibaca dari MQTT/.env (JANGAN di-commit).
"""
import os
import ssl
import sys

import paho.mqtt.client as mqtt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from logutil import load_dotenv  # noqa: E402

# File env bisa diganti lewat argumen --env, misal: --env .env.local
# (untuk broker Mosquitto lokal di Blok E). Default: MQTT/.env
ENV_FILE = ".env"
if "--env" in sys.argv:
    ENV_FILE = sys.argv[sys.argv.index("--env") + 1]
load_dotenv(ENV_FILE if os.path.isabs(ENV_FILE) else os.path.join(HERE, ENV_FILE))

BROKER = os.environ.get("MQTT_BROKER", "")
PORT = int(os.environ.get("MQTT_PORT", "8883"))
USE_TLS = os.environ.get("MQTT_TLS", "1") != "0"
USERNAME = os.environ.get("MQTT_USERNAME")
PASSWORD = os.environ.get("MQTT_PASSWORD")
GROUP = os.environ.get("MQTT_GROUP", "kelompok")

# Topik dipisah per kelompok agar tidak tercampur dengan kelompok lain
TOPIC_DATA = f"sister/{GROUP}/temp"     # + "/<node_id>"
TOPIC_ACK = f"sister/{GROUP}/ack"       # + "/<node_id>"


def make_client(client_id, clean_session=True):
    if not BROKER:
        print("Isi MQTT_BROKER di MQTT/.env (alamat cluster HiveMQ).")
        sys.exit(1)
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id,
                    clean_session=clean_session, protocol=mqtt.MQTTv311)
    if USERNAME:
        c.username_pw_set(USERNAME, PASSWORD)
    if USE_TLS:
        ctx = ssl.create_default_context()
        # Jika SSLKEYLOGFILE diset, kunci TLS disimpan agar Wireshark bisa
        # mendekripsi paket dan melihat header MQTT (Blok C).
        keylog = os.environ.get("SSLKEYLOGFILE")
        if keylog:
            ctx.keylog_filename = keylog
        c.tls_set_context(ctx)
    # Reconnect cepat setelah jaringan pulih (Blok D)
    c.reconnect_delay_set(min_delay=1, max_delay=4)
    return c


def connect(c, keepalive=15):
    print(f"Menghubungkan ke {BROKER}:{PORT} (TLS={'ya' if USE_TLS else 'tidak'})...")
    try:
        c.connect(BROKER, PORT, keepalive=keepalive)
    except Exception as e:
        print(f"Gagal menghubungkan ke broker: {e}")
        sys.exit(1)
