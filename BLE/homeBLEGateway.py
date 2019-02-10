#!/usr/bin/env python3

##
 #  @filename   :   leGateway.py
 #  @brief      :   Gateway script to react to BLE sensor info and publish to MQTT
 #  @author     :   Edwin Tam
 #
 #  Copyright (C) 2019 Telldus Technologies AB
 #
 #
 # THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 # IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 # FITNESS OR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 # AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 # LIABILITY WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 # OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 # THE SOFTWARE.
 ##

import socket
import time
import paho.mqtt.client as mqtt
from bluepy import btle
from bluepy.btle import Scanner, DefaultDelegate
import binascii
from struct import unpack
from binascii import unhexlify
import argparse
import os.path
import pickle

connected = False
btconnected=False
m_temp = "0ºC"
m_rh = "0%"
m_aqi = "AQI: 0"
m_dotiotdevice = ""
m_period = 3
m_luxth = 500
#dotIoTDevices = []
m_adddevices = {}
m_client = None
m_basetopic = "sensornet/env/home/"

default_dotIoTDevices = {
    "EnvMultiIR9070":
    {
        "2a77":"0,mobile/lux"
    },
    "EvTH1206":
    {
        "2a6e":"2,living/temperature",
        "2a6f":"2,living/humidity",
        "2a6d":"0,living/pressure",
        "addr":"C2:D6:9B:AB:8C:E6"
    },
    "EnvMultiUV0980":
    {
        "2a6e":"2,balcony/temperature",
        "2a6d":"2,balcony/pressure",
        "2a77":"0,balcony/lux",
        "2a76":"0,balcony/uvi"
    }
}
#default_dotIoTDevices = [{"name":"EvTH2618", "addr":"FF:28:58:4C:90:0A"}]
m_mqtthub="127.0.0.1"


class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if isNewDev:
            newdev = True
        elif isNewData:
            devupdated = True

def updateDotIoTdevices(alldevices):
#    global dotIoTDevices

    scanner = Scanner().withDelegate(ScanDelegate())
    devices = scanner.scan(10.0)
    count = 0
    for dev in devices:
#        print ("Device %s (%s), RSSI=%d dB" % (dev.addr, dev.addrType, dev.rssi))
        for (adtype, desc, value) in dev.getScanData():
#            if (adtype == 9):
#               print ( "[%s]  %s = %s" % (adtype, desc, value))
            if ((adtype == 9) and (alldevices.get(value) != None)):
                madr = dev.addr.upper()
                if alldevices[value].get('addr') == None:
                    alldevices[value]['addr']=madr
                    print("%s added new MAC:%s" % (value, madr))
                else:
                    if alldevices[value]['addr'].upper() != madr:
                        print("%s updated with MAC:%s" % (value, madr))
                        alldevices[value]['addr'] = madr
                count += 1



def main():
    global m_period
    global m_luxth
    global m_mqtthub
    global m_alldevices
    global m_client

    parser = argparse.ArgumentParser()
    parser.add_argument("-P", "--period", type=int, help="Period of each poll", default=5)
    parser.add_argument("-l", "--lux", type=int, help="Lux threshold for dark and bright", default=500)
    parser.add_argument("-m", "--mqtthost", help="IP address of MQTT broker", default="127.0.0.1")
    args = parser.parse_args()
    m_period = args.period
    m_luxth = args.lux
    m_mqtthub=args.mqtthost

    # Instead of looking for devices everytime, let's use a cache :)
    if os.path.exists("dbcache_homeBLEGateway.p"):
        m_alldevices = pickle.load(open("dbcache_homeBLEGateway.p", "rb"))
        m_ndev = len(m_alldevices)
        print("Loaded %s devices from cache" % _ndev)
    else:
        dotIoTDevices = default_dotIoTDevices
        print("DEBUG: Not from cache, updating devices")
        updateDotIoTdevices(dotIoTDevices)
        print("DEBUG: %s" % dotIoTDevices)
    h = socket.gethostname()+".local"
    lastTime = 0

    m_client = mqtt.Client()
    m_client.on_connect = on_connect
    m_client.on_publish = on_publish
    m_client.on_disconnect = on_disconnect
    m_client.on_message = on_message
    m_client.connect_async(m_mqtthub, 1883, 60)
    m_client.loop_start() #start loop to process received messages
    
    while (True):
        thisTime = time.monotonic()
        if ((thisTime - lastTime) > m_period) or lastTime == 0:
            lastTime = time.monotonic()
            for i in dotIoTDevices.keys():
                try:
                    getEnvInfoFromBLEDevices(i, dotIoTDevices[i])
                except:
                    pass
            ipaddr = socket.gethostbyname(h)


