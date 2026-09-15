#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Sep 22 17:44:07 2024

@author: widhi
"""

import sys, Ice
import Demo

if __name__ == "__main__":
    communicator = Ice.initialize(sys.argv)

    # Create proxy for SimplePrinter1 and SimplePrinter2
    base1 = communicator.stringToProxy("SimplePrinter1:default -p 11000")
    base2 = communicator.stringToProxy("SimplePrinter2:default -p 11000")

    # Cast proxies to Demo.PrinterPrx
    printer1 = Demo.PrinterPrx.checkedCast(base1)
    printer2 = Demo.PrinterPrx.checkedCast(base2)

    if (not printer1) or (not printer2):
        raise RuntimeError("Invalid proxy")

    # Call the printString method on both printers
    printer1.printString("Hello World from printer1!")
    printer2.printString("Hello World from printer2!")

    communicator.destroy()
