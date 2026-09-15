#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Sep  8 17:05:25 2024

@author: widhi
"""

import requests

# URL endpoint dari server REST
url = 'http://127.0.0.1:5151/add'

# Parameter yang akan dikirim ke server
params = {'a': 10, 'b': 5}

# Mengirimkan permintaan GET ke server REST
response = requests.get(url, params=params)

# Menampilkan respons dari server
if response.status_code == 200:
    data = response.json()
    print(f"Hasil penjumlahan: {data['result']}")
else:
    print(f"Error: {response.status_code}, {response.text}")
