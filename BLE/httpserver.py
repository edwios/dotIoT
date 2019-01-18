from aiohttp import web
from subprocess import call
import paho.mqtt.client as mqtt
import os.path
import time

HOST_NAME = 'localhost'
PORT_NUMBER = 80
CMDEXE = '/home/edwintam/BLE/lds.py'

_mqtthub = "127.0.0.1"
connected = False

async def HttpHandler(request):
		_lasthttpcmd = request.app['_lasthttpcmd']
		mqttclient = request.app['mqttclient']
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
				mqttclient.publish("sensornet/command", "on")
#				call([CMDEXE, "-d", "1", "on"])
			if (_httpcmd == "off"):
				mqttclient.publish("sensornet/command", "off")
#				call([CMDEXE, "-d", "1", "off"])

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
	global connected
	connected = True
	print("Connected with result code "+str(rc))
	client.subscribe([("sensornet/env/balcony/brightness", 0), ("sensornet/all", 0), ("sensornet/command", 0)])

def on_disconnect(client, userdata, rc):
	global connected
	connected = False
	if rc != 0:
		print("Unexpected disconnection.")

def on_message(client, userdata, msg):
	print(msg.topic+" "+str(msg.payload))

print("Starting mqtt")
client = mqtt.Client()
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message
client.connect_async(_mqtthub, 1883, 60)
client.loop_start() #start loop to process received messages
print("mqtt started")
app = web.Application()
app['_lasthttpcmd'] = ""
app['mqttclient'] = client
app.add_routes([web.get('/cmd/{cmd}', HttpHandler)])
print(time.asctime(), 'Server Starts - %s:%s' % (HOST_NAME, PORT_NUMBER))
web.run_app(app, port=PORT_NUMBER)
