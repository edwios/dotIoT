## PIRTester
#
# A tool to perform automatic / semi-automatic testing on development hardwares using a TTGO TFT display
#
# This one focused on BLE PIR sensor
#

DEBUG = False    # Global debug printing
USEOLED = False
VERSION = 'v2.0'

import time
#from umqtt.simple import MQTTClient
from machine import Pin, UART, PWM, reset, I2C, SPI
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
import st7789
import pytext

sys.path.append('/pyfonts')
#import font6
#import font10
import romand

# Baudrate max 20000000 for ST7789
spi = SPI(1, baudrate=20000000, polarity=1, phase=1, sck=Pin(18), mosi=Pin(19))
# Normal orientation
# display = st7789.ST7789(spi, 135, 240, reset=Pin(23, Pin.OUT), cs=Pin(5, Pin.OUT), dc=Pin(16, Pin.OUT), backlight=Pin(4, Pin.OUT))
# Rotated 90º clockwise
display = st7789.ST7789(spi, 240, 135, reset=Pin(23, Pin.OUT), cs=Pin(5, Pin.OUT), dc=Pin(16, Pin.OUT), backlight=Pin(4, Pin.OUT), xstart=40, ystart=53)

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
    global display

    print('PIRTester %s\n' % VERSION)
    print('Commands: \n    pir(ms), hack(ms), reset(s), kickout(s), poweron, poweroff, powercycle(s)\n')
    initIO()
    display.init()
    display.fill(st7789.YELLOW)
#    display.rect(10, 10, 220, 115, st7789.color565(0,0,255))
    font = romand
    pytext.text(display, font, "PIRTester", 32, 0, st7789.RED)
#    pytext.text(display, font6, VERSION, 64, 0, st7789.BLUE)
    display.on()


if __name__ == "__main__":
    main()

