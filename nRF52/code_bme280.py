import time
from board import *
from busio import I2C
import adafruit_bme280
from digitalio import DigitalInOut, Direction, Pull
import bleio

UUID_ENV_SENSING = 0x181a
UUID_CHAR_TEMPERATURE = 0x2a6e
UUID_CHAR_HUMIDITY = 0x2a6f
UUID_CHAR_PRESSURE = 0x2a6d
UUID_CHAR_ECO2 = 0xf801
UUID_CHAR_ETVOC = 0xf802
UUID_CHAR_GAS = 0xf803

def initIO():
	BME280_VCC = DigitalInOut(P0_31)
	BME280_VCC.direction = Direction.OUTPUT
	BME280_VCC.value = 1	# Turn on BME280

initIO()	# Turn on the sensor

# Create library object using our Bus I2C port
i2c = I2C(scl=P0_02, sda=P0_29)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)
# use RTC1 as RTC0 is used by bluetooth stack 
# set up RTC callback every 5 second

# change this to match the location's pressure (hPa) at sea level
bme280.sea_level_pressure = 1026

ledr = None
ledg = None
ledb = None
led = None

periph = None
serv_env_sense = None
chara_t = None
chara_h = None
chara_p = None
chara_g = None

_btconnected = False

_tempf = 0.0
_humif = 0.0
_presf = 0.0
_gas = 0
_altf = 0.0
_gas_reference = 250000
_iaq_count = 0

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
	try:
		p.stop_advertising()
		_btconnected = True
	except:
		pass

def onDisconnect(p):
	global _btconnected
	try:
		p.start_advertising()
		_btconnected = False
	except:
		pass

def send_data():
	global chara_t, chara_h, chara_p, chara_g
	global _tempf, _humif, _presf, _gas, _altf
	global _btconnected

	if _btconnected:
		try:
			temp =  int(_tempf * 100)
			chara_t.value = bytearray([temp & 0xFF, temp >> 8])
			humi = int(_humif * 100)
			chara_h.value = bytearray([humi & 0xFF, humi >> 8])
			pres = int(_presf)
			chara_p.value = bytearray([pres & 0xFF, pres >> 8])
		except:
			pass


def main():
	global ledr, ledg, ledb, led
	global periph
	global serv_env_sense
	global chara_t, chara_p, chara_h, chara_g
	global _btconnected
	global _tempf, _humif, _presf, _gas, _altf

	# start off with LED(1) off
	initLED()

	uuid_env_sense = bleio.UUID(UUID_ENV_SENSING) # Environmental Sensing service
	uuid_char_temp = bleio.UUID(UUID_CHAR_TEMPERATURE) # Temperature characteristic
	uuid_char_humi = bleio.UUID(UUID_CHAR_HUMIDITY) # Humidity characteristic
	uuid_char_pres = bleio.UUID(UUID_CHAR_PRESSURE) # Pressure characteristic

	try:
		chara_t = bleio.Characteristic(uuid_char_temp, notify=True, read=True, write=False)
		chara_h = bleio.Characteristic(uuid_char_humi, notify=True, read=True, write=False)
		chara_p = bleio.Characteristic(uuid_char_pres, notify=True, read=True, write=False)
		serv = bleio.Service(uuid_env_sense, [chara_t, chara_h, chara_p])
		periph = bleio.Peripheral([serv], name="BME280")
	except:
		pass

	try:
		periph.start_advertising()
	except:
		pass

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
				try:
					_tempf = float(bme280.temperature)
					_humif = float(bme280.humidity)
					_presf = float(bme280.pressure)
					_altf = float(bme280.altitude)
				except:
					pass
				print("\nTemperature: %0.1f C" % _tempf)
				print("Humidity: %0.1f %%" % _humif)
				print("Pressure: %0.3f hPa" % _presf)
				print("Altitude = %0.2f meters" % _altf)
				send_data()
		else:
			ledg.value = 1
			theled = ledb


if __name__ == '__main__':
	main()
