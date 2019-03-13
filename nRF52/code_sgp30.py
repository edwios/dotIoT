import time
from board import *
from busio import I2C
import adafruit_sgp30
from digitalio import DigitalInOut, Direction, Pull
import bleio

UUID_ENV_SENSING = 0x181a
UUID_CHAR_TEMPERATURE = 0x2a6e
UUID_CHAR_HUMIDITY = 0x2a6f
UUID_CHAR_PRESSURE = 0x2a6d
UUID_CHAR_ECO2 = 0xf801
UUID_CHAR_ETVOC = 0xf802



# Create library object using our Bus I2C port
i2c = I2C(P0_31, P0_29, frequency=100000)
sgp30 = adafruit_sgp30.Adafruit_SGP30(i2c)

ledr = None
ledg = None
ledb = None
led = None

_btconnected = False

periph = None
serv_env_sense = None
chara_c = None
chara_v = None
eCO2 = 0
eTVOC = 0

def initLED():
	global ledr, ledg, ledb, led

	led = DigitalInOut(LED1)
	led.direction = Direction.OUTPUT
	led.value = 1

	# Setup BLUE and RED LEDs as PWM output (default frequency is 500 Hz)
	ledg = DigitalInOut(LED2_G)
	ledb = DigitalInOut(LED2_B)
	ledr = DigitalInOut(LED2_R)
	ledr.direction = Direction.OUTPUT
	ledg.direction = Direction.OUTPUT
	ledb.direction = Direction.OUTPUT
	ledr.value = 1
	ledg.value = 1
	ledb.value = 1

def onConnect(p):
	global _btconnected
	p.stop_advertising()
	_btconnected = True

def onDisconnect(p):
	global _btconnected
	p.start_advertising()
	_btconnected = False

def send_data():
	global chara_c, chara_v
	global periph
	global eCO2, eTVOC

	if periph.connected:
		chara_c.value = bytearray([eCO2 & 0xFF, eCO2 >> 8])
		chara_v.value = bytearray([eTVOC & 0xFF, eTVOC >> 8])


def main():
	global ledr, ledg, ledb, led
	global periph
	global serv_env_sense
	global chara_c, chara_v
	global sgp30
	global eCO2, eTVOC
	global _btconnected

	# start off with LED(1) off
	initLED()
	sgp30.iaq_init()
	sgp30.set_iaq_baseline(0x8973, 0x8aae)

	uuid_env_sense = bleio.UUID(UUID_ENV_SENSING) # Environmental Sensing service
	uuid_char_eco2 = bleio.UUID(UUID_CHAR_ECO2) # Temperature characteristic
	uuid_char_etvoc = bleio.UUID(UUID_CHAR_ETVOC) # Temperature characteristic

	chara_c = bleio.Characteristic(uuid_char_eco2, notify=True, read=True, write=False)
	chara_v = bleio.Characteristic(uuid_char_etvoc, notify=True, read=True, write=False)
	serv = bleio.Service(uuid_env_sense, [chara_c, chara_v])
	periph = bleio.Peripheral([serv], name="CO2")

	periph.start_advertising()

	led_lt = time.monotonic()
	rep_lt = led_lt
	lastConn = False
	while True:
		if (time.monotonic() - led_lt) > 3:
			led_lt = time.monotonic()
			if theled.value == 1:
				theled.value = 0
		if (time.monotonic() - led_lt) > 0.01:
				theled.value = 1

		if periph.connected != lastConn:
			lastConn = periph.connected
			if periph.connected:
				onConnect(periph)
			else:
				onDisconnect(periph)

		if _btconnected:
			if (time.monotonic() - rep_lt) > 5:
				rep_lt = time.monotonic()
				ledb.value = 1
				theled = ledg
				eCO2, eTVOC = sgp30.iaq_measure()
				print("eCO2 = %d ppm \t TVOC = %d ppb" % (eCO2, eTVOC))
				send_data()
		else:
			ledg.value = 1
			theled = ledb


if __name__ == '__main__':
	main()
