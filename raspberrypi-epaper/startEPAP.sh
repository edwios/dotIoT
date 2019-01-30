#!/bin/bash

cd /home/edwintam/epap
while :
do
#    /usr/bin/python3 -u main_ble.py >> records.log
    /usr/bin/python3 -u startup.py
    sleep 300
done
