#!/bin/bash
cd /home/edwintam/BLE
while :
do
	python3 -u homeBLEGateway.py -m 10.0.1.250 -P 600 >> homeBLEGateway_log.txt
	sleep 300
done

