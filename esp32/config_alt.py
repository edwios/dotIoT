from machine import Pin

# MQTT broker IP
MQTT_SERVER = '192.168.1.143'

# MQTT client config
MQTT_CLIENT_ID = 'BleuSkyV2'
MQTT_TOPIC = 'sensornet/#'
MQTT_TOPIC_PREFIX = 'sensornet/' + MQTT_CLIENT_ID + '/'

# Board light defs
LED1 = Pin(33)
LED2 = Pin(32)
KEY1 = Pin(25)
