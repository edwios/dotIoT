from machine import Pin

# MQTT broker IP
MQTT_SERVER = '10.0.1.250'
#MQTT_SERVER = '192.168.1.143'

# MQTT client config
MQTT_CLIENT_ID = 'BleuSky'
MQTT_TOPIC = 'sensornet/#'
MQTT_TOPIC_PREFIX = 'sensornet/'

# Board light defs
LED1 = Pin(12)
LED2 = Pin(32)
KEY1 = Pin(14)
NEO1 = Pin(14)

N_NEO = 118
