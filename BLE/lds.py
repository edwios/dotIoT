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
from datetime import datetime
import pickle
import argparse
import paho.mqtt.client as mqtt
import os.path

_ldsdevices = {}
_acdevice = None
_network = None
_ndev = 0
_gotcallback = False
_psent = False
_btconnected = False
_mqtthub = "127.0.0.1"
_lastmqttcmd = ""
ON_DATA = [1,1,0]
OFF_DATA = [0,1,0]


class ScanDelegate(DefaultDelegate):
	def __init__(self):
		DefaultDelegate.__init__(self)

	def handleDiscovery(self, dev, isNewDev, isNewData):
		if isNewDev:
			newdev = True
		elif isNewData:
			devupdated = True


def foundLDSdevices(autoconnect=False):
	global _ldsdevices
	global _ndev

	autoconenctID = -1
	scanner = Scanner().withDelegate(ScanDelegate())
	devices = scanner.scan(10.0)
	count = 0
	maxrssi = -100
	if not autoconnect:
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
				if dev.rssi > maxrssi:
					maxrssi = dev.rssi
					autoconenctID = dev.deviceID
				print("%s DEBUG: [%s] MAC:%s RSSI: %s ID:%s" % (time.strftime('%F %H:%M'), dev.seq, dev.addr, dev.rssi, dev.deviceID))

	_ndev = count
	if _ndev > 0:
		try:
			pickle.dump(_ldsdevices, open("dbcache.p", "wb"))
		except:
			print("%s ERROR: Cannot save presistance dbcache.p" % time.strftime('%F %H:%M'))
		print("%s DEBUG: %s devices found and saved. Will auto connect to device %s" % (time.strftime('%F %H:%M'), _ndev, autoconenctID))
		return autoconenctID


def blecallback(mesh, mesg):
	global _gotcallback

	print("%s DEBUG: Callback %s" % (time.strftime('%F %H:%M'), mesg))
	_gotcallback = True
	pass

def cmd(n, ac, command, data):
	global _network
	global _psent
	global _btconnected

	targetdevice = None
	connectdevice = None
	n = int(n)
	for dev in list(_ldsdevices.values()):
		if dev.deviceID == n:
#			print("Found target device")
			targetdevice = dev
		if dev.deviceID == ac:
#			print("Found autoconenct device")
			connectdevice = dev
	if n > 0:
		if (targetdevice == None) or (connectdevice == None):
#			print("Missing either target: %s or ac: %s" % (n, ac))
			return None
		target = targetdevice.deviceID
	else:
		target = 0
	if not _btconnected:
		print("%s INFO: Connecting to mesh %s (%s) via device %s" % (time.strftime('%F %H:%M'), _meshname, _meshpass, targetdevice.addr))
		if _network == None:
			_network = dimond.dimond(0x0211, connectdevice.addr, _meshname, _meshpass, callback=blecallback)
		tries = 0
		# The BLE connection may not always happen on a Raspberry Pi due to the hardware limitation
		# Therefore, let's give it a few chances
		while (not _btconnected) and (tries < 5):
			try:
				_network.connect()
				_btconnected = True
				print("%s INFO: Connected to mesh" % time.strftime('%F %H:%M'))
			except:
				tries += 1
#				print("Reconnecting attempt %d" % tries)
				_btconnected = False
				time.sleep(2)
		if not _btconnected:
			print("%s ERROR: Cannot connect to mesh!" % time.strftime('%F %H:%M'))
			_lastmqttcmd = None
	if _btconnected:
		print("%s DEBUG: Sending to addr %s, MAC: %s, Cmd: %s, Data: %s" % (time.strftime('%F %H:%M'), target, connectdevice.addr, command, data))
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
		print("%s INFO: MQTT broker disconnected, will not try agian" % time.strftime('%F %H:%M'))

def on_publish(client, userdata, result):
	pass

