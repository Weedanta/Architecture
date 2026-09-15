#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Sep  8 14:47:19 2024

@author: widhi
"""

import sys
import HelloApp__POA
import omniORB
from omniORB import CORBA
import CosNaming

# Implementasi dari interface Hello
class HelloServant(HelloApp__POA.Hello):
    def sayHello(self):
        return "Hello from CORBA Server!"

# Inisialisasi ORB
orb = CORBA.ORB_init(sys.argv, CORBA.ORB_ID)

# Dapatkan referensi dari root POA
poa = orb.resolve_initial_references("RootPOA")
poaManager = poa._get_the_POAManager()

# Buat servant dan register ke ORB
hello_servant = HelloServant()
hello_ref = hello_servant._this()

# Dapatkan referensi ke Naming Service
obj = orb.resolve_initial_references("NameService")
namingContext = CosNaming.NamingContextExtHelper.narrow(obj)

# Bind nama ke referensi object
name = [CosNaming.NameComponent("Hello", "")]
namingContext.rebind(name, hello_ref)

print("Hello Server is ready and waiting...")

# Aktifkan POA Manager dan mulai server
poaManager.activate()
orb.run()
