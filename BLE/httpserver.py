from aiohttp import web
from subprocess import call
import time

HOST_NAME = 'localhost'
PORT_NUMBER = 80
CMDEXE = '/home/edwintam/BLE/lds.py'

async def HttpHandler(request):
		_lasthttpcmd = request.app['_lasthttpcmd']
		_httpcmd = None
		cmd = request.match_info.get('cmd', "off")
		if cmd == "on":
			print("Received on from HTTP")
			_httpcmd = "on"
		if cmd == "off":
			print("Received off from HTTP")
			_httpcmd = "off"
		if (_lasthttpcmd != _httpcmd):
			request.app['_lasthttpcmd'] = _httpcmd
			print("Recevied %s from HTTP" % _httpcmd)
			if (_httpcmd == "on"):
				call([CMDEXE, "-d", "1", "on"])
			if (_httpcmd == "off"):
				call([CMDEXE, "-d", "1", "off"])

app = web.Application()
app['_lasthttpcmd'] = ""
app.add_routes([web.get('/cmd/{cmd}', HttpHandler)])
print(time.asctime(), 'Server Starts - %s:%s' % (HOST_NAME, PORT_NUMBER))
web.run_app(app, port=PORT_NUMBER)
