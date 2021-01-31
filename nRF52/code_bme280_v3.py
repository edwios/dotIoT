# Adafruit Service demo for Adafruit CLUE board.
# Accessible via Adafruit Bluefruit Playground app and Web Bluetooth Dashboard.

import time
import board
import busio
import digitalio
import _bleio

from adafruit_ble import BLERadio
from adafruit_ble.services import Service
from adafruit_ble.uuid import StandardUUID
from adafruit_ble_adafruit.adafruit_service import AdafruitService
from adafruit_ble.attributes import Attribute
from adafruit_ble.advertising.standard import SolicitServicesAdvertisement
from adafruit_ble.characteristics import Characteristic
from adafruit_ble.characteristics.int import Uint16Characteristic, Int16Characteristic, Int32Characteristic
import adafruit_bme280

class EnvironmentalSensingService(Service):
    uuid = StandardUUID(0x181a)
    """Initially 10s."""
    measurement_period = Int32Characteristic(
            uuid=AdafruitService.adafruit_service_uuid(0x0001),
            properties=(Characteristic.READ | Characteristic.WRITE),
            initial_value=10000,
        )
    """Temperature in degrees Celsius (Uint16)."""
    temperature = Int16Characteristic(
        uuid=StandardUUID(0x2a6e),
        properties=(Characteristic.READ | Characteristic.NOTIFY),
        write_perm=Attribute.NO_ACCESS,
    )
    """Relative humidity as a percentage, 0.0% - 100.0% (Uint16)"""
    humidity = Uint16Characteristic(
        uuid=StandardUUID(0x2a6f),
        properties=(Characteristic.READ | Characteristic.NOTIFY),
        write_perm=Attribute.NO_ACCESS,
    )
    """Barometric pressure in hectoPascals (hPa) (Uint16)"""
    pressure = Uint16Characteristic(
        uuid=StandardUUID(0x2a6d),
        properties=(Characteristic.READ | Characteristic.NOTIFY),
        write_perm=Attribute.NO_ACCESS,
    )

led = digitalio.DigitalInOut(board.LED1)
led.direction = digitalio.Direction.OUTPUT
led.value = True # initial OFF

sensor_pwr = digitalio.DigitalInOut(board.P0_31)
sensor_pwr.direction = digitalio.Direction.OUTPUT
sensor_pwr.value = True # Power up the sensor

time.sleep(1)   # Wait for the sensor to power up

i2c = busio.I2C(sda=board.P0_29, scl=board.P0_02)

last_blink = time.monotonic_ns() // 1000000
last_on = last_blink
def led_blink(period=5000, blink_time=50):
    global last_blink, last_on
    if (time.monotonic_ns() // 1000000) - last_blink > period:
        last_blink = time.monotonic_ns() // 1000000
        last_on = last_blink
        led.value = False
    if (time.monotonic_ns() // 1000000) - last_on > blink_time:
        led.value = True
        

serv_env_sense = EnvironmentalSensingService()
serv_env_sense.measurement_period = 10000 # 10s
last_update = 0

ble = BLERadio()
# The Web Bluetooth dashboard identifies known boards by their
# advertised name, not by advertising manufacturer data.
ble.name = "bme280_02"

bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)

# The Bluefruit Playground app looks in the manufacturer data
# in the advertisement. That data uses the USB PID as a unique ID.
# Adafruit CLUE USB PID:
# Arduino: 0x8071,  CircuitPython: 0x8072, app supports either
adv = SolicitServicesAdvertisement()
adv.complete_name = "EnvSensing"
adv.solicited_services.append(serv_env_sense)
#adv.pid = 0x1802

last_t = 0
last_h = 0
last_p = 0

print("Starting up")
print("MAC {:s}".format(str(_bleio.adapter.address)))

while True:
    # Advertise when not connected.
    ble.start_advertising(adv)
    now_msecs = time.monotonic_ns() // 1000000
    while not ble.connected:
        led_blink()
    ble.stop_advertising()

    while ble.connected:
        led_blink(200, 50)
        now_msecs = time.monotonic_ns() // 1000000  # pylint: disable=no-member

        if now_msecs - last_update >= serv_env_sense.measurement_period:
            try:
                t = int((bme280.temperature - 0) * 100) # offset
            except:
                t = last_t
            serv_env_sense.temperature = t
            try:
                t = int((bme280.humidity - 0) * 100)
            except:
                t = last_h
            serv_env_sense.humidity = t
            try:
                t = int(bme280.pressure * 10)
            except:
                t = last_p
            serv_env_sense.pressure = t
            last_update = now_msecs

