from machine import Pin

# MQTT broker IP
MQTT_SERVER = '10.0.1.250'
#MQTT_SERVER = '192.168.1.143'

# MQTT client config
MQTT_CLIENT_ID = 'Weather_TV1'
MQTT_TOPIC = 'sensornet/env/+/status'
MQTT_TOPIC_PREFIX = 'sensornet/' + MQTT_CLIENT_ID + '/'

KEY1 = Pin(35)

N_LED = 0

PWR_ON = 2
OLED_PWR = 33
TOUCH=15
TOUCH_PWR=32
BATT_LVL=34

BAUD=27000000
SCK=18
MOSI=23
MISO=32
DC=19
RST=4
CS=5

DISPLAY_WIDTH=128
DISPLAY_HEIGHT=64

STYLE=1
LANG='sv'