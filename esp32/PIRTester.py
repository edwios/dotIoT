## PIRTester
#
# A tool to perform automatic / semi-automatic testing on development hardwares using a TTGO TFT display
#
# This one focused on BLE PIR sensor
#


DEBUG = False    # Global debug printing
USEOLED = False
VERSION = 'v1.0'

import time
#from umqtt.simple import MQTTClient
from machine import Pin, UART, PWM, reset, I2C
import network
import select
import esp32
import secrets
import config_PIRTester as config
import ujson
import os
import ubinascii
import sys
import json
import ntptime
#import esp
#esp.osdebug(None)
#import gc
#gc.collect()
from micropython import const

PIROut = None
LED = None
Hack = None
Rst = None
Power = None

def initIO():
    global PIROut, LED, Hack, Rst, Power
    PIROut = config.PIROut
    PIROut.value(0)
    LED = config.LED
    Hack = config.Hack
    Hack.value(1)
    Rst = config.Rst
    Rst.value(1)
    Power = config.Power
    Power.value(1)
    return


def pir(dur=500):
    global PIROut
    print('PIR active')
    PIROut.value(1)
    time.sleep_ms(dur)
    PIROut.value(0)
    return


def hack(dur=10):
    global Hack
    Hack.value(0)
    time.sleep_ms(dur)
    Hack.value(1)
    return


def reset(dur=10):
    global Rst
    Rst.value(0)
    time.sleep_ms(dur)
    Rst.value(1)
    return


def kickout(dur=6):
    global Rst
    print('Waking up MCU')
    hack()
    print('Performing reset')
    Rst.value(0)
    time.sleep(dur)
    Rst.value(1)
    return


def poweron():
    global Power
    print('Powering module on')
    Power.value(0)
    return


def poweroff():
    global Power
    print('Powering module off')
    Power.value(1)
    return


def powercycle(dur=1):
    poweroff()
    time.sleep(dur)
    poweron()
    return


def main():
    print('PIRTester %s\n' % VERSION)
    print('Commands: \n    pir(ms), hack(ms), reset(s), kickout(s), poweron, poweroff, powercycle(s)\n')
    initIO()


if __name__ == "__main__":
    main()

