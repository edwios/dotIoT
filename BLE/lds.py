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
_gotE1callback = False
_expectE1CallBack = False
_callBackCmd = 0
_psent = False
_meshconnected = False
_refreshmesh = False
_mqtthub = "127.0.0.1"
_lastmqttcmd = ""
ON_DATA = [1,0,0]
OFF_DATA = [0,0,0]
MAXMESHCONNFAILS =3		# Max tries before we declare the mesh is not reachable from this device
MESHREFRESHPERIOD =60	# Update mesh info every minute
CALLBACKWAIT = 10

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
	global _gotE1callback, _callBackCmd

	print("%s DEBUG: Callback %s" % (time.strftime('%F %H:%M'), mesg))
	_callBackCmd = mesg[7]
	if _callBackCmd == 0xE1:
		_gotE1callback = True
	pass

def cmd(n, ac, command, data):
	global _network
	global _psent
	global _meshconnected
	global _refreshmesh

	if n<0:
		return	# N<0 is an error carried over from somewhere else
	targetdevice = None
	connectdevice = None
	n = int(n)
	for dev in list(_ldsdevices.values()):
		if dev.deviceID == n:
			targetdevice = dev
		if dev.deviceID == ac:
			connectdevice = dev
	if n > 0:
		if (targetdevice == None) or (connectdevice == None):
#			print("Missing either target: %s or ac: %s" % (n, ac))
			return False
		target = targetdevice.deviceID
	else:
		target = 0
	if not _meshconnected:
		print("%s INFO: Connecting to mesh %s (%s) via device %d" % (time.strftime('%F %H:%M'), _meshname, _meshpass, targetdevice.deviceID))
		if _network == None:
			_network = dimond.dimond(0x0211, connectdevice.addr, _meshname, _meshpass, callback=blecallback)
		tries = 0
		# The BLE connection may not always happen on a Raspberry Pi due to the hardware limitation
		# Therefore, let's give it a few chances
		while (not _meshconnected) and (tries < MAXMESHCONNFAILS):
			try:
				_network.connect()
				_meshconnected = True
				print("%s INFO: Connected to mesh" % time.strftime('%F %H:%M'))
				time.sleep(2)	# We wait a bit until the 1st wave of notifications passed
			except:
				tries += 1
#				print("Reconnecting attempt %d" % tries)
				_meshconnected = False
				time.sleep(2)
		if not _meshconnected:
			print("%s ERROR: Cannot connect to mesh!" % time.strftime('%F %H:%M'))
			_lastmqttcmd = None
			if tries >= MAXMESHCONNFAILS:
				_refreshmesh = True
	if _meshconnected:
		print("%s DEBUG: Sending to addr %s, MAC: %s, Cmd: %s, Data: %s" % (time.strftime('%F %H:%M'), target, connectdevice.addr, command, data))
		_psent = False
		try:
			_network.send_packet(target, command, data)
			_psent = True
		except:
			_psent = False
	return _psent


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
			if (hcmd == "alarm"):
				cmd(did, _acdevice, 0xd0, ON_DATA)
				time.sleep(0.2)
				cmd(did, _acdevice, 0xe2, [0x04, 0xFF, 0x00, 0x00])
			if (hcmd == "disarm"):
				cmd(did, _acdevice, 0xd0, ON_DATA)
				time.sleep(0.2)
				cmd(did, _acdevice, 0xe2, [0x05, 0x26])
			if (hcmd == "disconnect"):
				if _meshconnected:
					_network.disconnect()
					_meshconnected = False
			if (hcmd == "settime"):
				settime(did)

def settime(did):
	# Set current time to device
	dtnow = datetime.now()
	yh = dtnow.year // 256
	yl = dtnow.year % 256
	data = [yh, yl, dtnow.month, dtnow.day, dtnow.hour, dtnow.minute, dtnow.second]
	# Let's do it by setting the time to ALL devices (thus 0xFFFF)
	cmd(0xffff, _acdevice, 0xe4, data)

def checkMeshConnection(acdevice, autoconnect):
	global _expectE1CallBack
	global _callBackCmd
	if (acdevice >= 0) and autoconnect:
		sendok = cmd(acdevice, acdevice, 0xe0, [0xff, 0xff])
		if sendok:
			_expectE1CallBack=True 	# Expect call back, if not, device's ded
		else:
			# Device's ded, let's see what's there again
			_refreshmesh = True

def refreshMesh(autoconnect):
	global _expectE1CallBack
	print("DEBUG: Refreshing mesh data")
	acdevice = foundLDSdevices(autoconnect)
	if (acdevice >= 0) and autoconnect:
		sendok = cmd(acdevice, acdevice, 0xe0, [0xff, 0xff])
		if sendok:
			_expectE1CallBack=True 	# Expect 0xE1 call back, if not, device's ded
		else:
			_refreshmesh = True
	else:
		if autoconnect:
			print("%s ERROR: No auto-connectable device was found" % time.strftime('%F %H:%M'))
			_refreshmesh = True
	return acdevice

def main():
	global _ndev
	global _meshdevid
	global _ldsdevices
	global _meshname
	global _meshpass
	global _acdevice
	global _refreshmesh
	global _gotE1callback
	global _expectE1CallBack

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
		_acdevice = refreshMesh(autoconnect)
	else:
		# Instead of looking for devices everytime, let's use a cache :)
		if os.path.exists("dbcache.p") and (not choosefromlist):
			_ldsdevices = pickle.load(open("dbcache.p", "rb"))
			_ndev = len(_ldsdevices)
			print("%s DEBUG: Loaded %s devices from cache" % (time.strftime('%F %H:%M'), _ndev))
		else:
			# Ahem, first time, let's do it the hard way
			refreshMesh(autoconnect)
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
			lt = time.monotonic()
			cblt = time.monotonic()
			while True:
				time.sleep(0.1)
# We don't do periodic refresh due to blocking mesh refresh
# This should be handled by a separated thread
# So we now only check and refresh upon error
				if (time.monotonic() - lt > MESHREFRESHPERIOD):
					lt = time.monotonic()
					checkMeshConnection(_acdevice, autoconnect)
					cblt = time.monotonic()
				if (time.monotonic() - cblt > CALLBACKWAIT) and _expectE1CallBack:
					cblt = time.monotonic()
					# We expect to have callback
					if not _gotE1callback:
						# Oops, we don't have one
						print("WARN: Didn't receive any E1 callback")
						_refreshmesh = True
					else:
						_gotE1callback = False
					_expectE1CallBack = False

				if _refreshmesh:
					_refreshmesh = False
					_acdevice = refreshMesh(autoconnect)
					cblt = time.monotonic()

				pass

if __name__ == '__main__':
	main()
