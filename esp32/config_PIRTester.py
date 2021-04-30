from machine import Pin

UART_TX=15
UART_RX=13

# MQTT broker IP
MQTT_SERVER = '10.0.1.250'
#MQTT_SERVER = '192.168.1.143'

# MQTT client config
MQTT_CLIENT_ID = 'TTGOTester'
MQTT_TOPIC = 'sensornet/#'
MQTT_TOPIC_PREFIX = 'sensornet/' + MQTT_CLIENT_ID + '/'

# Board light defs
PIROut = Pin(12, mode=Pin.OUT, pull=None, value=0)
Hack = Pin(13, mode=Pin.OUT, pull=None, value=1)
Rst = Pin(15, mode=Pin.OUT, pull=None, value=1)
LED = Pin(2, mode=Pin.IN, pull=None)

Power = Pin(22, mode=Pin.OPEN_DRAIN, pull=None, value = 1)
N_LED = 0