#!/bin/bash
while true; do
python -u smartline2.py -s house --mqtthost 10.0.1.250 wait
echo "Process dead, relaunching in 5s"
sleep 5
done
