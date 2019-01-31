##
 #  @filename   :   startup.py
 #  @brief      :   Startup script for epapar display on RPi0w
 #  @author     :   Edwin Tam
 #
 #  Copyright (C) 2019 Telldus Technologies AB
 #
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
import binascii

connected = False
btconnected=False
m_broadcast = "No message"
m_cmd = "Idle"

EvTH7271="fc:f4:35:bf:6b:37"
EvTH9640="e3:13:83:3a:33:c8"
EnvMultiUV0980="e7:7c:12:1f:73:24"
EnvMultiIR9070="FD:CA:60:13:52:9E"

MQTT_HOST = "127.0.0.1"

def main():

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    client.connect_async(MQTT_HOST, 1883, 60)

    # Non-Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    # Other loop*() functions are available that give a threaded interface and a
    # manual interface.
    client.loop_start() #start loop to process received messages

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
    mesg_image = Image.new('1', (200, 32), 255)  # 255: clear the frame
    cmd_image  = Image.new('1', (104, 28), 255)  # 255: clear the frame

    blank_draw = ImageDraw.Draw(blank_image)
    conn_draw = ImageDraw.Draw(conn_image)
    time_draw = ImageDraw.Draw(time_image)
    date_draw = ImageDraw.Draw(date_image)
    info_draw = ImageDraw.Draw(info_image)
    mesg_draw = ImageDraw.Draw(mesg_image)
    cmd_draw = ImageDraw.Draw(cmd_image)
    conn_font = ImageFont.truetype('/home/edwintam/epap/fonts/entypo/Entypo.otf', 24)
    mesg_font = ImageFont.truetype('/home/edwintam/epap/fonts/nunito/Nunito-Bold.ttf', 28)
    cmd_font = ImageFont.truetype('/home/edwintam/epap/fonts/Bitstream-Vera-Sans/Vera-Bold.ttf', 24)
    info_font = ImageFont.truetype('/home/edwintam/epap/fonts/noto-mono/NotoMono-Regular.ttf', 12)
    datetime_font = ImageFont.truetype('/home/edwintam/epap/fonts/noto-mono/NotoMono-Regular.ttf', 12)
    blank_image_width, blank_image_height  = blank_image.size
    conn_image_width, conn_image_height  = conn_image.size
    time_image_width, time_image_height  = time_image.size
    date_image_width, date_image_height  = date_image.size
    info_image_width, info_image_height  = info_image.size
    mesg_image_width, mesg_image_height  = mesg_image.size
    cmd_image_width, cmd_image_height  = cmd_image.size
    h = socket.gethostname()+".local"
    lastTime = time.monotonic()
    ipaddr = socket.gethostbyname(h)
    while (True):
        thisTime = time.monotonic()
        if (thisTime - lastTime) > 10:
            lastTime = time.monotonic()
            h = socket.gethostname()+".local"
            ipaddr = socket.gethostbyname(h)
        # draw a rectangle to clear the image
        blank_draw.rectangle((0, 0, blank_image_width, blank_image_height), fill = 255)
        conn_draw.rectangle((0, 0, conn_image_width, conn_image_height), fill = 255)
        time_draw.rectangle((0, 0, time_image_width, time_image_height), fill = 255)
        date_draw.rectangle((0, 0, date_image_width, date_image_height), fill = 255)
        info_draw.rectangle((0, 0, info_image_width, info_image_height), fill = 255)
        mesg_draw.rectangle((0, 0, mesg_image_width, mesg_image_height), fill = 255)
        cmd_draw.rectangle((0, 0, cmd_image_width, cmd_image_height), fill = 255)
        if connected:
            conn_draw.text((0, 0), "Q", font = conn_font, fill = 0)
        else:
            conn_draw.text((0, 0), "X", font = conn_font, fill = 0)
        time_draw.text((0, 0), time.strftime('%H:%M'), font = datetime_font, fill = 0)
        date_draw.text((0, 0), time.strftime('%d/%m'), font = datetime_font, fill = 0)
        info_draw.text((0, 6), ipaddr, font=info_font, fill=0)
        mesg_draw.text((0, 0), m_broadcast, font=mesg_font, fill=0)
        cmd_draw.text((0, 4), m_cmd, font=cmd_font, fill=0)
        epd.set_frame_memory(conn_image.rotate(270, expand=1), 104, 2)
        epd.set_frame_memory(time_image.rotate(270, expand=1), 104, 208)
        epd.set_frame_memory(date_image.rotate(270, expand=1), 104, 16)
        epd.set_frame_memory(info_image.rotate(270, expand=1), 8, 134)
        epd.set_frame_memory(mesg_image.rotate(270, expand=1), 72, 52)
        epd.set_frame_memory(cmd_image.rotate(270, expand=1), 32, 92)


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
    client.subscribe([("sensornet/broadcast", 0), ("sensornet/command", 0), ("sensornet/env/home/balcony/temperature", 0), ("sensornet/env/home/balcony/humidity", 0), ("sensornet/env/home/living/aqi", 0)])

def on_disconnect(client, userdata, rc):
    global connected

    connected = False
    if rc != 0:
        print("Unexpected disconnection.")

def reverse(val):
    swb = bytearray(len(val))
    swb[0::2], swb[1::2] = val[1::2], val[0::2]
    return swb

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global m_cmd
    global m_broadcast

#    print(msg.topic+" "+str(msg.payload))
    if (msg.topic == "sensornet/command"):
        x = str(msg.payload.decode("utf-8"))
        m_cmd = x
    if (msg.topic == "sensornet/broadcast"):
        x = str(msg.payload.decode("utf-8"))
        m_broadcast = x

if __name__ == '__main__':
    main()

