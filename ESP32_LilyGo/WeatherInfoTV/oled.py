from machine import Pin, SoftSPI
import ssd1306
import time

PWR_ON = 2
OLED_PWR = 33
TOUCH=15
TOUCH_PWR=32

TOUCHD=False

pwr_on=Pin(2, Pin.OUT, value=0)
oled_pwr = Pin(33, Pin.OUT, value=0)
touch = Pin(TOUCH, Pin.IN)
touch_pwr = Pin(TOUCH_PWR, Pin.OUT, value=0)

spi = SoftSPI(baudrate=27000000, sck=Pin(18), mosi=Pin(23), miso=Pin(32))
dc=Pin(19)
rst=Pin(4)
cs=Pin(5)

pwr_on.value(1)
touch_pwr.value(0)

oled_pwr.value(1)
display=ssd1306.SSD1306_SPI(128, 64, spi, dc, rst, cs)
display.poweron()
display.text('Hello', 0, 0, 1)
display.show()

while(1):
    SoftSPI.deinit(spi)
    touch_pwr = Pin(TOUCH_PWR, Pin.OUT, value=1)
    time.sleep_ms(20)
    touched = (touch.value() == 1)
    spi = SoftSPI(baudrate=27000000, sck=Pin(18), mosi=Pin(23), miso=Pin(32))
    if (touched):
        display.fill_rect(0, 0, 100, 16, 0)
        display.text('Hello Tammy', 0, 0, 1)
    else:
        display.fill_rect(0, 0, 100, 16, 0)
        display.text('Hello world', 0, 0, 1)
    display.show()

