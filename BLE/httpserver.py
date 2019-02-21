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
MQTT_TOPIC_CMD = "sensornet/command"

_mqtthub = "127.0.0.1"
connected = False

async def HttpHandler(request):
		_lasthttpcmd = request.app['_lasthttpcmd']
		_lastdid = request.app['_lastdid']
		mqttclient = request.app['mqttclient']

		cmd = request.match_info.get('cmd', "off")
		did = request.match_info.get('did', "1")
		did = str(int(did))
		print("Received %s from HTTP for device %s" % (cmd, did))
		if ((_lasthttpcmd != cmd) or (_lastdid != did)):	# skipping repeated commands
			request.app['_lasthttpcmd'] = cmd
			request.app['_lastdid'] = did
			mqtt_msg = did + "/" + cmd
			print("Sending MQTT message %s to %s" % (MQTT_TOPIC_CMD, mqtt_msg))
			mqttclient.publish(MQTT_TOPIC_CMD, mqtt_msg)
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
app['_lastdid'] = ""
app['mqttclient'] = client
app.add_routes([web.get('/cmd/{did}/{cmd}', HttpHandler)])
print(time.asctime(), 'Server Starts - %s:%s' % (HOST_NAME, PORT_NUMBER))
web.run_app(app, port=PORT_NUMBER)
