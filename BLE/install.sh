#!/bin/bash

echo "This script will install the dotIoT BLE Mesh utility."
echo -e "python3 and pip3 are required or installation will fail.\n"
echo "Hit <Enter> to continue installation, or ^C to abort."
read a

sudo apt install mosquitto
sudo apt install mosquitto-clients
sudo apt install python3-dbus
sudo apt install bluez
sudo pip3 install -r requirements.txt