# The callback for when the client successfully connected to the MQTT broker
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

def getEnvInfoFromBLEDevices(devname, iotdevice):
    global m_temp
    global m_rh
    global m_pr
    global m_lx
    global btconnected

    gotdata = False
    error=False
    devaddr=iotdevice.get('addr')
    m_temp = 0
    m_rh = 0
    m_pr = 0
    m_lx = 0

    if devaddr == None:
        print("DEBUG: Ignoring %s, no MAC address!" % devname)
        return

    print("DEBUG: Connecting to %s" % devaddr)
    try:
        devTH = btle.Peripheral(devaddr,btle.ADDR_TYPE_RANDOM)
    except:
        error=True
        btconnected=False
        print("DEBUG: Cannot connect!")

    if not error:
        btconnected=True
        print("DEBUG: Connected")
        # Set the MTU to bigger value if dealing with large data volume
        # devTH.setMTU(31)
        svcuuid = btle.UUID("181a")
        svc = devTH.getServiceByUUID(svcuuid)
        retry = 0
        for j in iotdevice.keys():
            if j != 'addr':
                print("DEBUG: processing %s from %s" % (j, devname))
                while (not gotdata) and (retry < 4):
                    print("DEBUG: iotdevice[%s]: %s" % (j, iotdevice[j]))
                    cmd = iotdevice[j]
                    a, b = cmd.split(',')
                    dp = int(a)
                    topic = m_basetopic+b
                    print("DEBUG: Obtaining values from %s for %d dp on topic %s" % (j, dp, topic))
                    sen = btle.UUID(str(j))
    # To get value from char with endian, use int.from.bytes():
                    devchar = svc.getCharacteristics(sen)[0]
                    if devchar != None:
                        if j == "815b":
                            # A 2 second delay is essential for EvTH2618 to get the Lux reading
                            # If not, the reading will stuck to one unchanging value
                            time.sleep(2)
                        t = int.from_bytes(devchar.read(), byteorder='little', signed=True)
                        if dp > 0:
                            charvalue = float(t)/(10**dp)
                        else:
                            charvalue = t
                        gotdata = True
                        print("DEBUG: publishing %s with %s" % (topic, charvalue))
                        m_client.publish(topic, charvalue)
                    else:
                        print("ERROR: Cannot oobtain char %s on device %s" % (j, devname))
                gotdata = False
                if retry >= 4:
                    print("ERROR: Cannot get data from device %s" % devname)
#            print("%s,%s,%s,ºC,%s,%%,%s,bar,%s,lux" % (time.strftime('%F %H:%M'),iotdevice["name"],m_temp,m_rh,m_pr,m_lx))
        devTH.disconnect()

def on_publish(client, userdata, result):
    pass

# The callback for when a PUBLISH message is received from the broker.
def on_message(client, userdata, msg):
    global m_aqi

    print(msg.topic+" "+str(msg.payload))
# To get value from message payload on a specific topic:
#    if (msg.topic == "sensornet/env/home/balcony/humidity"):
#        x = str(msg.payload.decode("utf-8"))
#        m_rh = str(round(float(x)))+"%"

if __name__ == '__main__':
    main()
