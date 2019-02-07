##
 #  @filename   :   main_ble.py
 #  @brief      :   Display BLE sensor info on epapar display on RPi0w
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

import socket
import time
import paho.mqtt.client as mqtt
#from bluepy import btle
import binascii
import serial
import RPi.GPIO as GPIO
import smbus
import argparse
import subprocess

ser = serial.Serial(            
	port='/dev/serial0',
	baudrate = 9600,
	parity=serial.PARITY_NONE,
	stopbits=serial.STOPBITS_ONE,
	bytesize=serial.EIGHTBITS,
	timeout=1,
	write_timeout= 0.2,
	xonxoff=False,
	rtscts=False
)

MQTT_HOST = "10.0.1.250"

i2c_bus = smbus.SMBus(1)

AO_RST_PIN = 23
CCS811_I2C_ADDR = 0x5a
CCS811_WAKE_PIN = 22
CCS811_RST_PIN = 27
SER_TIMEOUT = 10
m_periood = 30

# CCS811 Registers
CCS811_REG_STATUS = 0x00
CCS811_REG_MEAS_MODE = 0x01
CCS811_REG_ALG_RESULT_DATA = 0x02
CCS811_REG_HW_ID = 0x20
CCS811_REG_APP_START = 0xF4
CCS811_REG_ENV_DATA = 0x05
CCS811_REG_ERROR = 0xE0

CCS811_MEAS_MODE_1 = 0x10

CCS811_OK = False
m_has_envdata_t = False
m_has_envdata_h = False
m_envdata_t = 0
m_envdata_h = 0

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
	global connected

	connected = True
	print("Connected with result code "+str(rc))

	# Subscribing in on_connect() means that if we lose the connection and
	# reconnect then subscriptions will be renewed.
	client.subscribe([("sensornet/env/home/living/temperature", 0), ("sensornet/env/home/living/humidity", 0), ("sensornet/command/ao", 0)])

def on_disconnect(client, userdata, rc):
	global connected

	connected = False
	if rc != 0:
		print("Unexpected disconnection.")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
	global m_has_envdata_t
	global m_has_envdata_h
	global m_envdata_t
	global m_envdata_h

	if (msg.topic == "sensornet/command/ao"):
		x = str(msg.payload.decode("utf-8"))
		if (x == 'reset'):
			resetAO()
	if (msg.topic == "sensornet/env/home/living/humidity"):
		x = float(str(msg.payload.decode("utf-8")))
		m_envdata_h = int(x * 512)
		m_has_envdata_h = True
	if (msg.topic == "sensornet/env/home/living/temperature"):
		x = float(str(msg.payload.decode("utf-8")))
		if x < -25:
			x = -25	# sensor can only handle >= 025ºC
		m_envdata_t = int((x + 25) * 512)
		m_has_envdata_t = True


def reverse(val):
	swb = bytearray(len(val))
	swb[0::2], swb[1::2] = val[1::2], val[0::2]
	return swb

def read1char():
	out=ord(b'\x00')
	lt = time.monotonic()
	while (ser.inWaiting() == 0) and (time.monotonic() - lt < SER_TIMEOUT):
		pass
	if time.monotonic() - lt < SER_TIMEOUT:
		out = ser.read(1)
		out = ord(out)
	return out

def ccs811_update_envdata(t=0, h=0):
	if CCS811_OK:
		# Work if only we have BOTH T and H available
		if (m_has_envdata_t and m_has_envdata_h):
			m_has_envdata_h = False
			m_has_envdata_t = False
			th = m_envdata_t // 256
			tl = m_envdata_t % 256
			hh = m_envdata_h // 256
			hl = m_envdata_h % 256
			print("Env data: th %s, tl %s, hh %s, hl %s" % (th, tl, hh, hl))
			i2c_bus.write_byte_data(CCS811_I2C_ADDR, CCS811_REG_ENV_DATA, [th, tl, hh, hl])
			status = i2c_bus.read_byte_data(CCS811_I2C_ADDR, CCS811_REG_STATUS)
			if status != 0x98:
				err_code = i2c_bus.read_byte_data(CCS811_I2C_ADDR, CCS811_REG_ERROR)
				# Firmware not in app mode, i.e. app_start failed
				print("Failed to update ENV_DATA: %s" % hex(err_code))
				return False
			return True
	return False


def getAOData():
	voconc = -1
	lt = time.monotonic()	
	ch = read1char()
	while (time.monotonic() - lt < SER_TIMEOUT) and (ch != 0xff):
		pass
	if ch == 0xff:
		# We have the start bit
		# Read 7 more bytes
		gas=read1char()
		ppb=read1char()
		dcm=read1char()
		cnh=read1char()
		cnl=read1char()
		mxh=read1char()
		mxl=read1char()
		ckm=read1char()
		if (gas==0x17 and ppb==0x04):
			voconc=cnh*256+cnl
	return voconc

