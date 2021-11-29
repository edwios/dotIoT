#!/bin/bash
MPBIN=esp32spiram-20210902-v1.17.bin
ERASEBAUD=1500000
PGMBAUD=5000000
#PORT=/dev/tty.usbserial-AB0JJJ6L
#PORT=/dev/ttyS0
PORT=/dev/tty.SLAB_USBtoUART
python3 pgm.py
esptool.py --chip esp32 --baud ${ERASEBAUD} --port ${PORT} erase_flash
#esptool.py --chip esp32 --port /dev/ttyS0 --baud ${PGMBAUD} write_flash -z 0x1000 ${MPBIN}
esptool.py --chip esp32 --port ${PORT} write_flash -z 0x1000 ${MPBIN}

