import sys
import time
from argparse import ArgumentParser
import json
from bluepy import btle  # linux only (no mac)

DEBUG = False

# BLE IoT Sensor Demo
# Author: Gary Stafford
# Reference: https://elinux.org/RPi_Bluetooth_LE
# Requirements: python3 -m pip install --user -r requirements.txt
# To Run: python3 ./rasppi_ble_receiver.py d1:aa:89:0c:ee:82 <- MAC address - change me!


def readenv(mac_address):
    err = False
    dt = time.strftime('%F %H:%M:%S')

    if DEBUG: print("Connecting...")
    try:
        nano_sense = btle.Peripheral(mac_address, addrType=btle.ADDR_TYPE_RANDOM)
    except:
        if DEBUG: print("Connection failed")
        err = True

    if err:
        return
    if DEBUG: print("Discovering Services...")
    _ = nano_sense.services
    environmental_sensing_service = nano_sense.getServiceByUUID("181A")

    if DEBUG: print("Discovering Characteristics...")
    _ = environmental_sensing_service.getCharacteristics()
    t = read_temperature(environmental_sensing_service)
    h = read_humidity(environmental_sensing_service)
    p = read_pressure(environmental_sensing_service)
    l = read_lux(environmental_sensing_service)

    if DEBUG: print("Disconnecting...")
    nano_sense.disconnect()
    mesg = {"device_mac": mac_address, "type":"environment", "readings":{"temperature": t, "humidity": h, "pressure": p, "lux": l}, "datetime": dt}
    jstr = json.dumps(mesg)
    print(jstr)

def byte_array_to_int(value):
    # Raw data is hexstring of int values, as a series of bytes, in little endian byte order
    # values are converted from bytes -> bytearray -> int
    # e.g., b'\xb8\x08\x00\x00' -> bytearray(b'\xb8\x08\x00\x00') -> 2232

    # print(f"{sys._getframe().f_code.co_name}: {value}")

    value = bytearray(value)
    value = int.from_bytes(value, byteorder="little")
    return value


def split_color_str_to_array(value):
    # e.g., b'2660,2059,1787,4097\x00' -> 2660,2059,1787,4097 ->
    #       [2660, 2059, 1787, 4097] -> 166.0,128.0,111.0,255.0

    # print(f"{sys._getframe().f_code.co_name}: {value}")

    # remove extra bit on end ('\x00')
    value = value[0:-1]

    # split r, g, b, a values into array of 16-bit ints
    values = list(map(int, value.split(",")))

    # convert from 16-bit ints (2^16 or 0-65535) to 8-bit ints (2^8 or 0-255)
    # values[:] = [int(v) % 256 for v in values]

    # actual sensor is reading values are from 0 - 4097
    if DEBUG: print(f"12-bit Color values (r,g,b,a): {values}")

    values[:] = [round(int(v) / (4097 / 255), 0) for v in values]

    return values


def byte_array_to_char(value):
    # e.g., b'2660,2058,1787,4097\x00' -> 2659,2058,1785,4097
    value = value.decode("utf-8")
    return value


def decimal_exponent_two(value):
    # e.g., 2350 -> 23.5
    return value / 100


def decimal_exponent_one(value):
    # e.g., 988343 -> 98834.3
    return value / 10


def pascals_to_kilopascals(value):
    # 1 Kilopascal (kPa) is equal to 1000 pascals (Pa)
    # to convert kPa to pascal, multiply the kPa value by 1000
    # 98834.3 -> 98.8343
    return value / 1000


def celsius_to_fahrenheit(value):
    return (value * 1.8) + 32



def read_pressure(service):
    pressure_char = service.getCharacteristics("2A6D")[0]
    pressure = pressure_char.read()
    pressure = byte_array_to_int(pressure)
    pressure = decimal_exponent_one(pressure)
    if DEBUG: print(f"Barometric Pressure: {round(pressure, 2)} Pa")
    return pressure


def read_humidity(service):
    humidity_char = service.getCharacteristics("2A6F")[0]
    humidity = humidity_char.read()
    humidity = byte_array_to_int(humidity)
    humidity = decimal_exponent_two(humidity)
    if DEBUG: print(f"Humidity: {round(humidity, 2)}%")
    return humidity


def read_temperature(service):
    temperature_char = service.getCharacteristics("2A6E")[0]
    temperature = temperature_char.read()
    temperature = byte_array_to_int(temperature)
    temperature = decimal_exponent_two(temperature)
    if DEBUG: print(f"Temperature: {round(temperature, 2)}°C")
    return temperature

def read_lux(service):
    lux_char = service.getCharacteristics("2A77")[0]
    lux = lux_char.read()
    lux = byte_array_to_int(lux)
    lux = decimal_exponent_two(lux)
    if DEBUG: print(f"Lux: {round(lux, 2)}lm")
    return lux


def get_args():
    arg_parser = ArgumentParser(description="BLE IoT Sensor Demo")
    arg_parser.add_argument("-i", "--interval", help="Data collection interval", default=900)
    arg_parser.add_argument("-m", "--mac_address", help="MAC address of device to connect", default="E7:7C:12:1F:73:24")
    arg_parser.add_argument("-d", "--debug", help="Debug", default=False)
    args = arg_parser.parse_args()
    return args


def main():
    global DEBUG
    # get args
    args = get_args()
    sleeptime = args.interval
    mac_address = args.mac_address
    DEBUG = args.debug
    
    counter = 0
    while True:
        readenv(mac_address)
        if counter > 4:
            s = sleeptime
        else:
            s = 5
        counter = counter + 1
        time.sleep(s)

if __name__ == "__main__":
    main()
