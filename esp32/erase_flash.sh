#!/bin/bash
python3 pgm.py
esptool.py --chip esp32 --baud 1500000 --port /dev/ttyS0 erase_flash

