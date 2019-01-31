#!/usr/bin/env python3

##
 #  @filename   :   lds.py
 #  @brief      :   Script to interact with Telink BLE Mesh devices via MQTT
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
parser.add_argument("-m", "--dmac", help="MAC address of the device to control")
parser.add_argument("-c", "--choose", help="Choose from a list of devices to control", action="store_true")
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
		elif isNewData:
			devupdated = True


def foundLDSdevices():
	global _ldsdevices
	global _ndev

	scanner = Scanner().withDelegate(ScanDelegate())
	devices = scanner.scan(10.0)
	count = 0
	print("Enter number in [ ] below to choose the device:")
	for dev in devices:
		for (adtype, desc, value) in dev.getScanData():
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

	_ndev = count
	if _ndev > 0:
		try:
			pickle.dump(_ldsdevices, open("dbcache.p", "wb"))
		except:
			print("Error saving presistance dbcache.p")
	print()

def blecallback(mesh, mesg):
	global _gotcallback
	global _network
	global _psent

	_gotcallback = True
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
	if not _btconnected:
		print("Connecting to mesh")
		_network = dimond.dimond(0x0211, thisdevice.addr, _meshname, _meshpass, callback=blecallback)
		tries = 0
		# The BLE connection may not always happen on a Raspberry Pi due to the hardware limitation
		# Therefore, let's give it a few chances
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
		if not _btconnected:
			print("Cannot connect to mesh!")
			_lastmqttcmd = None
	if _btconnected:
		print("Sending to addr %s, MAC: %s, Cmd: %s, Data: %s" % (target, thisdevice.addr, command, data))
		_psent = False
		_network.send_packet(target, command, data)
		_psent = True

# Callback when connected successfully to the MQTT broker
def on_connect(client, userdata, flags, rc):
	global connected
	connected = True

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

# The callback for when a PUBLISH message is received from the broker.
def on_message(client, userdata, msg):
	global _lx
	global _mqttcmd
	global _lastmqttcmd
	global _meshdevid
	global ON_DATA
	global OFF_DATA

	if (msg.topic == "sensornet/command"):
		_mqttcmd = str(msg.payload.decode("utf-8"))
		if (_lastmqttcmd != _mqttcmd):
			_lastmqttcmd = _mqttcmd
			print("Recevied %s from MQTT" % _mqttcmd)
			if (_mqttcmd == "on"):
				cmd(_meshdevid, 0xd0, ON_DATA)
			if (_mqttcmd == "off"):
				cmd(_meshdevid, 0xd0, OFF_DATA)
			if (_mqttcmd == "disconnect"):
				if _btconnected:
					_network.disconnect()
					_btconnected = False

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

	# Instead of looking for devices everytime, let's use a cache :)
	if os.path.exists("dbcache.p") and (not _choosefromlist):
		print("Loading cache")
		_ldsdevices = pickle.load(open("dbcache.p", "rb"))
		_ndev = len(_ldsdevices)
	else:
		# Ahem, first time, let's do it the hard way
		foundLDSdevices()
		devn = 0
		_meshdevid = 0
		while (devn == 0) or (devn > _ndev) or (_meshdevid == 0):
			devn = int(input("Which device? ") or "0")
			for dev in list(_ldsdevices.values()):
				if dev.seq == devn:
					_meshdevid = dev.deviceID
	if (_meshdevid >= 0) and (_ndev > 0):
		if (_meshaction == "on") or (_meshaction == "off"):
			# currently only simple ON/OFF is implemented
			# For other commands, look into the Telink manuals
			cmd(_meshdevid, 0xd0, _data)
		else:
			while True:
				time.sleep(1)
				pass

if __name__ == '__main__':
	main()
