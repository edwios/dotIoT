#!/bin/bash
PORT="/dev/tty.SLAB_USBtoUART"
python3 pgm.py
esptool.py --chip esp32 --baud 1500000 --port ${PORT} erase_flash

