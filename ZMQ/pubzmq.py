#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Oct  6 18:09:53 2024

@author: widhi
"""

import zmq
import time

def publisher():
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind("tcp://127.0.0.1:12345")  # Bind to localhost

    time.sleep(2)  # Delay to ensure the subscriber has time to connect
    while True:
        message = f"WAKTU {time.asctime()}"
        socket.send_string(message)
        print(f"Published: {message}")
        time.sleep(1)

publisher()
