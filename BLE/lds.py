#!/usr/bin/env python3

import dimond
from bluepy import btle
from bluepy.btle import Scanner, DefaultDelegate
from struct import unpack
from binascii import unhexlify
import time

_ldsdevices = {}
_network = None
_ndev = 0
_gotcallback = False
_meshname = input("Input the mesh name [3S11ZFCS]: ") or "3S11ZFCS"
_meshpass = input("Input the mesh password [096355]: ") or "096355"

class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if isNewDev:
        	newdev = True
        	print(".", end="")
#            print("Discovered device", dev.addr)
        elif isNewData:
        	devupdated = True
        	print("U", end="")
#            print("Received new data from", dev.addr)


def foundLDSdevices():
	global _ldsdevices
	global _ndev

	scanner = Scanner().withDelegate(ScanDelegate())
	devices = scanner.scan(10.0)
	count = 0
	for dev in devices:
#	    print ("Device %s (%s), RSSI=%d dB" % (dev.addr, dev.addrType, dev.rssi))
	    for (adtype, desc, value) in dev.getScanData():
#	        print ( "[%s]  %s = %s" % (adtype, desc, value))
	        if ((adtype == 9) and (value == _meshname)):
	        	count += 1
	        	print("\nFound LDS device #:%s MAC:%s\n" % (count, dev.addr))
	        	_ldsdevices[count] = dev
	_ndev = count
	print()

def callback(dev, mesg):
	global _gotcallback
	_gotcallback = True
	print("Device callback")
	_network.disconnect()

def cmd(n, command, data = [1,1,0]):
	global _gotcallback
	global _network

	thisdevice = _ldsdevices[n]
	mdata = thisdevice.getValueText(255)
	sige = mdata.find("0001020304050607")
	sigb = sige -4
	sigs = mdata[sigb:sige]+"0000"
	target = unpack('<i', unhexlify(sigs))[0]
	print("Target: %s, Cmd: %s, Data: %s" % (target, command, data))
	_network = dimond.dimond(0x0211, thisdevice.addr, _meshname, _meshpass, callback=callback)
	_network.connect()
	_network.send_packet(target, command, data)
	retry=0
	while (not _gotcallback) and (retry <= 3):
		retry += 1
		time.sleep(1)
		_network.send_packet(target, command, data)
	_gotcallback = False
#	_network.disconnect()

def main():
	global _ndev

	while _ndev == 0:
		foundLDSdevices()
	#print("%s devices found" % _ndev)
	devn = 0
	while (devn == 0) or (devn > _ndev):
		devn = int(input("Which device? ") or "0")
	cmd(devn, 0xd0)

if __name__ == '__main__':
    main()
