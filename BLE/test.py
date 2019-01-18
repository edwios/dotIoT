import dimond
from bluepy import btle
import time

devaddr = "a4:c1:38:4b:40:26"
_meshname = "3S11ZFCS"
_meshpass = "096355"
_btconnected = False

if (_meshname == ""):
	_meshname = input("Input the mesh name [3S11ZFCS]: ") or "3S11ZFCS"
if (_meshpass == ""):
	_meshpass = input("Input the mesh password [096355]: ") or "096355"

def mycallback(self, mesg):
	print("Device called back: ")
	print(mesg)

if True:
	network = dimond.dimond(0x0211, devaddr, _meshname, _meshpass, callback=mycallback)
	target = 0x06
	command = 0xd0
	data = [1,1,0]
	tries = 0
	while (not _btconnected) and (tries < 5):
		try:
			print("Connecting to %s" % _meshname)
			network.connect()
			_btconnected = True
			print("Connected to mesh")
		except:
			tries += 1
			print("Reconnecting attempt %s" % tries)
			_btconnected = False
			time.sleep(2)
	if _btconnected:
		_psent = True
		print("Sending to addr %s, MAC: %s, Cmd: %s, Data: %s" % (target, devaddr, command, data))
		network.send_packet(target, command, data)
		print("Packet sent")
	else:
		print("Repeated fail to connect")


if False:
	p = btle.Peripheral("E7:7C:12:1F:73:24", btle.ADDR_TYPE_RANDOM)
	p.setMTU(23)
	services=p.getServices()
	for service in services:
	   print(service)
	p.disconnect()

if False:
	p = btle.Peripheral("a4:c1:38:3e:48:0a", btle.ADDR_TYPE_PUBLIC)
	p.setMTU(23)
	services=p.getServices()
	for service in services:
	   print(service)
	p.disconnect()

