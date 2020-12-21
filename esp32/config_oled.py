from machine import Pin

UART_TX=15
UART_RX=13

# MQTT broker IP
MQTT_SERVER = '10.0.1.250'
#MQTT_SERVER = '192.168.1.143'

# MQTT client config
MQTT_CLIENT_ID = 'BleuSkyV2OLED'
MQTT_TOPIC = 'sensornet/#'
MQTT_TOPIC_PREFIX = 'sensornet/' + MQTT_CLIENT_ID + '/'

# Board light defs
LED1 = Pin(12)
LED2 = Pin(32)
KEY1 = Pin(26)

N_LED = 2