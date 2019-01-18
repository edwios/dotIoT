#!/bin/bash

cd /home/edwintam/dotIoT/BLE
/usr/bin/python3 -u httpserver.py >> httpserver_log.txt &
/usr/bin/python3 -u lds.py -d 1 wait >> lds_log.txt &
#/usr/bin/python3 -u leGateway.py >> leGateway.txt &

