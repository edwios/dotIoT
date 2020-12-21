from machine import Pin

# MQTT broker IP
MQTT_SERVER = '10.0.1.250'
#MQTT_SERVER = '192.168.1.143'

# MQTT client config
MQTT_CLIENT_ID = 'BleuSkyV2'
MQTT_TOPIC = 'sensornet/#'
MQTT_TOPIC_PREFIX = 'sensornet/' + MQTT_CLIENT_ID + '/'

# Board light defs
LED1 = Pin(33)
LED2 = Pin(32)
LED3 = Pin(25)
LED4 = Pin(21)
LED5 = Pin(23)
LED6 = Pin(22)
KEY1 = Pin(35)

N_LED = 6
