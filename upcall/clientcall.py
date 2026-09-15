#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Sep  8 14:16:13 2024

@author: widhi
"""

import socket

def client_program():
    client_socket = socket.socket()  
    client_socket.connect((' 10.200.50.160', 4141))  
    
    message = input("Enter message: ")  
    
    while message.lower().strip() != 'bye':
        client_socket.send(message.encode())  
        data = client_socket.recv(1024).decode()  
    
        print('Received upcall from server:', data)  # Simulating upcall response
        
        message = input("Enter another message: ")  
    
    client_socket.close()

if __name__ == '__main__':
    client_program()
