import esp32
from machine import Pin

led1 = Pin(33, Pin.OUT)
led2 = Pin(32, Pin.OUT)
led1.value(1)
led2.value(1)

r = esp32.RMT(0, pin=l, clock_div=255)
r.loop(True)
r.write_pulses((16384, 1, 16384, 16384, 1), start=0)
r.write_pulses((32767, 1, 32767, 32767, 1), start=0)
r.write_pulses((32767, 1, 32767, 1, 32767, 32767, 1, 32767, 1), start=0)
