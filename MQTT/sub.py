#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Sep  8 17:49:00 2024

@author: widhi
"""

import paho.mqtt.client as mqtt
import os
import sys

# Muat kredensial dari file .env di folder yang sama (tanpa dependency tambahan)
def load_dotenv(path=None):
    path = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

load_dotenv()

# Inisialisasi broker MQTT - HiveMQ Cloud (cluster pribadi, butuh TLS + auth)
broker = "fec429b2a5b94f3096cda8a658769824.s1.eu.hivemq.cloud"
port = 8883  # Port TLS MQTT
topic = "sister/temp"

# Kredensial diambil dari file .env / environment variable (jangan hardcode di source code)
username = os.environ.get("MQTT_USERNAME")
password = os.environ.get("MQTT_PASSWORD")
if not username or not password:
    print("Set MQTT_USERNAME dan MQTT_PASSWORD di file .env atau environment variable.")
    sys.exit(1)

# Callback ketika koneksi berhasil
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"Berhasil terhubung ke broker MQTT {broker}")
        # Berlangganan topik setelah koneksi berhasil
        client.subscribe(topic)
        print(f"Berlangganan topik: {topic}")
    else:
        print(f"Gagal terhubung ke broker, kode error: {rc}")
        sys.exit(1)

# Callback untuk pesan yang diterima
def on_message(client, userdata, message, properties=None):
    print(f"Received message: {message.payload.decode()} (Topic: {message.topic})")

# Inisialisasi klien MQTT dengan API versi terbaru
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(username, password)
client.tls_set()  # TLS dengan sertifikat CA sistem, wajib untuk HiveMQ Cloud
client.on_connect = on_connect
client.on_message = on_message

# Menghubungkan ke broker dengan error handling
try:
    print(f"Menghubungkan ke {broker}...")
    client.connect(broker, port, keepalive=60)
except Exception as e:
    print(f"Gagal menghubungkan ke broker: {e}")
    sys.exit(1)

# Menjaga koneksi tetap terbuka
try:
    print("Menunggu pesan... (Tekan Ctrl+C untuk keluar)")
    client.loop_forever()
except KeyboardInterrupt:
    print("\nSubscriber dihentikan.")
    client.disconnect()