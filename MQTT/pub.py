#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Sep  8 17:49:49 2024

@author: widhi
"""

import paho.mqtt.client as mqtt
import time
import sys

# Inisialisasi broker MQTT - menggunakan broker publik yang lebih reliabel
broker = "broker.hivemq.com"  # Public HiveMQ broker
port = 1883  # Port default untuk MQTT

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