# The callback for when a PUBLISH message is received from the broker.
def on_message(client, userdata, msg):
	global _lastmqttcmd
	global _acdevice

	if (msg.topic == "sensornet/command"):
		mqttcmd = str(msg.payload.decode("utf-8"))
		if (_lastmqttcmd != mqttcmd):
			_lastmqttcmd = mqttcmd
			did, hcmd = mqttcmd.split('/')
			did = int(did)
			print("%s DEBUG: Recevied %s from MQTT > device: %s, cmd: %s" % (time.strftime('%F %H:%M'), mqttcmd, did, hcmd))
			if (hcmd == "on"):
				cmd(did, _acdevice, 0xd0, ON_DATA)
			if (hcmd == "off"):
				cmd(did, _acdevice, 0xd0, OFF_DATA)
			if (hcmd == "disconnect"):
				if _btconnected:
					_network.disconnect()
					_btconnected = False
			if (hcmd == "settime"):
				settime(did)

def settime(did):
	# Set current time to device
	dtnow = datetime.now()
	yh = dtnow.year // 256
	yl = dtnow.year % 256
	data = [yh, yl, dtnow.month, dtnow.day, dtnow.hour, dtnow.minute, dtnow.second]
	cmd(did, _acdevice, 0xe4, data)


def main():
	global _ndev
	global _meshdevid
	global _ldsdevices
	global _meshname
	global _meshpass
	global _acdevice

	parser = argparse.ArgumentParser()
	parser.add_argument("-n", "--meshname", help="Name of the mesh network", default="3S11ZFCS")
	parser.add_argument("-p", "--meshpass", help="Password of the mesh network", default="096355")
	parser.add_argument("-d", "--did", help="Device to control", type=int, default=1)
	parser.add_argument("-c", "--choose", help="Choose from a list of devices to control", action="store_true")
	parser.add_argument("-a", "--auto", help="Auto connect to mesh upon start", action="store_true", default=False)
	parser.add_argument("action", help="on, off to turn on off device, wait to wait for mqtt input, settime to set the date time to the device")
	args = parser.parse_args()
	meshaction = args.action
	if meshaction == "on":
		data = ON_DATA
	if meshaction == "off":
		data = OFF_DATA
	_meshname = args.meshname
	_meshpass = args.meshpass
	_meshdevid = args.did
	autoconnect = args.auto
	choosefromlist = args.choose

	if (_meshname == ""):
		_meshname = input("Input the mesh name [3S11ZFCS]: ") or "3S11ZFCS"
	if (_meshpass == ""):
		_meshpass = input("Input the mesh password [096355]: ") or "096355"

	if autoconnect:
		_acdevice = foundLDSdevices(autoconnect)
		if _acdevice >= 0:
			cmd(_acdevice, _acdevice, 0xe0, [0xff, 0xff])
		else:
			print("%s ERROR: No auto-connectable device was found" % time.strftime('%F %H:%M'))
	else:
		# Instead of looking for devices everytime, let's use a cache :)
		if os.path.exists("dbcache.p") and (not choosefromlist):
			_ldsdevices = pickle.load(open("dbcache.p", "rb"))
			_ndev = len(_ldsdevices)
			print("%s DEBUG: Loaded %s devices from cache" % (time.strftime('%F %H:%M'), _ndev))
		else:
			# Ahem, first time, let's do it the hard way
			foundLDSdevices(autoconnect)
			devn = 0
			_meshdevid = 0
			while (devn == 0) or (devn > _ndev) or (_meshdevid == 0):
				devn = int(input("Which device? ") or "0")
				for dev in list(_ldsdevices.values()):
					if dev.seq == devn:
						_meshdevid = dev.deviceID
		_acdevice = _meshdevid

	if (choosefromlist):
		print("%s INFO: Will have device in mesh %s from below list to %s" % (time.strftime('%F %H:%M'), _meshname, args.action))
	else:
		print("%s INFO: Will have device #%s in mesh %s to %s" % (time.strftime('%F %H:%M'), _meshdevid, _meshname, args.action))

	client = mqtt.Client()
	client.on_connect = on_connect
	client.on_publish = on_publish
	client.on_disconnect = on_disconnect
	client.on_message = on_message
	client.connect_async(_mqtthub, 1883, 60)
	client.loop_start() #start loop to process received messages

	if (_meshdevid >= 0) and (_ndev > 0):
		if (meshaction == "on") or (meshaction == "off"):
			# currently only simple ON/OFF is implemented
			# For other commands, look into the Telink manuals
			cmd(_meshdevid, _acdevice, 0xd0, data)
		if meshaction == "settime":
			settime(_meshdevid)
		else:
			while True:
				time.sleep(1)
				pass

if __name__ == '__main__':
	main()
