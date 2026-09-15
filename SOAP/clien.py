#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Sep  8 16:52:27 2024

@author: widhi
"""
from zeep import Client

# URL WSDL dari server SOAP lokal yang sedang berjalan
wsdl = 'http://127.0.0.1:8000/?wsdl'

# Membuat klien SOAP berdasarkan WSDL
client = Client(wsdl=wsdl)

# Memanggil metode penjumlahan dari layanan SOAP server
result = client.service.add(10, 5)

# Menampilkan hasil penjumlahan
print(f'Hasil penjumlahan dari server SOAP: {result}')

