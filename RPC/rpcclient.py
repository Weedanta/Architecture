#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Sep 20 20:45:15 2024

@author: widhi
"""

import requests
import json

# Fungsi untuk memanggil RPC
def call_rpc(method, params):
    url = "http://localhost:4000"
    headers = {'content-type': 'application/json'}
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1,
    }
    response = requests.post(url, data=json.dumps(payload), headers=headers).json()
    return response

# Panggil operasi penjumlahan
result_add = call_rpc("add", [10, "s"])
print(f"Result of add: {result_add['result']}")

# Panggil operasi perkalian
result_multiply = call_rpc("multiply", [10, 5])
print(f"Result of multiply: {result_multiply['result']}")
