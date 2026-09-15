#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Sep  8 17:02:45 2024

@author: widhi
"""

from flask import Flask, request, jsonify

# Inisialisasi aplikasi Flask
app = Flask(__name__)

# Endpoint untuk penjumlahan
@app.route('/add', methods=['GET'])
def add_numbers():
    try:
        # Mengambil parameter a dan b dari query string
        a = int(request.args.get('a'))
        b = int(request.args.get('b'))
        result = a + b
        
        # Mengembalikan hasil dalam format JSON
        return jsonify({'result': result})
    except (TypeError, ValueError):
        # Menangani error jika input tidak valid
        return jsonify({'error': 'Invalid input'}), 400
    
@app.route('/mul', methods=['GET'])
def mul_numbers():
    try:
        # Mengambil parameter a dan b dari query string
        a = int(request.args.get('a'))
        b = int(request.args.get('b'))
        result = a * b
        
        # Mengembalikan hasil dalam format JSON
        return jsonify({'result': result})
    except (TypeError, ValueError):
        # Menangani error jika input tidak valid
        return jsonify({'error': 'Invalid input'}), 400

# Jalankan server di port 5000
if __name__ == '__main__':
    app.run(debug=True, port=5151)
