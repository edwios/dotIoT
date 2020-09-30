#!/usr/bin/env python3

VERSION='1.3'
DEBUG = False

import paho.mqtt.client as mqtt
import time
import argparse
import colorsys

_mqttConnected = False
_client = None
_mqtthub = "10.0.1.250"
_stepR = 16
_stepG = 16
_stepB = 16
_freq = 5

# Callback when connected successfully to the MQTT broker
def on_connect(client, userdata, flags, rc):
    global _mqttConnected, DEBUG

    _mqttConnected = True
    if DEBUG: print("%s Debug: MQTT broker connected" % time.strftime('%F %H:%M:%S'))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    #    client.subscribe([("sensornet/env/home/balcony/temperature", 0), ("sensornet/env/home/balcony/humidity", 0), ("sensornet/env/home/living/aqi", 0)])
    #client.subscribe([("sensornet/env/balcony/brightness", 0), ("sensornet/all", 0), ("sensornet/command", 0)])

def on_disconnect(client, userdata, rc):
    global _mqttConnected, DEBUG
    _mqttConnected = False
    if rc != 0:
        print("%s INFO: MQTT broker disconnected, will not try agian" % time.strftime('%F %H:%M:%S'))

def on_message(client, userdata, msg):
    global DEBUG
    pass

def on_publish(client, userdata, msg):
    pass

def initMQTT():
    global _client
    _client = mqtt.Client()
    _client.on_connect = on_connect
    _client.on_publish = on_publish
    _client.on_disconnect = on_disconnect
    _client.on_message = on_message
    if DEBUG: print("%s DEBUG: Connecting to mqtt host %s" % (time.strftime('%F %H:%M:%S'), _mqtthub))
    _client.connect_async(_mqtthub, 1883, 60)
    _client.loop_start() #start loop to process received messages

def loopRGB(devname):
    global DEBUG
    global _stepR, _stepG, _stepB, _freq
    if _freq > 0:
        rate = 1/_freq
    else:
        rate = 0.2
    cmdStr = '{:s}/{:s}'.format(devname, 'on')
    sendCmd(cmdStr)
    while(True):
        for ang in range(0, 360):
            (R, G, B) = getRGB(ang)
            rgbStr = '{:02x}{:02x}{:02x}'.format(R,G,B)
            cmdStr = '{:s}/rgb:{:s}'.format(devname, rgbStr)
            sendCmd(cmdStr)
            time.sleep(rate)

def getRGB(angle):
    r,g,b = colorsys.hsv_to_rgb(angle/360, 1.0, 1.0)
#    r,g,b = srgb2.from_sRGB([r*255,g*255,b*255])
    gamma = .43
    r,g,b = r**(1/gamma), g**(1/gamma), b**(1/gamma)
    t = r + g + b
    r = r / t
    g = g / t
    b = b / t
    r,g,b = r**gamma, g**gamma, b**gamma
    return (int(r*255), int(g*255), int(b*255))

def sendCmd(cmdStr):
    global DEBUG
    global _client
    if DEBUG: print("%s DEBUG: cmdStr %s " % (time.strftime('%F %H:%M:%S'), cmdStr))
    _client.publish('sensornet/command', cmdStr)


def main():
    global _mqtthub, _client, _freq
    global DEBUG, VERSION
    if DEBUG: print("%s DEBUG: main()" % (time.strftime('%F %H:%M:%S')))
    parser = argparse.ArgumentParser()
    parser.add_argument("-N", "--devicename", help="Name of the LED device", default="")
    parser.add_argument("-m", "--mqtthost", help="MQTT host", default='10.0.1.250')
    parser.add_argument("-v", "--verbose", help="Debugly verbose", action="store_true", default=False)
    parser.add_argument("-f", "--frequency", help="Change frequency (Hz)", default=5)
    args = parser.parse_args()
    DEBUG = args.verbose
    devname = args.devicename
    _mqtthub = args.mqtthost
    _freq = int(args.frequency)
    initMQTT()
    loopRGB(devname)



if __name__ == '__main__':
    main()
