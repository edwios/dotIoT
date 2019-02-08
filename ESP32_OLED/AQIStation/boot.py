#
# AQIStation: boot.py
# Version 1.0
#
# Display eCO2 and eTVoC values from MQTT broker, as well as indoor AQI
#
# Copyright (c) 2019 ioStation Ltd. All rights reserved.
#
# boot.py
#
# Initialise modules and parameters
#
import network
import machine as m
import time
import ssd1306
from umqttsimple import MQTTClient
import ubinascii
import micropython
import network
from writer import Writer
import nunito_r
import ostrich_r
import font6
import esp
esp.osdebug(None)
import gc
gc.collect()

SSID = "<SSID_Name>"
PSWD = "<SSID_PASS>"
MQTT_HOST = "10.0.1.250"

print("Starting")
i2c = m.I2C(scl=m.Pin(4), sda=m.Pin(5))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)
wri_l = Writer(oled, nunito_r)
wri_v = Writer(oled, ostrich_r)
wri_m = Writer(oled, font6)
wri_m_len = wri_m.stringlen("999")
wri_v_len = wri_v.stringlen("9999")

print("Connecting to WiFi")
station = network.WLAN(network.STA_IF)
station.active(True)
station.connect(SSID, PSWD)

client_id = ubinascii.hexlify(m.unique_id())
topic_sub_co2 = b'sensornet/env/home/living/co2'
topic_sub_voc = b'sensornet/env/home/living/voc'
topic_sub_aqi = b'sensornet/env/home/living/aqi'
topic_pub = b'sensornet/status'

last_message = 0
message_interval = 5
counter = 0

print("Waiting to be connected")
while station.isconnected() == False:
  pass

print('Connection successful')
print(station.ifconfig())
