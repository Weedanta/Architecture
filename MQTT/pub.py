#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Sep  8 17:49:49 2024

@author: widhi
"""

import paho.mqtt.client as mqtt
import os
import time
import sys

# Inisialisasi broker MQTT - HiveMQ Cloud (cluster pribadi, butuh TLS + auth)
broker = "fec429b2a5b94f3096cda8a658769824.s1.eu.hivemq.cloud"
port = 8883  # Port TLS MQTT

# Kredensial diambil dari environment variable (jangan hardcode di source code)
username = os.environ.get("MQTT_USERNAME")
password = os.environ.get("MQTT_PASSWORD")
if not username or not password:
    print("Set environment variable MQTT_USERNAME dan MQTT_PASSWORD terlebih dahulu.")
    sys.exit(1)

# Inisialisasi topik dan pesan suhu
topic = "sister/temp"
suhu = 28  # Suhu tetap 26'C

# Callback untuk koneksi
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"Berhasil terhubung ke broker MQTT {broker}")
    else:
        print(f"Gagal terhubung ke broker, kode error: {rc}")
        sys.exit(1)

# Inisialisasi klien MQTT dengan API versi terbaru
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(username, password)
client.tls_set()  # TLS dengan sertifikat CA sistem, wajib untuk HiveMQ Cloud
client.on_connect = on_connect

# Menghubungkan ke broker dengan timeout dan error handling
try:
    print(f"Menghubungkan ke {broker}...")
    client.connect(broker, port, keepalive=60)
except Exception as e:
    print(f"Gagal menghubungkan ke broker: {e}")
    sys.exit(1)

# Loop untuk mengirim pesan setiap detik
try:
    while True:
        # Mempublikasikan suhu ke topik
        message = f"Suhu: {suhu}°C"
        client.publish(topic, message)
        print(f"Published: {message}")
        
        # Tunggu 1 detik sebelum mengirim lagi
        time.sleep(1)

except KeyboardInterrupt:
    print("Publisher dihentikan.")
    client.disconnect()