def getVOCData():
	try:
		status = i2c_bus.read_byte_data(CCS811_I2C_ADDR, CCS811_REG_STATUS)
		while status != 0x98:
			err_code = i2c_bus.read_byte_data(CCS811_I2C_ADDR, CCS811_REG_ERROR)
			time.sleep(0.01)
			status = i2c_bus.read_byte_data(CCS811_I2C_ADDR, CCS811_REG_STATUS)
		vocdata = i2c_bus.read_i2c_block_data(CCS811_I2C_ADDR, CCS811_REG_ALG_RESULT_DATA, 8)
		status = vocdata[4]
		if status == 0x98:
			co2h = vocdata[0] & 0x7f
			co2l = vocdata[1]
#			print("Debug: co2h %s, co2l %s" % (hex(co2h), hex(co2l)))
			voch = vocdata[2] & 0x7f
			vocl = vocdata[3]
			err = vocdata[5]
			if status & 0x01 == 1:
				err = i2c_bus.read_byte_data(CCS811_I2C_ADDR, CCS811_REG_ERROR)
				print("getVOCData Error %s" % hex(err))
			co2 = co2h*256+co2l
			voc = voch*256+vocl
			return (status, co2, voc)
		else:
			err_code = i2c_bus.read_byte_data(CCS811_I2C_ADDR, CCS811_REG_ERROR)
			# Firmware not in app mode, i.e. app_start failed
			print("Failed to get data from VOC: %s" % hex(err_code))

	except:
		pass
	return (-1, 0, 0)


def initCCS811():
	GPIO.output(CCS811_WAKE_PIN, 0)
	time.sleep(0.01) # wait 1ms
	hwid = i2c_bus.read_byte_data(CCS811_I2C_ADDR, CCS811_REG_HW_ID)
	if (hwid != 0x81):
		print("Cannot find CCS811, incorrect hwid %s" % hex(hwid))
		return False
	status = i2c_bus.read_byte_data(CCS811_I2C_ADDR, CCS811_REG_STATUS)
	if status & 0x10 == 0:
		print("CCS811 did not have valid app")
		return False
	# Issue APP_START to CCS811
	#i2c_bus.write_byte_data(CCS811_I2C_ADDR, CCS811_REG_APP_START, 0)
	try:
		subprocess.run(["/usr/sbin/i2cset", "-y", "1", str(CCS811_I2C_ADDR), str(CCS811_REG_APP_START)])
	except:
		print("Cannot execute i2cset, make sure i2ctools are installed (apt-get install -y i2c-tools)")
		return False
	time.sleep(0.02)
	# Important: Must set measurement mode otherwise chip won't work, status reg read will fail!!
	i2c_bus.write_byte_data(CCS811_I2C_ADDR, CCS811_REG_MEAS_MODE, CCS811_MEAS_MODE_1)
	status = i2c_bus.read_byte_data(CCS811_I2C_ADDR, CCS811_REG_STATUS)
	if status & 0x90 == 0:
		# Firmware not in app mode, i.e. app_start failed
		err_code = i2c_bus.read_byte_data(CCS811_I2C_ADDR, CCS811_REG_ERROR)
		print("CCS811 did not start up succefully: %s" % hex(err_code))
		return False
	return True

def initAO():
	pass

def resetCCS811():
	GPIO.output(CCS811_RST_PIN, 0)
	time.sleep(0.01) # wait 1ms
	GPIO.output(CCS811_RST_PIN, 1)
	time.sleep(0.1) # wait 20ms

def resetAO():
	GPIO.output(AO_RST_PIN, 0)
	time.sleep(0.2)
	GPIO.output(AO_RST_PIN, 1)

def initGPIO():
	GPIO.setwarnings(False)
	GPIO.setmode(GPIO.BCM)
	GPIO.setup(AO_RST_PIN, GPIO.OUT)
	GPIO.setup(CCS811_RST_PIN, GPIO.OUT)
	GPIO.setup(CCS811_WAKE_PIN, GPIO.OUT)
	GPIO.output(CCS811_WAKE_PIN, 1)
	GPIO.output(CCS811_RST_PIN, 1)

def main():
	aodata = ""

	parser = argparse.ArgumentParser()
	parser.add_argument("-t", "--period", help="Measurement period in seconds. Default 30s", type=int, default=30)
	args = parser.parse_args()
	m_periood = args.period

	client = mqtt.Client()
	client.on_connect = on_connect
	client.on_disconnect = on_disconnect
	client.on_message = on_message
	client.connect_async(MQTT_HOST, 1883, 60)
	initGPIO()
	initAO()
	resetCCS811()
	CCS811_OK = initCCS811()
	# Non-Blocking call that processes network traffic, dispatches callbacks and
	# handles reconnecting.
	# Other loop*() functions are available that give a threaded interface and a
	# manual interface.
	client.loop_start() #start loop to process received messages
	lastTime = time.monotonic()
	while (True):
		if (time.monotonic() - lastTime) > m_periood:
			lastTime = time.monotonic()
			aodata = getAOData()
			ccs811_update_envdata()
			if aodata != -1:
				print("Got AO data from sensor: %s" % aodata)
				# split ao data into array
				client.publish("sensornet/env/home/living/ao", aodata)
			if CCS811_OK:
				(status, co2, voc) = getVOCData()
				if (status != -1):
					print("Got [Status: %s] CO2: %s, TVOC: %s" % (hex(status), co2, voc))
					client.publish("sensornet/env/home/living/co2", co2)
					client.publish("sensornet/env/home/living/voc", voc)




if __name__ == '__main__':
	main()