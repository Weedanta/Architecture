#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Oct  6 18:10:24 2024

@author: widhi
"""

import zmq

def subscriber():
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect("tcp://127.0.0.1:12345")  # Connect to the publisher's address
    socket.setsockopt_string(zmq.SUBSCRIBE, "WAKTU")  # Subscribe to the TIME topic

    while True:
        message = socket.recv_string()
        print(f"Received: {message}")

subscriber()
