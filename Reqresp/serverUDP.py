#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct  3 12:51:14 2024

@author: widhi
"""

import socket

# Set up the server socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Bind the socket to an IP and port
server_address = ('localhost', 12346)
server_socket.bind(server_address)

print(f"UDP server up and listening on {server_address}")

while True:
    # Receive data from client
    data, client_address = server_socket.recvfrom(1024)
    print(f"Received message from {client_address}: {data.decode('utf-8')}")
    
    # Send a response back to the client
   # message = f"Hello, {client_address}. You said: {data.decode('utf-8')}"
    #server_socket.sendto(message.encode('utf-8'), client_address)
