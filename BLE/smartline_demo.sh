#!/bin/bash

cd /home/edwintam/dotIoT/BLE
/usr/bin/python3 -u leGateway.py >> leGateway_log.txt &
/usr/bin/python3 -u lds.py >> lds_log.txt &

