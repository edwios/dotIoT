# A simple test script to test the ST77899 driver
# Expected result:
#   Yellow filled display with a Blue rectangle closes to the edges.

import machine
import st7789

VERSION='V1.0'

# Baudrate max 20000000 for ST7789
spi = machine.SPI(1, baudrate=20000000, polarity=1, phase=1, sck=machine.Pin(18), mosi=machine.Pin(19))
#display = st7789.ST7789(spi, 135, 240, reset=machine.Pin(23, machine.Pin.OUT), cs=machine.Pin(5, machine.Pin.OUT), dc=machine.Pin(16, machine.Pin.OUT), backlight=machine.Pin(4, machine.Pin.OUT))
display = st7789.ST7789(spi, 240, 135, reset=machine.Pin(23, machine.Pin.OUT), cs=machine.Pin(5, machine.Pin.OUT), dc=machine.Pin(16, machine.Pin.OUT), backlight=machine.Pin(4, machine.Pin.OUT), xstart=40, ystart=53)

def main():
    global display

    print('ST7789 test %s\n' % VERSION)

    display.init()
    display.on()
    display.fill(st7789.color565(0,255,250))
    display.rect(10, 10, 220, 115, st7789.color565(0,0,255))



if __name__ == "__main__":
    main()
