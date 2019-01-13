import dimond
from bluepy import btle

_meshname = input("Input the mesh name [3S11ZFCS]: ") or "3S11ZFCS"
_meshpass = input("Input the mesh password [096355]: ") or "096355"

def callback(self, mesg):
	print("Device called back: ")
	print(mesg)

if True:
	network = dimond.dimond(0x0211, "a4:c1:38:3e:48:0a", _meshname, _meshpass, callback=callback)
	network.connect()
	print("Connected")
	target = 0x04
	command = 0xd0
	data = [1,1,0]
	network.send_packet(target, command, data)


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

