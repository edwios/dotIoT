#!/usr/bin/env python3

##
 #  @filename   :   httpserver.py
 #  @brief      :   HTTP server script to relay http commands to MQTT
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

from aiohttp import web
from subprocess import call
import paho.mqtt.client as mqtt
import os.path
import time

HOST_NAME = 'localhost'
PORT_NUMBER = 80
CMDEXE = 'lds.py'

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
			if (_httpcmd == "off"):
				mqttclient.publish("sensornet/command", "off")
		data = {'status': 'OK'}
		return web.json_response(data)

def on_connect(client, userdata, flags, rc):
	connected = True
	print("Connected with result code "+str(rc))
	client.subscribe([("sensornet/env/balcony/brightness", 0), ("sensornet/all", 0), ("sensornet/command", 0)])

def on_disconnect(client, userdata, rc):
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
