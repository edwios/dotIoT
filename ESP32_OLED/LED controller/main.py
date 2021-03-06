#
# AQIStation: main.py
# Version 1.0
#
# Copyright (c) 2019 ioStation Ltd. All rights reserved.
#
# main.py
#
# Display eCO2 and eTVoC values from MQTT broker, as well as indoor AQI
#
'''
def displayInit():
  oled.fill(0)
  # oled.text(String,X-pixels,y-Pixels)
  wri_m.set_textpos(oled, 10, 100)  # verbose = False to suppress console output
  wri_m.printstring('Ready')
  # Show on display
  oled.show()
'''

def sub_cb(topic, msg):
  print((topic, msg))
  if topic == b'sensornet/light/home/balcony/lantern':
    x=int(msg)
    if x < 0:
      x = 0
    if x > 100:
      x = 100
    bgl = int(x*1023/100)
    eled.duty(bgl)
#    wri_v.set_textpos(oled, 50, 22+wri_v_len-l)  # verbose = False to suppress console output
#    wri_m.printstring(s)

#  oled.show()

def connect_and_subscribe():
#  global client_id, MQTT_HOST, topic_sub
  client = MQTTClient(client_id, MQTT_HOST)
  client.set_callback(sub_cb)
  client.connect()
  client.subscribe(topic_sub_co2)
  client.subscribe(topic_sub_voc)
  client.subscribe(topic_sub_aqi)
  client.subscribe(topic_sub_lgt)
#  print('Connected to %s MQTT broker, subscribed to topics' % MQTT_HOST)
  return client

def restart_and_reconnect():
#  print('Failed to connect to MQTT broker. Reconnecting...')
  time.sleep(10)
  m.reset()

try:
  client = connect_and_subscribe()
except OSError as e:
  restart_and_reconnect()

#displayInit()
msg = b'ESP32_LEDC Ready' 
client.publish(topic_pub, msg)
oled.poweroff()
#oled.text('OK', 110, 56)
#oled.show()
#eled = m.Pin(12, m.Pin.OUT)
#eled.on()

while True:
  try:
    client.check_msg()
#    if (time.time() - last_message) > message_interval:
#      last_message = time.time()
#      counter += 1
  except OSError as e:
    restart_and_reconnect()
    
