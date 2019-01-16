#!/usr/bin/env python3

import dimond
from bluepy import btle
from bluepy.btle import Scanner, DefaultDelegate
from struct import unpack
from binascii import unhexlify
import time
import pickle
import argparse
import paho.mqtt.client as mqtt
import os.path

_ldsdevices = {}
_network = None
_ndev = 0
_gotcallback = False
_psent = False
_btconnected = False
_mqtthub = "127.0.0.1"
_mqttcmd = ""
_httpcmd = ""
_lastmqttcmd = ""
_lastmqttcmd = ""
_choosefromlist = False
ON_DATA = [1,1,0]
OFF_DATA = [0,1,0]

parser = argparse.ArgumentParser()
parser.add_argument("-n", "--meshname", help="Name of the mesh network", default="3S11ZFCS")
parser.add_argument("-p", "--meshpass", help="Password of the mesh network", default="096355")
parser.add_argument("-d", "--did", help="Device to control", type=int, default=1)
parser.add_argument("-m", "--dmac", help="MAC address of device to control")
parser.add_argument("-c", "--choose", help="Choose from a list of device to control", action="store_true")
parser.add_argument("action", help="Action to turn on off device, or wait for mqtt input")
args = parser.parse_args()
_meshaction = args.action
if _meshaction == "on":
	_data = ON_DATA
if _meshaction == "off":
	_data = OFF_DATA
_meshname = args.meshname
_meshpass = args.meshpass
_meshdevid = args.did
_meshdevmac = args.dmac
_choosefromlist = args.choose

if (_meshname == ""):
	_meshname = input("Input the mesh name [3S11ZFCS]: ") or "3S11ZFCS"
if (_meshpass == ""):
	_meshpass = input("Input the mesh password [096355]: ") or "096355"

if (_choosefromlist):
	print("Will have device in mesh %s from below list %s" % (_meshname, args.action))
else:
	print("Will have device #%s %s in mesh %s" % (_meshdevid, args.action, _meshname))

class ScanDelegate(DefaultDelegate):
	def __init__(self):
		DefaultDelegate.__init__(self)

	def handleDiscovery(self, dev, isNewDev, isNewData):
		if isNewDev:
			newdev = True
#			print(".", end="")
#            print("Discovered device", dev.addr)
		elif isNewData:
			devupdated = True
#			print("U", end="")
#            print("Received new data from", dev.addr)


def foundLDSdevices():
	global _ldsdevices
	global _ndev

	scanner = Scanner().withDelegate(ScanDelegate())
	devices = scanner.scan(10.0)
	count = 0
	print("Enter number in [ ] below to choose the device:")
	for dev in devices:
#	    print ("Device %s (%s), RSSI=%d dB" % (dev.addr, dev.addrType, dev.rssi))
		for (adtype, desc, value) in dev.getScanData():
#	        print ( "[%s]  %s = %s" % (adtype, desc, value))
			if ((adtype == 9) and (value == _meshname)):
				count += 1
				dev.seq = count
				mdata = dev.getValueText(255)
				sige = mdata.find("0001020304050607")
				sigb = sige -4
				sigs = mdata[sigb:sige]+"0000"
				dev.deviceID = unpack('<i', unhexlify(sigs))[0]
				_ldsdevices[count] = dev
				print("[%s] MAC:%s ID:%s" % (dev.seq, dev.addr, dev.deviceID))
#				print("Device ID is %s" % dev.deviceID)

	_ndev = count
	if _ndev > 0:
		try:
			pickle.dump(_ldsdevices, open("dbcache.p", "wb"))
		except:
			print("Error saving presistance dbcache.p")
	print()

def callback(mesh, mesg):
	global _gotcallback
	global _network
	global _psent

	_gotcallback = True
	print("Mesh callback with: %s" % mesg)
	if _psent:
		_psent = False
		try:
			_network.disconnect()
		except:
			print("Disconnected or unable to disconnect")
	print("callback ended")
	pass

