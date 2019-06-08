#!/bin/bash

cd ~/dotIoT/BLE
/usr/bin/python3 -u httpserver.py >> httpserver_log.txt &
# Next line you will need to change the device number [-d] to the one you want to control.
# To lookup the device number, execute `lds.py -c on`
/usr/bin/python3 -u lds.py -a -N 8P9T2NFG -P 302771 wait >> lds_log.txt &
#
# Uncomment the following is a BLE lux sensor is used
# /usr/bin/python3 -u leGateway.py -P 600 >> leGateway_log.txt &

