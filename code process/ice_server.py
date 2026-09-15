#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Sep 22 17:42:24 2024

@author: widhi
"""

import sys, Ice
import Demo

class PrinterI(Demo.Printer):
    def __init__(self, t):
        self.t = t

    def printString(self, s, current=None):
        print(self.t, s)

if __name__ == "__main__":
    communicator = Ice.initialize(sys.argv)

    # Create Object Adapter
    adapter = communicator.createObjectAdapterWithEndpoints("SimpleAdapter", "default -p 11000")

    # Create instances of PrinterI
    object1 = PrinterI("Object1 says:")
    object2 = PrinterI("Object2 says:")

    # Add the objects to the adapter with specific identities
    adapter.add(object1, communicator.stringToIdentity("SimplePrinter1"))
    adapter.add(object2, communicator.stringToIdentity("SimplePrinter2"))

    # Activate the adapter
    adapter.activate()

    # Wait for shutdown signal
    communicator.waitForShutdown()