def cmd(n, command, data):
	global _gotcallback
	global _network
	global _psent
	global _meshname
	global _meshpass
	global _btconnected

	for dev in list(_ldsdevices.values()):
		if dev.deviceID == n:
			thisdevice = dev
			break
	target = thisdevice.deviceID
	_network = dimond.dimond(0x0211, thisdevice.addr, _meshname, _meshpass, callback=None)
	tries = 0
	_psent = False
# Somehow dimond disconnect after send_packet, so at the moment, has to force reconnection
	_btconnected = False
	while (not _btconnected) and (tries < 5):
		try:
			_network.connect()
			_btconnected = True
			print("Connected to mesh")
		except:
			tries += 1
			print("Reconnecting attempt %s" % tries)
			_btconnected = False
			time.sleep(2)
	if _btconnected:
		_psent = True
		print("Sending to addr %s, MAC: %s, Cmd: %s, Data: %s" % (target, thisdevice.addr, command, data))
		_network.send_packet(target, command, data)

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
	global connected

	connected = True
#    print("Connected with result code "+str(rc))

	# Subscribing in on_connect() means that if we lose the connection and
	# reconnect then subscriptions will be renewed.
#    client.subscribe([("sensornet/env/home/balcony/temperature", 0), ("sensornet/env/home/balcony/humidity", 0), ("sensornet/env/home/living/aqi", 0)])
	client.subscribe([("sensornet/env/balcony/brightness", 0), ("sensornet/all", 0), ("sensornet/command", 0)])

def on_disconnect(client, userdata, rc):
	global connected

	connected = False
	if rc != 0:
		print("Unexpected disconnection.")

def on_publish(client, userdata, result):
	pass

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
	global _lx
	global _mqttcmd
	global _lastmqttcmd
	global _meshdevid
	global ON_DATA
	global OFF_DATA

#    print(msg.topic+" "+str(msg.payload))
	if (msg.topic == "sensornet/command"):
		_mqttcmd = str(msg.payload.decode("utf-8"))
#        print("Recevied: %s", _mqttcmd)
		if (_lastmqttcmd != _mqttcmd):
			_lastmqttcmd = _mqttcmd
			print("Recevied %s from MQTT" % _mqttcmd)
			if (_mqttcmd == "on"):
				cmd(_meshdevid, 0xd0, ON_DATA)
			if (_mqttcmd == "off"):
				cmd(_meshdevid, 0xd0, OFF_DATA)

client = mqtt.Client()
client.on_connect = on_connect
client.on_publish = on_publish
client.on_disconnect = on_disconnect
client.on_message = on_message
client.connect_async(_mqtthub, 1883, 60)
client.loop_start() #start loop to process received messages

def main():
	global _ndev
	global _network
	global _meshdevid
	global _data
	global _ldsdevices
	global _action
	global _mqttcmd
	global _lastmqttcmd
	global _doinit
	global ON_DATA
	global OFF_DATA

	if os.path.exists("dbcache.p") and (not _choosefromlist):
		print("Loading cache")
		_ldsdevices = pickle.load(open("dbcache.p", "rb"))
		_ndev = len(_ldsdevices)
	else:
		foundLDSdevices()
		#print("%s devices found" % _ndev)
		devn = 0
		_meshdevid = 0
		while (devn == 0) or (devn > _ndev) or (_meshdevid == 0):
			devn = int(input("Which device? ") or "0")
			for dev in list(_ldsdevices.values()):
				if dev.seq == devn:
					_meshdevid = dev.deviceID
	if (_meshdevid >= 0) and (_ndev > 0):
		if (_meshaction == "on") or (_meshaction == "off"):
			cmd(_meshdevid, 0xd0, _data)
		else:
			while True:
				time.sleep(1)
				pass

if __name__ == '__main__':
	main()
