# dotIoT - raspberrypi-epaper
dotIoT project on Raspberry Pi with the ePaper HAT

This project in dotIoT uses a Raspberry Pi ZeroW and a ePaper HAT from WaveShare for displaying some selected environmental information form various sensors.

There are two versions of this:
1. main.py The data was collected by the Raspberry Pi subscribing to a few MQTT topics over the IP network
2. main_ble.py The data was collected directly from different sensors using Bluetooth LE

Installation
============

Install python modules: pillow, bluepy
Install libjpeg, libtiff

Usage:
python3 main_ble.py

To collect log:
python3 main_ble.py > records.log &

