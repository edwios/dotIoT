##
 #  @filename   :   main.cpp
 #  @brief      :   2.13inch e-paper display demo
 #  @author     :   Yehui from Waveshare
 #
 #  Copyright (C) Waveshare     September 9 2017
 #
 # Permission is hereby granted, free of charge, to any person obtaining a copy
 # of this software and associated documnetation files (the "Software"), to deal
 # in the Software without restriction, including without limitation the rights
 # to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 # copies of the Software, and to permit persons to  whom the Software is
 # furished to do so, subject to the following conditions:
 #
 # The above copyright notice and this permission notice shall be included in
 # all copies or substantial portions of the Software.
 #
 # THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 # IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 # FITNESS OR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 # AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 # LIABILITY WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 # OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 # THE SOFTWARE.
 ##

import socket
import epd2in13
import time
from PIL import Image, ImageDraw, ImageFont
import paho.mqtt.client as mqtt
from bluepy import btle
import binascii

connected = False
btconnected=False
m_temp = "0ºC"
m_rh = "0%"
m_aqi = "AQI: 0"

EvTH7271="fc:f4:35:bf:6b:37"
EvTH9640="e3:13:83:3a:33:c8"
EnvMultiUV0980="e7:7c:12:1f:73:24"

def main():
    global m_temp
    global m_rh
    global m_aqi
    global connected
    global btconnected

    image = Image.open('dotIoT.tif')

    epd = epd2in13.EPD()
    epd.init(epd.lut_full_update)

    wipe_screen()
##
 # there are 2 memory areas embedded in the e-paper display
 # and once the display is refreshed, the memory area will be auto-toggled,
 # i.e. the next action of SetFrameMemory will set the other memory area
 # therefore you have to set the frame memory twice.
 ##     
    epd.set_frame_memory(image, 0, 0)
    epd.display_frame()
    epd.set_frame_memory(image, 0, 0)
    epd.display_frame()

    blank_image = Image.new('1', (24, 24), 255)  # 255: clear the frame
    conn_image = Image.new('1', (24, 24), 255)  # 255: clear the frame
    time_image = Image.new('1', (40, 16), 255)  # 255: clear the frame
    date_image = Image.new('1', (64, 16), 255)  # 255: clear the frame
    info_image = Image.new('1', (112, 18), 255)  # 255: clear the frame
    temp_image = Image.new('1', (126, 48), 255)  # 255: clear the frame
    rh_image   = Image.new('1', (62, 32), 255)  # 255: clear the frame
    aqi_image  = Image.new('1', (104, 28), 255)  # 255: clear the frame

    blank_draw = ImageDraw.Draw(blank_image)
    conn_draw = ImageDraw.Draw(conn_image)
    time_draw = ImageDraw.Draw(time_image)
    date_draw = ImageDraw.Draw(date_image)
    info_draw = ImageDraw.Draw(info_image)
    temp_draw = ImageDraw.Draw(temp_image)
    rh_draw = ImageDraw.Draw(rh_image)
    aqi_draw = ImageDraw.Draw(aqi_image)
    conn_font = ImageFont.truetype('/home/edwintam/epap/fonts/entypo/Entypo.otf', 24)
    temp_font = ImageFont.truetype('/home/edwintam/epap/fonts/nunito/Nunito-Bold.ttf', 48)
    rh_font = ImageFont.truetype('/home/edwintam/epap/fonts/nunito/Nunito-Bold.ttf', 28)
    aqi_font = ImageFont.truetype('/home/edwintam/epap/fonts/Bitstream-Vera-Sans/Vera-Bold.ttf', 24)
    info_font = ImageFont.truetype('/home/edwintam/epap/fonts/noto-mono/NotoMono-Regular.ttf', 12)
    datetime_font = ImageFont.truetype('/home/edwintam/epap/fonts/noto-mono/NotoMono-Regular.ttf', 12)
    blank_image_width, blank_image_height  = blank_image.size
    conn_image_width, conn_image_height  = conn_image.size
    time_image_width, time_image_height  = time_image.size
    date_image_width, date_image_height  = date_image.size
    info_image_width, info_image_height  = info_image.size
    temp_image_width, temp_image_height  = temp_image.size
    rh_image_width, rh_image_height  = rh_image.size
    aqi_image_width, aqi_image_height  = aqi_image.size
    h = socket.gethostname()+".local"
    lastTime = time.monotonic()
    getEnvInfoFromBLEDevices()
    ipaddr = socket.gethostbyname(h)
    while (True):
        thisTime = time.monotonic()
        if (thisTime - lastTime) > 300:
            lastTime = time.monotonic()
            getEnvInfoFromBLEDevices()
            ipaddr = socket.gethostbyname(h)
        # draw a rectangle to clear the image
        blank_draw.rectangle((0, 0, blank_image_width, blank_image_height), fill = 255)
        conn_draw.rectangle((0, 0, conn_image_width, conn_image_height), fill = 255)
        time_draw.rectangle((0, 0, time_image_width, time_image_height), fill = 255)
        date_draw.rectangle((0, 0, date_image_width, date_image_height), fill = 255)
        info_draw.rectangle((0, 0, info_image_width, info_image_height), fill = 255)
        temp_draw.rectangle((0, 0, temp_image_width, temp_image_height), fill = 255)
        rh_draw.rectangle((0, 0, rh_image_width, rh_image_height), fill = 255)
        aqi_draw.rectangle((0, 0, aqi_image_width, aqi_image_height), fill = 255)
        if connected:
            conn_draw.text((0, 0), "Q", font = conn_font, fill = 0)
        else:
            conn_draw.text((0, 0), "X", font = conn_font, fill = 0)
        time_draw.text((0, 0), time.strftime('%H:%M'), font = datetime_font, fill = 0)
        date_draw.text((0, 0), time.strftime('%d/%m'), font = datetime_font, fill = 0)
        info_draw.text((0, 6), ipaddr, font=info_font, fill=0)
        temp_draw.text((0, 0), m_temp, font=temp_font, fill=0)
        rh_draw.text((0, 4), m_rh, font=rh_font, fill=0)
        aqi_draw.text((0, 4), m_aqi, font=aqi_font, fill=0)
        epd.set_frame_memory(conn_image.rotate(270, expand=1), 104, 2)
        epd.set_frame_memory(time_image.rotate(270, expand=1), 104, 208)
        epd.set_frame_memory(date_image.rotate(270, expand=1), 104, 16)
        epd.set_frame_memory(info_image.rotate(270, expand=1), 8, 134)
        epd.set_frame_memory(temp_image.rotate(270, expand=1), 72, 52)
        epd.set_frame_memory(rh_image.rotate(270, expand=1), 72, 180)
        epd.set_frame_memory(aqi_image.rotate(270, expand=1), 32, 92)
        if btconnected:
            epd.set_frame_memory(conn_image.rotate(270, expand=1), 88, 2)
        else:
            epd.set_frame_memory(blank_image.rotate(270, expand=1), 88, 2)


        epd.display_frame()

