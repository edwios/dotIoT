#!/bin/bash
FLAGG=$1
while true; do
python -u smartline.py -R -s house --mqtthost 10.0.1.250 ${FLAGG} wait
echo "Process dead, relaunching in 5s"
systemctl restart bluetooth
sleep 1
done
