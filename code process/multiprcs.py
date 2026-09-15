#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep 19 09:56:46 2024

@author: widhi
"""

from multiprocessing import Process
from time import *
from random import *

def sleeper(name):
    t = gmtime()
    s = randint(1, 50)  # Menghasilkan angka acak antara 1 dan 20 detik
    txt = str(t.tm_min) + ':' + str(t.tm_sec) + ' ' + name + ' is going to sleep for ' + str(s) + ' seconds'
    print(txt)
    sleep(s)
    t = gmtime()  # Mendapatkan waktu setelah bangun
    txt = str(t.tm_min) + ':' + str(t.tm_sec) + ' ' + name + ' has woken up'
    print(txt)

if __name__ == '__main__':
    p = Process(target=sleeper, args=('eve',))  # Proses pertama dengan argumen 'eve'
    q = Process(target=sleeper, args=('bob',))  # Proses kedua dengan argumen 'bob'
    
    p.start()  # Memulai proses 'eve'
    q.start()  # Memulai proses 'bob'
    
    p.join()  # Menunggu proses 'eve' selesai
    q.join()  # Menunggu proses 'bob' selesai
