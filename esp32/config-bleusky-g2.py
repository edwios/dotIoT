from machine import Pin

# MQTT broker IP
#MQTT_SERVER = '10.0.1.250'
MQTT_SERVER = '192.168.1.143'

# MQTT client config
MQTT_CLIENT_ID = 'BleuSkyG2'
MQTT_TOPIC = 'sensornet/#'
MQTT_TOPIC_PREFIX = 'sensornet/' + MQTT_CLIENT_ID + '/'

# Board light defs
LED1 = Pin(9)
LED4 = Pin(10)
LED2 = Pin(11)
LED5 = Pin(12)
LED3 = Pin(13)
LED6 = Pin(14)
KEY1 = Pin(1)

N_LED = 6

MESH_MOD_TX=17
MESH_MOD_RX=18
