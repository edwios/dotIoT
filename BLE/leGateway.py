#!/usr/bin/env python3

import socket
import time
import paho.mqtt.client as mqtt
from bluepy import btle
import binascii
from struct import unpack
from binascii import unhexlify
import argparse

connected = False
btconnected=False
m_temp = "0ºC"
m_rh = "0%"
m_aqi = "AQI: 0"

#dotIoTDevices = [{"name":"EnvMultiIR9070", "addr":"FD:CA:60:13:52:9E"}, {"name":"EvTH7271", "addr":"fc:f4:35:bf:6b:37"},{"name":"EvTH9640", "addr":"e3:13:83:3a:33:c8"},{"name":"EnvMultiUV0980", "addr":"e7:7c:12:1f:73:24"}]
dotIoTDevices = [{"name":"EnvMultiIR9070", "addr":"FD:CA:60:13:52:9E"}]
mqtthub="127.0.0.1"

parser = argparse.ArgumentParser()
parser.add_argument("-P", "--period", type=int, help="Period of each poll", default=5)
parser.add_argument("-l", "--lux", type=int, help="Lux threshold for dark and bright", default=500)
parser.add_argument("mqtthost", help="IP address of MQTT host", default="127.0.0.1", nargs="?")
args = parser.parse_args()
m_period = args.period
m_luxth = args.lux
mqtthub=args.mqtthost

def main():
    global m_temp
    global m_rh
    global m_aqi
    global m_pr
    global m_lx
    global m_luxth
    global m_period
    global gotdata
    global connected
    global btconnected
    global client


    h = socket.gethostname()+".local"
    lastTime = time.monotonic()
    while (True):
        thisTime = time.monotonic()
        if (thisTime - lastTime) > m_period:
            lastTime = time.monotonic()
            for i in dotIoTDevices:
                gotdata = False
                try:
                    getEnvInfoFromBLEDevices(i)
                except:
                    pass
                if gotdata:
                    client.publish("sensornet/env/balcony/brightness", m_lx)
                    client.publish("sensornet/env/balcony/temperature", m_temp)
                    client.publish("sensornet/env/balcony/pressure", m_pr)
                    client.publish("sensornet/env/balcony/humidity", m_rh)
                    if (int(m_lx) < m_luxth):
                        client.publish("sensornet/command", "on")
                    else:
                        client.publish("sensornet/command", "off")
            ipaddr = socket.gethostbyname(h)


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    global connected

    connected = True
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
#    client.subscribe([("sensornet/env/home/balcony/temperature", 0), ("sensornet/env/home/balcony/humidity", 0), ("sensornet/env/home/living/aqi", 0)])
    client.subscribe([("sensornet/broadcast", 0), ("sensornet/all", 0), ("sensornet/command", 0)])

def on_disconnect(client, userdata, rc):
    global connected

    connected = False
    if rc != 0:
        print("Unexpected disconnection.")

def reverse(val):
    swb = bytearray(len(val))
    swb[0::2], swb[1::2] = val[1::2], val[0::2]
    return swb

def getEnvInfoFromBLEDevices(iotdevice):
    global m_temp
    global m_rh
    global m_pr
    global m_lx
    global btconnected
    global gotdata

    gotdata = False
    error=False
    devaddr=iotdevice["addr"]
#    print("Connecting to %s" % devaddr)
    try:
        devTH = btle.Peripheral(devaddr,btle.ADDR_TYPE_RANDOM)
    except:
        error=True
        btconnected=False
        print("Cannot connect")

    if not error:
        btconnected=True
#        devTH.setMTU(31)

        retry = 0
        while (not gotdata) and (retry < 4):
            envSensor = btle.UUID("181a")
            envTHSvc = devTH.getServiceByUUID(envSensor) 
            tempUUIDVal = btle.UUID("2a6e")
            rhUUIDVal = btle.UUID("2a6f")
            prUUIDVal = btle.UUID("2a6d")
            lxUUIDVal = btle.UUID("2a77")
            devchar = envTHSvc.getCharacteristics(tempUUIDVal)[0]
            tempVal = int.from_bytes(devchar.read(), byteorder='little', signed=True)
            devchar = envTHSvc.getCharacteristics(rhUUIDVal)[0]
            rhVal = int.from_bytes(devchar.read(), byteorder='little', signed=False)
            devchar = envTHSvc.getCharacteristics(prUUIDVal)[0]
            prVal = int.from_bytes(devchar.read(), byteorder='little', signed=False)
            devchar = envTHSvc.getCharacteristics(lxUUIDVal)[0]
            lxVal = int.from_bytes(devchar.read(), byteorder='little', signed=False)
            if (tempVal != 0) and (prVal != 0):
                gotdata = True
                m_temp = str(round(tempVal/100,1))
                m_rh = str(round(rhVal/100))
                m_pr = str(prVal)
                m_lx = str(lxVal)
            else:
                retry += 1
        devTH.disconnect()
        print("%s,%s,%s,ºC,%s,%%,%s,bar,%s,lux" % (time.strftime('%F %H:%M'),iotdevice["name"],m_temp,m_rh,m_pr,m_lx))

def on_publish(client, userdata, result):
    pass

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global m_aqi

    print(msg.topic+" "+str(msg.payload))
#    if (msg.topic == "sensornet/env/home/balcony/humidity"):
#        x = str(msg.payload.decode("utf-8"))
#        m_rh = str(round(float(x)))+"%"

client = mqtt.Client()
client.on_connect = on_connect
client.on_publish = on_publish
client.on_disconnect = on_disconnect
client.on_message = on_message

client.connect_async(mqtthub, 1883, 60)

# Non-Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
client.loop_start() #start loop to process received messages

if __name__ == '__main__':
    main()
