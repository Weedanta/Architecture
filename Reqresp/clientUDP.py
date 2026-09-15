#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct  3 12:51:57 2024

@author: widhi
"""

import socket

# Set up the client socket
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Server address
server_address = ('localhost', 12346)

# Send data to server
message = "halo john"
client_socket.sendto(message.encode('utf-8'), server_address)

# Receive response from server
#data, server = client_socket.recvfrom(1024)
#print(f"Received from server: {data.decode('utf-8')}")

# Close the socket
client_socket.close()
