#!/bin/bash

echo "This script will install the dotIoT BLE Mesh utility."
echo -e "python3 and pip3 are required or installation will fail.\n"
echo "Hit <Enter> to continue installation, or ^C to abort."
read a

sudo apt install -y libglib2.0-dev mosquitto mosquitto-clients python3-dbus bluez
sudo pip3 install -r requirements.txt
