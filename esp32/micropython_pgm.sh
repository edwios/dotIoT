#!/bin/bash
MPBIN=esp32-idf3-20200902-v1.13.bin
ERASEBAUD=1500000
PGMBAUD=5000000
python3 pgm.py
# esptool.py --chip esp32 --baud ${ERASEBAUD} --port /dev/ttyS0 erase_flash
#esptool.py --chip esp32 --port /dev/ttyS0 --baud ${PGMBAUD} write_flash -z 0x1000 ${MPBIN}
esptool.py --chip esp32 --port /dev/ttyS0 write_flash -z 0x1000 ${MPBIN}

