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
UUID_CHAR_ECO2 = 0xf801
UUID_CHAR_ETVOC = 0xf802
UUID_CHAR_GAS = 0xf803


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
	p.stop_advertising()
	_btconnected = True

def onDisconnect(p):
	global _btconnected
	p.start_advertising()
	_btconnected = False

def getGasRef():
	g = 0

	for i in range(10):
		g += bme680.gas
	return int(g/10)


def calcIAQ(g):
	global _iaq_count
	global _gas_reference

	iaq = 0
	if (_iaq_count > 10) or (_iaq_count == 0):
		_iaq_count = 0
		_gas_reference = getGasRef()
	_iaq_count += 1
	hum_weighting = 0.25 # so hum effect is 25% of the total air quality score
	gas_weighting = 0.75 # so gas effect is 75% of the total air quality score
	hum_score = 0
	gas_score = 0
	hum_reference = 40

	# Calculate humidity contribution to IAQ index
	current_humidity = bme680.humidity
	if (current_humidity >= 38 and current_humidity <= 42):
		hum_score = 0.25*100	# Humidity +/-5% around optimum 
	else:
		# sub-optimal
		if (current_humidity < 38):
			hum_score = 0.25/hum_reference*current_humidity*100
		else:
			hum_score = ((-0.25/(100-hum_reference)*current_humidity)+0.416666)*100

	# Calculate gas contribution to IAQ index
	gas_lower_limit = 5000   # Bad air quality limit
	gas_upper_limit = 50000  # Good air quality limit 
	if (_gas_reference > gas_upper_limit):
		_gas_reference = gas_upper_limit
	if (_gas_reference < gas_lower_limit):
		_gas_reference = gas_lower_limit
	gas_score = (0.75/(gas_upper_limit-gas_lower_limit)*_gas_reference -(gas_lower_limit*(0.75/(gas_upper_limit-gas_lower_limit))))*100

	# Combine results for the final IAQ index value (0-100% where 100% is good quality air)
	air_quality_score = hum_score + gas_score

	# Calculate the relative scale
	score = (100-air_quality_score)*5
	if (score >= 301):
		iaq = 5
	elif (score >= 201 and score <= 300 ):
		iaq = 4
	elif (score >= 176 and score <= 200 ):
		iaq = 3
	elif (score >= 151 and score <= 175 ):
		iaq = 2
	elif (score >=  51 and score <= 150 ):
		iaq = 1
	elif (score >=  00 and score <=  50 ):
		iaq = 0
	print("DEBUG: Air quality score %d and IAQ %d" % (air_quality_score, iaq))
	return iaq

def send_data():
	global chara_t, chara_h, chara_p, chara_g
	global _tempf, _humif, _presf, _gas, _altf
	global _btconnected

	if _btconnected:
		temp =  int(_tempf * 100)
		chara_t.value = bytearray([temp & 0xFF, temp >> 8])
		humi = int(_humif * 100)
		chara_h.value = bytearray([humi & 0xFF, humi >> 8])
		pres = int(_presf)
		chara_p.value = bytearray([pres & 0xFF, pres >> 8])
		gas = round(_gas)
		chara_g.value = bytearray([gas & 0xFF, gas >> 8])


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
	uuid_char_gas = bleio.UUID(UUID_CHAR_GAS) # Gas characteristic

	chara_t = bleio.Characteristic(uuid_char_temp, notify=True, read=True, write=False)
	chara_h = bleio.Characteristic(uuid_char_humi, notify=True, read=True, write=False)
	chara_p = bleio.Characteristic(uuid_char_pres, notify=True, read=True, write=False)
	chara_g = bleio.Characteristic(uuid_char_gas, notify=True, read=True, write=False)
	serv = bleio.Service(uuid_env_sense, [chara_t, chara_h, chara_p, chara_g])
	periph = bleio.Peripheral([serv], name="BME680")

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
				_tempf = float(bme680.temperature)
				_humif = float(bme680.humidity)
				_presf = float(bme680.pressure)
				_gas = calcIAQ(bme680.gas)
				_altf = float(bme680.altitude)
				print("\nTemperature: %0.1f C" % _tempf)
				print("Gas: %d ohm" % _gas)
				print("Humidity: %0.1f %%" % _humif)
				print("Pressure: %0.3f hPa" % _presf)
				print("Altitude = %0.2f meters" % _altf)
				send_data()
		else:
			ledg.value = 1
			theled = ledb


if __name__ == '__main__':
	main()
