import time
from board import *
from busio import I2C
import adafruit_bme680
from digitalio import DigitalInOut, Direction, Pull
import bleio

UUID_ENV_SENSING = 0x181a
UUID_CHAR_TEMPERATURE = 0x2a6e
UUID_CHAR_HUMIDITY = 0x2a6f
UUID_CHAR_PRESSURE = 0x2a6d


# Create library object using our Bus I2C port
i2c = I2C(P0_31, P0_29)
bme680 = adafruit_bme680.Adafruit_BME680_I2C(i2c, debug=False)
# use RTC1 as RTC0 is used by bluetooth stack 
# set up RTC callback every 5 second

# change this to match the location's pressure (hPa) at sea level
bme680.sea_level_pressure = 1026

ledr = None
ledg = None
ledb = None
led = None

periph = None
serv_env_sense = None
chara_t = None
chara_h = None
chara_p = None

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


def send_data():
	global chara_t, chara_h, chara_p
	global periph

	if periph.connected:
		temp = bme680.temperature
		temp =  int(temp * 100)
		chara_t.value = bytearray([temp & 0xFF, temp >> 8])
#		if chara_h.notify:
		humi = bme680.humidity
		humi = int(humi * 100)
		chara_h.value = bytearray([humi & 0xFF, humi >> 8])
#		if chara_p.notify:
		pres = int(bme680.pressure)
		chara_p.value = bytearray([pres & 0xFF, pres >> 8])


def main():
	global ledr, ledg, ledb, led
	global periph
	global serv_env_sense
	global chara_t, chara_p, chara_h

	# start off with LED(1) off
	initLED()

	uuid_env_sense = bleio.UUID(UUID_ENV_SENSING) # Environmental Sensing service
	uuid_char_temp = bleio.UUID(UUID_CHAR_TEMPERATURE) # Temperature characteristic
	uuid_char_humi = bleio.UUID(UUID_CHAR_HUMIDITY) # Temperature characteristic
	uuid_char_pres = bleio.UUID(UUID_CHAR_PRESSURE) # Temperature characteristic

	chara_t = bleio.Characteristic(uuid_char_temp, notify=True, read=True, write=False)
	chara_h = bleio.Characteristic(uuid_char_humi, notify=True, read=True, write=False)
	chara_p = bleio.Characteristic(uuid_char_pres, notify=True, read=True, write=False)
	serv = bleio.Service(uuid_env_sense, [chara_t, chara_h, chara_p])
	periph = bleio.Peripheral([serv], name="BME680")

	periph.start_advertising()

	led_lt = time.monotonic()
	rep_lt = led_lt
	while True:
		if (time.monotonic() - led_lt) > 1:
			led_lt = time.monotonic()
			if theled.value == 1:
				theled.value = 0
			else:
				theled.value = 1

		if periph.connected:
			if (time.monotonic() - rep_lt) > 5:
				rep_lt = time.monotonic()
				ledb.value = 1
				theled = ledg
				print("\nTemperature: %0.1f C" % bme680.temperature)
				print("Gas: %d ohm" % bme680.gas)
				print("Humidity: %0.1f %%" % bme680.humidity)
				print("Pressure: %0.3f hPa" % bme680.pressure)
				print("Altitude = %0.2f meters" % bme680.altitude)
				send_data()
		else:
			ledg.value = 1
			theled = ledb


if __name__ == '__main__':
	main()
