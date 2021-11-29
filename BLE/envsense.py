#!/usr/bin/env python3

import sys
import time
from argparse import ArgumentParser
import json
from bluepy import btle  # linux only (no mac)
import paho.mqtt.client as mqtt
import secrets
import deviceconfig

DEBUG = True

MQTT_PUB_TOPIC_STATUS = 'sensornet/env/{:s}/status'
MQTT_USER = secrets.MQTT_USER
MQTT_PASS = secrets.MQTT_PASS

m_devicemapping = deviceconfig.devices

# BLE IoT Sensor Demo
# Author: Gary Stafford
# Reference: https://elinux.org/RPi_Bluetooth_LE
# Requirements: python3 -m pip install --user -r requirements.txt
# To Run: python3 ./rasppi_ble_receiver.py d1:aa:89:0c:ee:82 <- MAC address - change me!


def readenv(mac_address, client, iface):
    global DEBUG
    err = False
    dt = time.strftime('%F %H:%M:%S')
    if DEBUG:
        dt = time.strftime('%F %H:%M:%S')
        print("[%s] Connecting..." % dt)
    try:
        nano_sense = btle.Peripheral(mac_address, addrType=btle.ADDR_TYPE_RANDOM, iface=iface)
    except:
        if DEBUG:
            dt = time.strftime('%F %H:%M:%S')
            print("[%s] Connection failed" % dt)
        err = True
    if err:
        return err
    if DEBUG: print("[%s] Discovering Services..." % dt)
    try:
        _ = nano_sense.services
        environmental_sensing_service = nano_sense.getServiceByUUID("181A")
    except:
        dt = time.strftime('%F %H:%M:%S')
        print("[%s] ERROR: Device %s provides no such service" % (dt, mac_address))
        try:
            nano_sense.disconnect()
        except:
            pass
        err = True
    if err:
        return err
    if DEBUG:
        dt = time.strftime('%F %H:%M:%S')
        print("[%s] Discovering Characteristics..." % dt)
    try:
        ac = environmental_sensing_service.getCharacteristics()
    except:
        dt = time.strftime('%F %H:%M:%S')
        print("[%s] ERROR: Device %s provides no characteristic!" % (dt, mac_address))
        try:
            nano_sense.disconnect()
        except:
            pass
        err = True
    if err:
        return err
    if ac.count == 0:
        dt = time.strftime('%F %H:%M:%S')
        print("[%s] ERROR: Device %s provides no characteristic!" % (dt, mac_address))
        try:
            nano_sense.disconnect()
        except:
            pass
        err = True
    if err:
        return err
    supports_temp = False
    supports_pressure = False
    supports_humidity = False
    supports_lux = False
    for chara in ac:
        x = chara.uuid.getCommonName()
        if x == 'Temperature':
            supports_temp = True
        elif x == 'Pressure':
            supports_pressure = True
        elif x == 'Humidity':
            supports_humidity = True
        elif x == 'Irradiance':
            supports_lux = True
    count = 5
    st = 1
    while (st != 0) and (count > 0) and supports_temp:     
        st, t = read_temperature(environmental_sensing_service)
        time.sleep(2)
        count = count - 1
    count = 5
    sh = 1
    while (sh != 0) and (count > 0) and supports_humidity:     
        sh, h = read_humidity(environmental_sensing_service)
        time.sleep(2)
        count = count - 1
    count = 5
    sp = 1
    while (sp != 0) and (count > 0) and supports_pressure:     
        sp, p = read_pressure(environmental_sensing_service)
        time.sleep(2)
        count = count - 1
    count = 5
    sl = 1
    while (sl != 0) and (count > 0) and supports_lux:
        sl, l = read_lux(environmental_sensing_service)
        time.sleep(2)
        count = count - 1
    if DEBUG:
        dt = time.strftime('%F %H:%M:%S')
        print("[%s] Disconnecting..." % dt)
    try:
        nano_sense.disconnect()
    except:
        pass
    res = {}
    if (st == 0):
        res['temperature'] = t
    else:
        dt = time.strftime('%F %H:%M:%S')
        print("[%s] ERROR: Cannot read temperature from evice %s!" % (dt, mac_address))
    if (sh == 0):
        res['humidity'] = h
    else:
        print("[%s] ERROR: Cannot read humidity from evice %s!" % (dt, mac_address))
    if (sp == 0):
        res['pressure'] = p
    else:
        dt = time.strftime('%F %H:%M:%S')
        print("[%s] ERROR: Cannot read pressure from evice %s!" % (dt, mac_address))
    if (sl == 0):
        res['lux'] = l
    else:
        dt = time.strftime('%F %H:%M:%S')
        print("[%s] ERROR: Cannot read lux from evice %s!" % (dt, mac_address))
    try:
        devicename = m_devicemapping[mac_address]
    except:
        devicename = mac_address
    mesg = {"device_mac": mac_address, "type":"environment", "datetime": dt, "device_name":devicename}
    mesg['readings'] = res
    mesg['state'] = 'ON'
#    mesg['epoch'] = int(time.clock_gettime(0))
    jstr = json.dumps(mesg)
    if DEBUG:
        dt = time.strftime('%F %H:%M:%S')
        print(jstr)
    mtopic = MQTT_PUB_TOPIC_STATUS.format(devicename)
    if client:
        client.publish(mtopic, jstr, retain=True)
    return True


