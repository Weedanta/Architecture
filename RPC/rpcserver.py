#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Sep 20 20:43:48 2024

@author: widhi
"""

from jsonrpc import JSONRPCResponseManager, dispatcher
from http.server import BaseHTTPRequestHandler, HTTPServer
import json

# Mendefinisikan metode penjumlahan
@dispatcher.add_method
def add(a, b):
    return a / b

# Mendefinisikan metode perkalian
@dispatcher.add_method
def multiply(a, b):
    return a * b

# Kelas untuk menangani permintaan HTTP
class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        response = JSONRPCResponseManager.handle(post_data, dispatcher)
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(response.json.encode())

# Jalankan server di port 4000
def run(server_class=HTTPServer, handler_class=RequestHandler, port=4000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting JSON-RPC server on port {port}...')
    httpd.serve_forever()

if __name__ == "__main__":
    run()
