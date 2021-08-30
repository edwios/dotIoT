# Weather Info on LilyGo TTV

## Required drivers and modules


`mqtt.robust`<br/>
[`Writer`](https://github.com/peterhinch/micropython-font-to-py/tree/master/writer), from Peterhinch<br/>
`ssd1306`

## Fonts used in this application

Zekton from Ray Larabie, used as the big digits

Aadhunik from Hareesh Seera, used for the room names

Jura-Medium for other smaller size fonts

## Changes

To display the degree symbol (º), the double quote symbol in `largedigits.py` was hacked to facilitate this. Therefore, use " and it will display as a º


## Install

Install [micropython](https://micropython.org/download/esp32/) on the LilyGo TTV.

Create a file called `secret.py` and add the followings as the content:
```
SSID = 'Wi-Fi name'
PASS = 'Wi-Fi password'
MQTT_USER = 'MQTT user name'
MQTT_PASS = 'MQTT password'
```

Copy all files to the LilyGo TTV using for example, `rshell` or `ampy`

Alternatively, use `mpy-cross` to complile everything except `main.py`, then copy the `main.py` and all `.mpy` files to the LiliGo TTV.


## Uses

Long touch to switch between Weather info and Clock display.

Short touch to switch between different rooms