def byte_array_to_int(value):
    # Raw data is hexstring of int values, as a series of bytes, in little endian byte order
    # values are converted from bytes -> bytearray -> int
    # e.g., b'\xb8\x08\x00\x00' -> bytearray(b'\xb8\x08\x00\x00') -> 2232

    # print(f"{sys._getframe().f_code.co_name}: {value}")

    value = bytearray(value)
    value = int.from_bytes(value, byteorder="little", signed=True)
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
    try:
        pressure_char = service.getCharacteristics("2A6D")[0]
    except:
        return (1, 0)
    pressure = pressure_char.read()
    pressure = byte_array_to_int(pressure)
    if pressure > 5000:
        pressure = decimal_exponent_one(pressure)
    if DEBUG: print(f"Barometric Pressure: {round(pressure, 2)} Pa")
    return (0, pressure)


def read_humidity(service):
    try:
        humidity_char = service.getCharacteristics("2A6F")[0]
    except:
        return (1, 0)
    humidity = humidity_char.read()
    humidity = byte_array_to_int(humidity)
    humidity = decimal_exponent_two(humidity)
    if DEBUG: print(f"Humidity: {round(humidity, 2)}%")
    return (0, humidity)


def read_temperature(service):
    try:
        temperature_char = service.getCharacteristics("2A6E")[0]
    except:
        return (1, 0)
    temperature = temperature_char.read()
    temperature = byte_array_to_int(temperature)
    temperature = decimal_exponent_two(temperature)
    if DEBUG: print(f"Temperature: {round(temperature, 2)}°C")
    return (0, temperature)

def read_lux(service):
    try:
        lux_char = service.getCharacteristics("2A77")[0]
    except:
        return (1, 0)
    lux = lux_char.read()
    lux = byte_array_to_int(lux)
    if DEBUG: print(f"Lux: {lux}lm")
    return (0, lux)


def get_args():
    arg_parser = ArgumentParser(description="BLE IoT Sensor Demo")
    arg_parser.add_argument("-t", "--interval", help="Data collection interval", default=900)
    arg_parser.add_argument("-s", "--singleshot", help="Execute only once, for cron jobs. Overrides and invalidate --interval", action='store_true')
    arg_parser.add_argument("-i", "--interface", help="BLE interface", default=0)
    arg_parser.add_argument("-m", "--mac", help="MAC address of device to connect", default=None)
    arg_parser.add_argument("-d", "--debug", help="Debug", action='store_true')
    arg_parser.add_argument("-H", "--mqtt", help="MQTT broker address ", default="10.0.1.250")
    args = arg_parser.parse_args()
    return args


def on_connect(client, userdata, flags, rc):
    global m_connected, DEBUG

    m_connected = True
    if DEBUG: print("%s Debug: MQTT broker connected" % time.strftime('%F %H:%M:%S'))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    #    client.subscribe([("sensornet/env/home/balcony/temperature", 0), ("sensornet/env/home/balcony/humidity", 0), ("sensornet/env/home/living/aqi", 0)])
    # client.subscribe([("sensornet/env/balcony/brightness", 0), ("sensornet/all", 0), ("sensornet/command", 0)])

def on_disconnect(client, userdata, rc):
    global m_connected, DEBUG
    m_connected = False
    if rc != 0:
        print("%s INFO: MQTT broker disconnected, will not try agian" % time.strftime('%F %H:%M:%S'))

def on_publish(client, userdata, result):
    pass

# The callback for when a PUBLISH message is received from the broker.
def on_message(client, userdata, msg):
    pass

def mqttinit(mqtthub, port=1883):
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_publish = on_publish
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    if DEBUG: print("%s DEBUG: Connecting to mqtt host %s" % (time.strftime('%F %H:%M:%S'), mqtthub))
    client.username_pw_set(username=MQTT_USER, password=MQTT_PASS)
    client.connect_async(mqtthub, port, 60)
    client.loop_start() #start loop to process received messages
    return client


m_connected = False
m_auto_reconnect = True

def main():
    global DEBUG
    global m_connected, m_auto_reconnect, m_devicemapping

    # get args
    args = get_args()
    sleeptime = int(args.interval)
    mac_address = args.mac
    DEBUG = args.debug
    mqtt_hub = args.mqtt
    iface = args.interface
    singleshot = args.singleshot

    m_connected = False
    m_auto_reconnect = False
    
    mqttclient = mqttinit(mqtt_hub)
    counter = 5
    pause_time = 0
    last = time.monotonic()
    while (sleeptime > 0) or singleshot:
        if (time.monotonic() - last > pause_time) or singleshot:
            last = time.monotonic()
            if mac_address is None:
                n = 1
                for mac in m_devicemapping:
                    if DEBUG: print("Reading {:d} or {:d} from {:s}".format(n, len(m_devicemapping), mac))
                    err = readenv(mac, mqttclient, iface)
                    n = n + 1
                    if (n <= len(m_devicemapping)) and not err:
                        if DEBUG: print("Waiting 30s for next one")
                        time.sleep(30)
            else:
                readenv(mac_address, mqttclient, iface)
            if counter == 0:
                pause_time = sleeptime
            else:
                pause_time = 30
            if counter > 0:
                counter = counter - 1
        if (not m_connected) and m_auto_reconnect:
            mqttclient = mqttinit(mqtt_hub)
        time.sleep(0.1)
        if singleshot:
            if DEBUG: print("Single shot mode")
            singleshot = False
            sleeptime = 0

if __name__ == "__main__":
    main()
