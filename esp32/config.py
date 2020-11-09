from machine import Pin

# MQTT broker IP
#MQTT_SERVER = '10.0.1.250'
MQTT_SERVER = '192.168.1.143'

# MQTT client config
MQTT_CLIENT_ID = 'BlueSky'
MQTT_TOPIC = 'sensornet/#'
MQTT_TOPIC_PREFIX = 'sensornet/'

# Board light defs
LED1 = Pin(33)
LED2 = Pin(32)