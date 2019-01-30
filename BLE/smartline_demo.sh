#!/bin/bash

cd /home/edwintam/dotIoT/BLE
/usr/bin/python3 -u httpserver.py >> httpserver_log.txt &
/usr/bin/python3 -u lds.py -d 6 wait >> lds_log.txt &
/usr/bin/python3 -u leGateway.py -P 600 >> leGateway_log.txt &

