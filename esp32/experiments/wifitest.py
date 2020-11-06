from machine import Pin
import time
import network
import secrets

SSID = secrets.SSID
PASS = secrets.PASS


def do_connect(ssid, pwd):
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print('connecting to network...')
        sta_if.active(True)
        time.sleep(2)
        sta_if.connect(ssid, pwd)
        lastTime = time.time()
        while (not sta_if.isconnected()) and ((time.time() - lastTime) < 10):
            pass
        if (time.time() >= lastTime + 10):
            print("Error: timeout connecting to WLAN %s" % ssid)
    print('network config:', sta_if.ifconfig())

do_connect(SSID, PASS)
