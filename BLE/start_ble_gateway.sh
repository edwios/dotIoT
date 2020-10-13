#!/bin/bash
FLAGG=$1
while true; do
python3 -u smartline.py -R -s house --mqtthost 10.0.1.250 ${FLAGG} wait
if [ $? -eq 0 ]; then
    echo "Process terminated normally"
    exit 0
else
    echo "Process dead, relaunching in 5s"
fi
systemctl restart bluetooth
sleep 1
done