# Wipe screen to white backgroud
# Would take long time
def wipe_screen():
    step=16
    x=0
    f=True

    epd = epd2in13.EPD()
    epd.init(epd.lut_partial_update)
    while (f):
        bimage = Image.new('1', (epd2in13.EPD_WIDTH, epd2in13.EPD_HEIGHT), 255)  # 255: clear the frame
        bdraw = ImageDraw.Draw(bimage)
        bdraw.rectangle((x, 0, step+x-1, epd2in13.EPD_HEIGHT-1), fill = 0)
        epd.clear_frame_memory(0xFF)
        epd.set_frame_memory(bimage, 0, 0)
        epd.display_frame()

        bimage = Image.new('1', (epd2in13.EPD_WIDTH, epd2in13.EPD_HEIGHT), 255)  # 255: clear the frame
        bdraw = ImageDraw.Draw(bimage)
        bdraw.rectangle((x, 0, step+x-1, epd2in13.EPD_HEIGHT-1), fill = 0)
        epd.clear_frame_memory(0xFF)
        epd.set_frame_memory(bimage, 0, 0)
        epd.display_frame()

        x += step
        f=(x<=epd2in13.EPD_WIDTH)

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    global connected

    connected = True
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe([("sensornet/env/home/balcony/temperature", 0), ("sensornet/env/home/balcony/humidity", 0), ("sensornet/env/home/living/aqi", 0)])

def on_disconnect(client, userdata, rc):
    global connected

    connected = False
    if rc != 0:
        print("Unexpected disconnection.")

def reverse(val):
    swb = bytearray(len(val))
    swb[0::2], swb[1::2] = val[1::2], val[0::2]
    return swb

def getEnvInfoFromBLEDevices():
    global m_temp
    global m_rh
    global btconnected

    gotdata = False
    error=False
    try:
#        devTH = btle.Peripheral(EnvMultiUV0980,btle.ADDR_TYPE_RANDOM)
#        devRH = btle.Peripheral(EvTH9640,btle.ADDR_TYPE_RANDOM)
        devRH = btle.Peripheral(EvTH7271,btle.ADDR_TYPE_RANDOM)
    except:
        error=True
        btconnected=False
        print("Cannot connect")

    if not error:
        btconnected=True
#        devTH.setMTU(31)
        devRH.setMTU(31)

        retry = 0
        while (not gotdata) and (retry < 4):
            envSensor = btle.UUID("0000181a-0000-1000-8000-00805f9b34fb")
            envTHSvc = devRH.getServiceByUUID(envSensor) 
            envRHSvc = devRH.getServiceByUUID(envSensor) 
            tempUUIDVal = btle.UUID("00002a6e-0000-1000-8000-00805f9b34fb")
            rhUUIDVal = btle.UUID("00002a6f-0000-1000-8000-00805f9b34fb")
            tempVal = envRHSvc.getCharacteristics(tempUUIDVal)[0]
            rhVal = envRHSvc.getCharacteristics(rhUUIDVal)[0]
            _tempB = tempVal.read()
            tempB = reverse(_tempB)
            _rhB = rhVal.read()
            rhB = reverse(_rhB)

            x = binascii.b2a_hex(tempB)
            y = binascii.b2a_hex(rhB)
            if (x != 0) and (y != 0):
                gotdata = True
                m_temp = str(round(int(x, 16)/100))+"ºC"
                m_rh = str(round(int(y,16)/100))+"%"
            else:
                retry += 1
        devRH.disconnect()
        print(time.strftime('%F %H:%M')+","+str(int(x, 16)/100.0)+","+str(int(y,16)/100.0))

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global m_aqi

#    print(msg.topic+" "+str(msg.payload))
    if (msg.topic == "sensornet/env/home/living/aqi"):
        x = str(msg.payload.decode("utf-8"))
        m_aqi = "AQI: "+str(round(float(x)))
    if (msg.topic == "sensornet/env/home/balcony/humidity"):
        x = str(msg.payload.decode("utf-8"))
#        m_rh = str(round(float(x)))+"%"

client = mqtt.Client()
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message

client.connect_async("10.0.1.250", 1883, 60)

# Non-Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
client.loop_start() #start loop to process received messages

if __name__ == '__main__':
    main()
