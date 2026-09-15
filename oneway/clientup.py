#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Sep  8 14:12:07 2024

@author: widhi
"""

import socket

def client_program():
    client_socket = socket.socket()  
    client_socket.connect(('127.0.0.1', 3131))  
    
    message = input("Enter message: ")  
    print(type(message))
    while message.lower().strip() != 'bye':
        client_socket.send(message.encode())
        print(type(message.encode()))# No need to wait for response
        message = input("Enter another message: ")  
    
    client_socket.close()

if __name__ == '__main__':
    client_program()
