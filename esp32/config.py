from machine import Pin

# MQTT broker IP
MQTT_SERVER = '10.0.1.250'
#MQTT_SERVER = '192.168.1.143'

# MQTT client config
MQTT_CLIENT_ID = 'BleuSkyV2'
MQTT_TOPIC = 'sensornet/#'
MQTT_TOPIC_PREFIX = 'sensornet/' + MQTT_CLIENT_ID + '/'

# Board light defs
LED4 = Pin(33)
LED1 = Pin(32)
LED5 = Pin(25)
LED2 = Pin(21)
LED6 = Pin(23)
LED3 = Pin(22)
KEY1 = Pin(35)

N_LED = 6

MESH_MOD_TX=18
MESH_MOD_RX=4

UART_DELAY_CRLF = True
UART_DELAY_CRLF_TIME = 0.01
MPU = 1 ## ESP32 WROVER
#MPU = 2 ## ESP32S3