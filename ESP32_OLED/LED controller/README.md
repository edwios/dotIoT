AQIStation v1.0
===============

Air quality station, part of dotIoT.

An air quality station utilising a Lolin32/Wemos ESP32 board with OLED display and micropython to show the air quality indices received from MQTT.

The Air Quqlity indices shown including:

* eCO₂ in ppm
* eTVoC in ppm
* AQI

**Preparations**

Download firmware for ESP32 from MicroPython: http://micropython.org/download#esp32

Erase flash on ESP32:

`esptool.py --port /dev/tty.SLAB_USBtoUART erase_flash`

Flash firmware to ESP32:

`esptool.py --port /dev/tty.SLAB_USBtoUART --chip esp32 write_flash -z 0x1000 esp32-2019.bin`


**Install ampy**

Install the Ada-Fruit AMPY utility. You will need this to manage those python files on the ESP32 board.

`sudo pip3 install adafruit-ampy`


**Install to ESP32**

* Modify `boot.py` and replace <SSID_NAME> and <SSID_PASS> with your Wi-Fi base stsation's name and WiFi password. Then copy all files onto the ESP using `ampy put <file>`. E.g.


	```
	ampy put font6.py
	ampy put nunito_r.py
	ampy put ostrich_r.py
	ampy put ssd1306.py
	ampy put umqttsimple.py
	ampy put writer.py
	ampy put boot.py
	ampy put main.py
	```


Notes
-----

The following mictopython library modules are used in this project:

**MQTT**

https://github.com/micropython/micropython-lib/tree/master/umqtt.simple

**Font Writer**

Font writer was used to provide differnet fonts and font sizes for the OLED display
https://github.com/peterhinch/micropython-font-to-py

**SSD1306 display**

Have to use the micropython driver:
https://github.com/micropython/micropython/blob/master/drivers/display/ssd1306.py

