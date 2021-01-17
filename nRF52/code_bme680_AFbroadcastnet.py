"""This is a complex sensor node that uses the sensors on a Clue and Feather Bluefruit Sense."""

import time
import board
import busio
import adafruit_bme680
import adafruit_ble_broadcastnet

print("This is BroadcastNet sensor:", adafruit_ble_broadcastnet.device_address)

i2c = busio.I2C(board.P0_31, board.P0_29)

# Define sensors:

# Barometric pressure sensor:
bme680 = adafruit_bme680.Adafruit_BME680_I2C(i2c, address=0x76)

while True:
    measurement = adafruit_ble_broadcastnet.AdafruitSensorMeasurement()
    measurement.temperature = bme680.temperature
    measurement.relative_humidity = bme680.relative_humidity
    measurement.pressure = bme680.pressure
    print(measurement)
    adafruit_ble_broadcastnet.broadcast(measurement)
    time.sleep(60)
