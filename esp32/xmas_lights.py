import time
from umqtt.simple import MQTTClient
from machine import Pin, UART, PWM, reset, I2C
import network
import select
import esp32
import secrets
import config_xmas_lights as config
import ujson
import os
import ubinascii
import sys
from writer import Writer
import nunito_r
import ostrich_r
import font6
import ssd1306
import json
from neopixel import NeoPixel
import ntptime
#import esp
#esp.osdebug(None)
#import gc
#gc.collect()

DEBUG = True    # Global debug printing

DEFAULT_MESHNAME = secrets.DEFAULT_MESHNAME
DEFAULT_MESHPWD = secrets.DEFAULT_MESHPWD
SSID = secrets.SSID
PASS = secrets.PASS

DEFAULT_DSTADDR = "FFFF"
DEFAULT_OPCODE  = "D0"
DEFAULT_PARS    = "010100"

MQTT_SERVER = config.MQTT_SERVER
MQTT_CLIENT_ID = config.MQTT_CLIENT_ID
MQTT_TOPIC_PREFIX = config.MQTT_TOPIC_PREFIX
MQTT_TOPIC_HASS_PREFIX = config.MQTT_TOPIC_HASS_PREFIX

MQTT_USER = secrets.MQTT_USER
MQTT_PASS = secrets.MQTT_PASS
MQTT_SUB_TOPIC_ALL = MQTT_TOPIC_PREFIX + '#'
MQTT_SUB_TOPIC_CMD = MQTT_TOPIC_PREFIX + 'xmaslight/command'
MQTT_SUB_TOPIC_CONF = MQTT_TOPIC_PREFIX + 'xmaslight/config'
MQTT_PUB_TOPIC_STATUS = MQTT_TOPIC_PREFIX + 'xmaslight/status'
MQTT_PUB_TOPIC_HASS_PREFIX = MQTT_TOPIC_HASS_PREFIX
MQTT_SUB_TOPIC_HASS_PREFIX = MQTT_TOPIC_HASS_PREFIX
MQTT_SUB_TOPIC_HASS_SET = MQTT_SUB_TOPIC_HASS_PREFIX + '+/set'

CACHEDIR = 'cache'
DEVICE_CACHE_NAME = 'devices.json'
MESH_SECRTES_NAME = 'meshsecrets.json'
Device_Cache = CACHEDIR + '/' + DEVICE_CACHE_NAME
Mesh_Secrets = CACHEDIR + '/' + MESH_SECRTES_NAME

LED1 = config.LED1
LED2 = config.LED2
NEO1 = config.NEO1
N_NEO = config.N_NEO

ON_DATA = [1, 1, 0]
OFF_DATA = [0, 1, 0]

WAIT_TIME = 5

m_WiFi_connected = False
led1 = None
led2 = None
neo1 = None
status_led_1 = None
status_led_2 = None
m_client = None
m_devices = None
m_systemstatus = 0
m_brightness = 10
m_colour = 0xFFFFFF
m_state = "off"
Meshname = DEFAULT_MESHNAME
Meshpass = DEFAULT_MESHPWD

WIFI_ERROR_FLAG = const(1)
BT_ERROR_FLAG = const(2)
MQTT_ERROR_FLAG = const(4)
BTMOD_ERROR_FLAG = const(8)
STATUS_TO_MESH = const(0x11)
STATUS_FROM_MESH = const(0x12)
WIFI_CONNECTING = const(32)
EXIT_FLAG = const(0x80)
WIFI_CONNECTING_SYMB = "W)))"
WIFI_ERROR_SYMB = "Wi-Fi"
BT_ERROR_SYMB = "MESH"
MQTT_ERROR_SYMB = "MQTT"
BTMOD_ERROR_SYMB = "BTMOD"
STATUS_TO_MESH_SYMB = ">>>Mesh"
STATUS_FROM_MESH_SYMB = "Mesh>>>"
EXIT_SYMB = "QUIT"

def do_connect(ssid, pwd, forced=False):
    """Connect to Wi-Fi network with 10s timeout"""
    global DEBUG
    import network
    sta_if = network.WLAN(network.STA_IF)
    if forced:
        sta_if.disconnect()
        time.sleep(2)
    if not sta_if.isconnected():
        # if DEBUG: print('connecting to network...')
        sta_if.active(True)
        time.sleep(0.5)
        sta_if.connect(ssid, pwd)
        lastTime = time.time()
        while (not sta_if.isconnected()) and ((time.time() - lastTime) < 10):
            pass
        if (time.time() >= lastTime + 10):
            WiFi_connected = False
            print("Error: timeout connecting to WLAN %s" % ssid)
        else:
            if DEBUG: print("Connected to Wi-Fi")
            WiFi_connected = True
        if WiFi_connected and DEBUG: print('Wi-Fi connected, network config:', sta_if.ifconfig())
        return WiFi_connected
    return True


def on_message(topic, msg):
    """Callback for MQTT published messages """
    global DEBUG, MQTT_SUB_TOPIC_CMD, MQTT_PUB_TOPIC_STATUS, MQTT_SUB_TOPIC_CONF, MQTT_SUB_TOPIC_HASS_PREFIX
    m = msg.decode("utf-8")
    t = topic.decode("utf-8")
    if DEBUG: print('MQTT received: %s from %s' % (m, t))
    if (t == MQTT_SUB_TOPIC_CMD):
        process_command(m)
    if (t == MQTT_PUB_TOPIC_STATUS):
        process_status(m)
    if (t == MQTT_SUB_TOPIC_CONF):
        process_config(m)
    if (t.startswith(MQTT_SUB_TOPIC_HASS_PREFIX)):
        process_hass(t, m)


def connectWiFi(forced=False):
    global DEBUG, SSID, PASS
    if DEBUG: print("Connecting to Wi-Fi")
    if m_WiFi_connected and not forced:
        if DEBUG: print("Already connected to Wi-Fi")
        return True
    wifi_error(2)
    if do_connect(SSID, PASS, forced):
        print_progress("Wi-Fi OK")
        wifi_error(0)
        try:
            ntptime.settime()
        except:
            pass
        return True
    else:
        print("Error connecting to Wi-Fi")
        wifi_error(1)
        return False


def initMQTT(mqtt_client):
    """Initialise MQTT client and connect to the MQTT broker. """
    global m_client, m_WiFi_connected, m_systemstatus, DEBUG, MQTT_PASS, MQTT_USER, MQTT_SERVER, BT_ERROR_FLAG, MQTT_CLIENT_ID
    global MQTT_SUB_TOPIC_CMD, MQTT_SUB_TOPIC_STATUS, MQTT_SUB_TOPIC_CONF, MQTT_SUB_TOPIC_HASS_SET, MQTT_PUB_TOPIC_STATUS
    if not m_WiFi_connected:
        print("ERROR: MQTT: no Wi-Fi connected")
        return False
    if mqtt_client is None:
        if DEBUG: print("Connecting to MQTT server at %s" % MQTT_SERVER)
        if MQTT_USER == '':
            MQTT_USER = None
        if MQTT_PASS == '':
            MQTT_PASS = None
        try:
            mqtt_client = MQTTClient(MQTT_CLIENT_ID, MQTT_SERVER, user=MQTT_USER, password=MQTT_PASS)
        except:
            mqtt_client = None
    if mqtt_client is not None:
        print_progress("MQTT OK")
        if DEBUG: print("Connected to MQTT server")
        m_systemstatus = m_systemstatus & ~BT_ERROR_FLAG
        mqtt_client.set_callback(on_message)  # Specify on_message callback
        try:
            mqtt_client.connect()   # Connect to MQTT broker
        except:
            print("ERROR: MQTT: Cannot reach broker!")
            mqtt_error(1)
            return False
        m_client = mqtt_client
        m_client.subscribe(MQTT_SUB_TOPIC_CMD)
        m_client.subscribe(MQTT_SUB_TOPIC_CONF)
        m_client.subscribe(MQTT_SUB_TOPIC_HASS_SET)
        m_client.publish(MQTT_PUB_TOPIC_STATUS, "Ready")
        mqtt_error(0)
        return True
    else:
        mqtt_error(1)
        return False


def updateStatus():
    """ Send an update to MQTT for status renew """
    global m_client, MQTT_PUB_TOPIC_STATUS, DEBUG


def _send_command(cmd: str = 'AT'):
    """Internal method to send AT commands to BLE module appending 0D0A to the end"""
    global DEBUG, STATUS_TO_MESH
    if DEBUG: print("DEBUG: Sending %s to BLE Module" % cmd)
    print_status(STATUS_TO_MESH)
    m_uart.write(cmd)
    time.sleep(0.05)
    m_uart.write('\r\n')
    time.sleep(0.3)


def send_command(cmd: str = None):
    """Send AT command without AT+ prefix"""
    command = 'AT+'+cmd
    _send_command(command)


def checkBLEModule():
    """Check if BLE module is alive and communicable"""
    _send_command()
    if not expect_reply():
        print("ERROR: Cannot get in touch with BLE module!")
        return False
    return True


def resetBLEModule():
    """Reset the BLE module"""
    _send_command('AT+RST')
    if not expect_reply():
        print("ERROR: Cannot get in touch with BLE module!")
        return False
    return True


def _setMeshParams(name=DEFAULT_MESHNAME, pwd=DEFAULT_MESHPWD):
    """Internal method to set the mesh parameters to the BLE module. """
    send_command('MESHNAME=' + name)
    if not expect_reply('OK'):
        print("ERROR in setting Mesh Name")
        return False
    send_command('MESHPWD=' + pwd)
    if not expect_reply('OK'):
        print("ERROR in setting Mesh Password")
        return False
    return True


def setMeshParams(name=DEFAULT_MESHNAME, pwd=DEFAULT_MESHPWD):
    global Mesh_Secrets
    """Set mesh parameters to BLE module and reset it to make it effective."""
    if not _setMeshParams(name, pwd):
        return False
    if not resetBLEModule():
        print("ERROR: Cannot reset BLE module!")
        ble_error(1)
    if not _setMeshParams(name, pwd):
        return False
    cacheMeshSecrets(name, pwd, Mesh_Secrets)
    return True


def cacheMeshSecrets(name, pwd, cache_path=Mesh_Secrets):
    """Store mesh secrets in Flash"""
    if DEBUG: print("Create cache for mesh secrets in %s" % cache_path)
    meshsecrets = ujson.loads('{' + '"meshname":"{:s}", "meshpass":"{:s}"'.format(name, pwd) +'}')
    if cache_path is None:
        return None
    try:
        filep = open(cache_path, 'w')
    except:
        print("ERROR: Cannot cache mesh secrets to %s" % cache_path)
    else:
        filep.write(ujson.dumps(meshsecrets))
        filep.close()
        if DEBUG: print("DEBUG: Cache for mesh secrets created")
    return meshsecrets


def retrieveMeshSecrets(def_name=DEFAULT_MESHNAME, def_pass=DEFAULT_MESHPWD, cache_path=Mesh_Secrets):
    """Get the stored or default mesh secrets"""
    if DEBUG: print("DEBUG: Retrieving mesh secrets from %s" % Mesh_Secrets)
    if cache_path is None:
        return None
    try:
        filep = open(cache_path, 'r')
    except:
        # Mesh secrets not exist, create one
        if DEBUG: print("DEBUG: No mesh secret stored yet, creating one")
        meshsecrets = cacheMeshSecrets(def_name, def_pass, cache_path)
    else:
        if DEBUG: print("DEBUG: Reading mesh secrets from cache")
        jj = filep.read()
        meshsecrets = ujson.loads(jj)
        filep.close()
    return meshsecrets

def refresh_devices(config, cache_path):
    """Refresh devices from configuration received"""
    global m_devices, Device_Cache
    if DEBUG: print("DEBUG: Refreshing device database")
    print_progress("Refresh devices")
    try:
        m_devices = config['devices']
    except:
        print("ERROR: No device found in config!!")
        return None
    else:
        try:
            filep = open(cache_path, 'w')
        except:
            print("ERROR: Cannot write to device cache %s" % cache_path)
        else:
            filep.write(ujson.dumps(m_devices))
            filep.close()
            if DEBUG: print("DEBUG: Written device DB to cache")
    return m_devices



def retrieveDeviceDB(cache_path):
    """Restore device from DB"""
    global DEBUG
    if DEBUG: print("Retrieving devices from cache %s" % cache_path)
    devices = None
    try:
        filep = open(cache_path, 'r')
    except:
        if DEBUG: print("DEBUG: Device cache not exist yet")
    else:
        jj = filep.read()
        devices = ujson.loads(jj)
        filep.close()
        if DEBUG: print("DEBUG: Device DB loaded from cache")
    return devices


def lookup_device(name):
    """Look up the device's address from the given name"""
    global m_devices, DEBUG
    devaddr = 0
    if m_devices is None or name == '':
        return devaddr
    if DEBUG: print("DEBUG: Looking up device ID from database")
    for dev in m_devices:
        try:
            devname = dev['deviceName']
        except:
            devname = ''
        if devname == name:
            try:
                tmp = dev['deviceAddress']
            except:
                tmp = 0
            if tmp > 255:
                # from iOS share, the endian is wrong (<=v2.0.3)
                devaddr = tmp >> 8 + ((tmp & 0x0F) << 8)
            if DEBUG: print("Found device %s with addr %04x" % (name, devaddr))
            break
    return devaddr


def rev_lookup_device(devaddr):
    """Look up the device's address from the given name"""
    global m_devices, DEBUG
    name = None
    if m_devices is None or devaddr == 0:
        return name
    if DEBUG: print("DEBUG: Looking up device name from database")
    for dev in m_devices:
        try:
            tmp = dev['deviceAddress']
            if tmp > 255:
                addr = tmp >> 8 + ((tmp & 0x0F) << 8)
            else:
                addr = tmp
        except:
            addr = 0
        if addr == devaddr:
            try:
                name = dev['deviceName']
            except:
                name = None
            if DEBUG: print("Found device %s with addr %04x" % (name, devaddr))
            break
    return name


def mesh_send(dst=0x00, cmd=0xd0, data=[]):
    """Send to mesh using binary data"""
    length = len(data)
    if length == 0:
        return False
    atcommand = 'SEND={:x},{:d},{:02x}'.format(dst, length+1, cmd)
    for d in data:
        atcommand = atcommand + '{:02x}'.format(d)
    send_command(atcommand)
    if not expect_reply('OK'):
        print("ERROR in sending to mesh")
        return False
    return True


def mesh_send_asc(dst: int = 0x00, cmd: int = 0xd0, data: str = None):
    global DEBUG
    """Send to mesh using hexified ASCII string as the data
        dst:    Device address (2 bytes)
        cmd:    Op code (1 byte)
        data:   String of hexified bytes
    """
    length = len(data) >> 1
    if length == 0:
        return False
    atcommand = 'SEND={:s},{:s},{:s}{:s}'.format(dst, str(length), cmd, data)
    if DEBUG: print("Sending to UART: %s" % atcommand)
    send_command(atcommand)
    if not expect_reply('OK'):
        print("ERROR in sending to mesh")
        return False
    return True


def expect_reply(reply='OK'):
    """Expect from serial port some specific incoming"""
    return True
    rpy = getReply(5)
    if rpy is None:
        return False
    for i in rpy:
        if i == reply:
            return True
    return False


def getReply(timeout=10):
    global DEBUG, m_uart, poll
    """Check for serial port incoming"""
    events = poll.poll(timeout)
    data = ''
    while (len(events) > 0):
        events = poll.poll(timeout)
        for file in events:
            # file is a tuple
            if file[0] == m_uart:
                ch = m_uart.read(1)
                data = data + chr(ch[0])

    if data is not '':
        # Show the byte as 2 hex digits then in the default way
        # if DEBUG: print("DEBUG: received from BLE module: %s " % data)
        reply = []
        lines = data.split('\r\n')
        for line in lines:
            if line is not '':
                reply.append(line)
        if DEBUG: print("DEBUG: received %d lines of text as %s" % (len(reply), reply))
        return reply

"""
def check_callbacks():
    global DEBUG, STATUS_FROM_MESH
    replies = getReply(3)
    if replies is None:
        return
    for reply in replies:
        if reply.startswith('+DATA'):
            devaddrstr, lengthstr, callback = reply[6:].split(',')
            if DEBUG: print("DEBUG: Got call back from %s" % devaddrstr)
            print_status(STATUS_FROM_MESH)
            try:
                t = ubinascii.unhexlify(devaddrstr)
            except:
                devaddr = -1
            else:
                devaddr = t[0] * 256 + t[1]
            try:
                length = int(lengthstr)
            except:
                length = 0
            if (len(callback) != length * 2) or (length == 0) or (devaddr == -1):
                print("ERROR: Corrupted callback packet found")
                process_callback(devaddr, callback)
            else:
                process_callback(devaddr, callback)


def process_callback(devaddr, callback):
    global m_client, DEBUG, MQTT_PUB_TOPIC_STATUS
    if DEBUG: print("Processing call back from %04x" % devaddr)
    name = rev_lookup_device(devaddr)
    if name is None:
        return
    opcode = callback[:2]
    if opcode == 'DC':
        # Status notify report
        topic = MQTT_PUB_TOPIC_STATUS
        par1 = callback[2:4]
        par2 = callback[4:6]
        try:
            bgt = ubinascii.unhexlify(par1)[0]
        except:
            bgt = 0
        try:
            cct = ubinascii.unhexlify(par2)[0]
        except:
            cct = 0
        state = 'on'
        if bgt == 0:
            state = 'off'
        mesg = '"device_name":"{:s}", "state":"{:s}", "brightness":{:d}, "cct":{:d}'.format(name, state, bgt, cct)
        mesg = '{' + mesg + '}'
        if m_client:
            m_client.publish(topic, mesg.encode('utf-8'))
    else:
        if DEBUG: print("Unsupported call back opcode %s" % opcode)
        return
"""

def update_hass(name, state, brightness, cct):
    global DEBUG, m_client, MQTT_PUB_TOPIC_HASS_PREFIX
    if DEBUG: print("update_hass(): Pub status for %s" % (name))
    hass_state_topic = '{:s}{:s}'.format(MQTT_PUB_TOPIC_HASS_PREFIX, name)
    hass_mesg = {}
    hass_mesg['device_name'] = name
    if state is not None:
        hass_mesg['state'] = state.upper()
    if brightness is not None:
        hass_mesg['brightness'] = brightness
    if cct is not None:
        hasscct = cct
        if cct <= 100:
            cct1 = 100 - cct
            hasscct = int(cct1 * 347 / 100 + 153)
        hass_mesg['color_temp'] = hasscct
        hass_mesg['batt'] = cct
    hass_mesg['timestamp'] = str(time.time())
    try:
        if m_client:
            m_client.publish(hass_state_topic, json.dumps(hass_mesg).encode('utf-8'))
    except:
        print("ERROR: update_hass(hass_mesg) has invalid content")
        return


def process_hass(topic, msg):
    global DEBUG, ON_DATA, OFF_DATA
    global m_brightness, m_colour, m_state, neo1
    if DEBUG: print("Process HASS command %s at topic %s" % (msg, topic))
    try:
        mqtt_json = json.loads(msg)
    except:
        print("ERROR: JSON format error")
        return
    ts = topic.split('/')
    if ts is None:
        # We don't handle topics without '/'
        print("ERROR: process_hass(): Topic has no '/'")
        return
    if ts[-1:][0] != 'set':
        # We don't handle here non-set topics
        print("ERROR: process_hass(): Topic is not ended with 'set' (%s)" % ts[-1:][0])
        return
    device_name = ts[-2:][0]
    if device_name == '' or device_name == 'hass':
        # Missing device name, we don't handle either
        print("ERROR: process_hass(): Topic does not contain device name (%s)" % device_name)
        return
    if (neo1 is None):
        print("Error: Cannot proceed with no neopixels available")
        print_progress("E: No NEO")
        return
    if device_name is not None:
        if DEBUG: print("HASS control of device %s" % device_name)
        if device_name != "Bedlight":
            if DEBUG: print("Not me")
            return
        try:
            state = mqtt_json['state']
        except:
            state = m_state
        else:
            state = state.lower()
        if state == "on":
            st = 1
            m_state = "on"
        else:
            st = 0
            m_state = "off"
        try:
            brightness = mqtt_json['brightness']
        except:
            brightness = None
        try:
            cct = mqtt_json['color_temp']
        except:
            cct = None
        try:
            color = mqtt_json['color']
        except:
            color = None
        hexdata = ''
        if brightness is not None:
            try:
                m_brightness = int(brightness)
            except:
                brightness = m_brightness
        else:
            brightness = m_brightness
        if DEBUG: print("HASS control %s for state: %s, brightness %s, cct: %s, color: %s" % (device_name, state, brightness, cct, color))
        if (color is not None):
            try:
                cr = color['r']
                cg = color['g']
                cb = color['b']
                r = int(cr)
                g = int(cg)
                b = int(cb)
            except:
                print("ERROR: Malformed RGB colour in JSON")
                return
            if (r > 255) or (g > 255) or (b > 255) or (r < 0) or (g < 0) or (b < 0):
                print("ERROR: RGB colour values outside of 0..255")
                return
            hexdata = '{:02X}'.format(r) + '{:02X}'.format(g) + '{:02X}'.format(b)
            if hexdata != '':
                cl = int(hexdata, 16)
                if (cl > 0xFFFFFF):
                    print("ERROR: RGB value must be 3 bytes")
                    print_progress("E: RGB")
                    return
                else:
                    m_colour = cl
        data = m_colour.to_bytes(3, 'big')
        if (m_colour > 0) and (m_brightness > 0) and (state != "off"):
            st = 1
            m_state = "on"
        b = m_brightness * st
        if DEBUG: print("DEBUG: Setting ALL pixels to %X (%d)" % (m_colour, b))
        for i in range(N_NEO):
            neo1[i] = (int(data[0] * b / 100), int(data[1] * b / 100), int(data[2] * b / 100))
        neo1.write()
        if (m_colour == 0) or (m_brightness == 0) or (st == 0):
            update_hass("Bedlight", "OFF", 0, 0)
            m_state = "off"
        else:
            update_hass("Bedlight", "ON", m_brightness, 0)



def process_command(mqttcmd):
    global oled, neo1, N_NEO, DEBUG
    """Process mesh commands received from MQTT
        MQTT commands take forms:
            {"command", "state", "brightness", "color_temp", "white_value", "rgb", "raw", "value"}
            Single word commands, such as debug, nodebug
            Compound commands composed of:
                a device name or device id,
                a '/',
                a single command or a tupule containing a command and a value separated by a ':'
                E.g.
                    7/on
                    Hall light/off
                    Table lamp/dim:25
    """
    if DEBUG: print("Process command %s" % mqttcmd)
    try:
        mqtt_json = json.loads(mqttcmd)
    except:
        print("ERROR: JSON format error")
        return
    try:
        mqttcmd = mqtt_json['command']
    except:
        mqttcmd = None
    try:
        mqttval = mqtt_json['value']
    except:
        mqttval = None
    if mqttcmd is not None:
        mqttcmd = mqttcmd.lower()
        print_progress(mqttcmd[:16])
        if mqttcmd is not None:
            # {"command":"debug"}
            if (mqttcmd == "debug"):
                DEBUG = True
                return
            elif (mqttcmd == "nodebug"):
                DEBUG = False
                return
            elif (mqttcmd == "clear_all"):
                clear_neo()
                return
            elif (mqttcmd == "display_on"):
                oled.poweron()
                return
            elif (mqttcmd == "display_off"):
                oled.poweroff()
                return
            else:
                return
    if True:
        try:
            mqttdevname = mqtt_json['device_name']
        except:
            mqttdevname = None
        try:
            dids = mqtt_json['device_addr']
        except:
            dids = None
        try:
            mhcmd = mqtt_json['state']
        except:
            mhcmd = None
        try:
            brightness = mqtt_json['brightness']
        except:
            brightness = None
        try:
            cct = mqtt_json['color_temp']
        except:
            cct = None
        try:
            color = mqtt_json['color']
        except:
            color = None
        try:
            pixels = mqtt_json['pixels']
        except:
            pixels = None
        if pixels is not None:
            if len(pixels) > N_NEO:
                print_progress("W: N pix")
                if DEBUG: print("DEBUG: Trimmed to %d pixels", N_NEO)
                pixels = pixels[:N_NEO]
        if mhcmd is not None:
            hcmd = mhcmd.lower()
        else:
            hcmd = ''
        hexdata = ''
        did = 0
        if (neo1 is None):
            print("Error: Cannot proceed with no neopixels available")
            print_progress("E: No NEO")
            return
        if dids is not None:
            try:
                did = int(dids)
            except:
                did = lookup_device(dids)
        if (did > 0):
            if DEBUG: print("DEBUG: Recevied %s from MQTT > ID: %s, cmd: %s" % (mqttcmd, did, hcmd))
            if (hcmd == "on"):
                # {"state":"on", "device_addr":2}
                neo1[did] = (255, 255, 255)
            elif (hcmd == "off"):
                neo1[did] = (0, 0, 0)
            elif (brightness is not None):
                hexdata = brightness
                if hexdata != '':
                    try:
                        i = int(hexdata)
                    except:
                        i = 25
                    if (i > 100 or i < 0):
                        print_progress("E: Lum")
                    else:
                        r, g, b = neo1[did]
                        neo1[did] = (int(r * i / 100), int(g * i / 100), int(b * i / 100))
            elif (cct is not None):
                hexdata = cct
                if hexdata != '':
                    try:
                        i = int(hexdata)
                    except:
                        i = 2700
                    if (i < 1800 or i > 6500):
                        print("ERROR: CCT value must be between 1800K and 6500K")
                    else:
                        ct = int(100 * (i - 2700)/3800)
                        if ct < 0:
                            ct = 0
                        if ct > 100:
                            ct = 100
                        # neo1[did] = (r, g, b)
            elif (color is not None):
                # {"color":{"r":100, "g":210, "b":155}, "device_addr":2}
                try:
                    color_r = color['r']
                except:
                    color_r = 0
                try:
                    color_g = color['g']
                except:
                    color_g = 0
                try:
                    color_b = color['b']
                except:
                    color_b = 0
                hexdata = '{:02X}'.format(color_r) + '{:02X}'.format(color_g) + '{:02X}'.format(color_b)
                if hexdata != '':
                    i = int(hexdata, 16)
                    if (i > 0xFFFFFF):
                        print_progress("E: RGB")
                    else:
                        data = i.to_bytes(3, 'big')
                        neo1[did] = (data[0], data[1], data[2])
            else:
                return
            neo1.write()
        elif (color is not None) and (pixels is not None):
            # {"color":{"r":100, "g":210, "b":155}, "pixels":"111000111000111"}
            try:
                color_r = color['r']
            except:
                color_r = 0
            try:
                color_g = color['g']
            except:
                color_g = 0
            try:
                color_b = color['b']
            except:
                color_b = 0
            hexdata = '{:02X}'.format(color_r) + '{:02X}'.format(color_g) + '{:02X}'.format(color_b)
            if hexdata != '':
                try:
                    cl = int(hexdata, 16)
                except:
                    cl = 0
                if (cl > 0xFFFFFF):
                    print_progress("E: RGB")
                elif len(pixels) == 0:
                    print_progress("E: pixels")
                else:
                    if DEBUG: print("DEBUG: Setting %d pixels to a color" % len(pixels))
                    data = cl.to_bytes(3, 'big')
                    all_dark = True
                    for i in range(len(pixels)):
                        if pixels[i:i+1] == '1':
                            all_dark = False    # Any pixel on is not dark
                            neo1[i] = (data[0], data[1], data[2])
                    neo1.write()
                    if (cl == 0) or all_dark:
                        update_hass("Bedlight", "OFF", 0, 0)
                    else:
                        update_hass("Bedlight", "ON", 100, 0)
        else:
            return


def cmd(device_addr, op_code, pars):
    global DEBUG
    """Properly format mesh command before sending to mesh"""
    if DEBUG: print("Sending to %s op code %s and pars %s" % (device_addr, op_code, pars))
    Dstdev = '{:04x}'.format(device_addr)
    Opcode = '{:02x}'.format(op_code)
    Params = ''
    for i in pars:
        Params = Params + '{:02x}'.format(i)
    mesh_send_asc(dst=Dstdev, cmd=Opcode, data=Params)


def process_status(status):
    """Process statuses received from Mesh"""
    global DEBUG
    if DEBUG: print("Process status %s" % status)


def process_config(conf):
    global N_NEO, DEBUG
    """Process configuration updates from Mesh or WiFi

        The configuration is expected to be a decrypted JSON containing one or more of the followings:
            Mesh name and mesh password
            Device information including at least the Device name and Device address
    """
    global Meshname, Meshpass, m_devices
    config = None
    if DEBUG: print("Process config %s" % conf)
    print_progress("Renew config")
    try:
        config = ujson.loads(conf)
    except:
        print("ERROR: Improper json in config")
        return False
    try:
        mn = config['space']['meshNetworkName']
        mp = config['space']['meshNetworkPassword']
    except:
        mn = Meshname
        mp = Meshpass
    if (mn != Meshname) or (mp != Meshpass):
        if DEBUG: print("DEBUG: Setting new mesh name and password")
        Meshname = mn
        Meshpass = mp
        setMeshParams(mn, mp)
        refresh_devices(config, Device_Cache)
    try:
        np = config['pixels']
    except:
        np = N_NEO
    if (np != N_NEO):
        # We have change of pixels
        if (np <= 0) or (np > 500):
            print_progress("E: N pix")
            return False
        N_NEO = np
        msg = 'I: {:d}'.format(N_NEO)
        print_progress(msg)
        if DEBUG: print("Reconfigured to %d pixels" % N_NEO)
        board_init()
    return True


def wifi_error(e):
    global WIFI_ERROR_FLAG, WIFI_CONNECTING
    """Flash LED upon Wi-Fi connection failed"""
    if e == 1:
        print_status(WIFI_ERROR_FLAG)
    elif e == 2:
        print_status(WIFI_CONNECTING)
    else:
        print_status(~WIFI_CONNECTING)
        print_status(~WIFI_ERROR_FLAG)


def mqtt_error(e):
    global MQTT_ERROR_FLAG
    """Flashes LED upon MQTT connection failure"""
    if e == 1:
        print_status(MQTT_ERROR_FLAG)
    else:
        print_status(~MQTT_ERROR_FLAG)


def ble_error(e):
    global BT_ERROR_FLAG
    """Flashes LED upon communication problem with the BLE module"""
    if e == 1:
        print_status(BT_ERROR_FLAG)
    else:
        print_status(~BT_ERROR_FLAG)


def exit_mode():
    global LED1, LED2, status_led_1, status_led_2, EXIT_FLAG, SSID, PASS, m_WiFi_connected
    """Exit willingly"""
    m_WiFi_connected = do_connect(SSID, PASS) # If we want webrepl afterwards
    print_status(EXIT_FLAG)
    time.sleep(3)
    sys.exit(0)


def board_init():
    global LED1, LED2, NEO1, N_NEO, led1, led2, neo1
    LED1.init(mode=Pin.OUT)
    NEO1.init(mode=Pin.OUT)
    led1 = LED1
    led1.value(1)
    neo1 = NeoPixel(NEO1, N_NEO)
    clear_neo()


def clear_neo():
    global neo1, N_NEO
    # Clear lightstrip
    if neo1 is not None:
        for i in range(N_NEO):
            neo1[i] = (0, 0, 0)
        neo1.write()
        update_hass("Bedlight", "OFF", 0, 0)


m_rstcnt = 0
"""
def check_reset():
    global m_rstcnt
    if key1.value() == 0:
        print_progress("Reset/Exit?")
        if m_rstcnt == 0:
            m_rstcnt = time.time()  # start timer at first keypress
    else:
        if m_rstcnt == 0:
            return  # no key pressed so far
        # key released, check elapsed time on keypress
        t = time.time() - m_rstcnt
        if t > 0.05 and t < 1:
            # perform reset only when key is pressed down for a while (debounce) but not too long (exit)
            reset()
        if t > 5:
            # Quit when key hold for > 5s
            exit_mode()
        # Key released but not meant for reset, clear timer
        m_rstcnt = 0
"""


def check_reset():
    pass


def displayInit():
    global oled, wri_m
    oled.fill(0)
    # oled.text(String,X-pixels,y-Pixels)
    wri_m.set_textpos(oled, 0, 0)  # verbose = False to suppress console output
    wri_m.printstring('XMas Light')
    # Show on display
    oled.show()


def print_progress(msg):
    global oled, wri_m
    wri_m.set_textpos(oled, 32, 0)  # verbose = False to suppress console output
    wri_m.printstring("                            ")
    wri_m.set_textpos(oled, 32, 0)  # verbose = False to suppress console output
    wri_m.printstring(msg)
    oled.show()


def print_status(statusflag):
    global m_systemstatus, wri_m, oled, DEBUG
    m_systemstatus = m_systemstatus | statusflag
    st = m_systemstatus
    if st == 0 or st == 0x80:
        if st == 0:
            msg = "Ready"
        else:
            msg = EXIT_SYMB
    else:
        if st & STATUS_FROM_MESH:
            msg = STATUS_FROM_MESH_SYMB
        elif st & STATUS_TO_MESH:
            msg = STATUS_TO_MESH_SYMB
        elif st & WIFI_CONNECTING:
            msg = WIFI_CONNECTING_SYMB
        else:
            msg = "ERR: "
            if st & WIFI_ERROR_FLAG:
                msg = msg + ' ' + WIFI_ERROR_SYMB
            if st & BT_ERROR_FLAG:
                msg = msg + ' ' + BT_ERROR_SYMB
            if st & MQTT_ERROR_FLAG:
                msg = msg + ' ' + MQTT_ERROR_SYMB
            if st & BTMOD_ERROR_FLAG:
                msg = msg + ' ' + BTMOD_ERROR_SYMB
    wri_m.set_textpos(oled, 50, 0)  # verbose = False to suppress console output
    wri_m.printstring("                        ")
    wri_m.set_textpos(oled, 50, 0)  # verbose = False to suppress console output
    wri_m.printstring(msg)
    oled.show()


i2c = I2C(scl=Pin(4), sda=Pin(5))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)
wri_l = Writer(oled, nunito_r)
wri_v = Writer(oled, ostrich_r)
wri_m = Writer(oled, font6)
wri_m_len = wri_m.stringlen("999")
wri_v_len = wri_v.stringlen("9999")

board_init()
displayInit()

t = time.time()
released = False
'''
if key1.value() == 0:
    while (time.time() - t < WAIT_TIME):
        if (key1.value() == 1):
            released = True
            break
    if not released:
        exit_mode()

if released:
    """Button pressed during boot, change to config #2"""
    if DEBUG: print("DEBUG: Switch to alt config")
    import config_oled_alt as config_alt
    import secrets_alt

    wri_m.set_textpos(oled, 16, 0)  # verbose = False to suppress console output
    wri_m.printstring('Alternate config')
    oled.show()

    DEFAULT_MESHNAME = secrets_alt.DEFAULT_MESHNAME
    DEFAULT_MESHPWD = secrets_alt.DEFAULT_MESHPWD
    SSID = secrets_alt.SSID
    PASS = secrets_alt.PASS
    MQTT_SERVER = config_alt.MQTT_SERVER
    MQTT_CLIENT_ID = config_alt.MQTT_CLIENT_ID
    MQTT_TOPIC_PREFIX = config_alt.MQTT_TOPIC_PREFIX
    try:
        MQTT_USER = secrets_alt.MQTT_USER
    except:
        MQTT_USER = None
    try:
        MQTT_PASS = secrets_alt.MQTT_PASS
    except:
        MQTT_PASS = None
else:
    wri_m.set_textpos(oled, 16, 0)  # verbose = False to suppress console output
    wri_m.printstring('Default config')
    oled.show()
'''

wri_m.set_textpos(oled, 16, 0)  # verbose = False to suppress console output
wri_m.printstring('Default config')
oled.show()


if DEBUG: print("Connecting to Wi-Fi")
m_WiFi_connected = connectWiFi()

# Main()
"""
XMas Lights is controlled via MQTT with the following messgages in JSON.
The Topic is sensornet/xmaslights/command.

To set the color pattern on the XMas lights
{
    "color":
    {
        "r": byte
        "g": byte
        "b": byte
    },
    "pixels": "string"
}
pixels defines the liner mapping of the LED strip where 1 represent a lit dot and 0 dark
color defines one single color for all the '1's in the pixels string

To turn off all dots in the XMas lights, use the following MQTT message.
{
    "command":"clear_all"
}
"""


print("INFO: Starting XMas light")
print_progress("Starting up")

try:
    os.mkdir(CACHEDIR)
except:
    print("WARNING: Cannot create dir %s" % CACHEDIR)

"""
m_meshsecrets = retrieveMeshSecrets(DEFAULT_MESHNAME, DEFAULT_MESHPWD, Mesh_Secrets)
Meshname = m_meshsecrets['meshname']
Meshpass = m_meshsecrets['meshpass']
if DEBUG: print("Using mesh name %s and pass %s" % (Meshname, Meshpass))
m_devices = retrieveDeviceDB(Device_Cache)

if DEBUG: print("Initialising UART to BLE")
print_progress("Init UART")
m_uart = UART(2, tx=15, rx=13)                         # init with given baudrate
m_uart.init(115200, bits=8, parity=None, stop=1, timeout=10)

poll = select.poll()
poll.register(m_uart, select.POLLIN)

if not checkBLEModule():
    print("ERROR: Cannot find BLE module!")
    print_status(BTMOD_ERROR_FLAG)
else:
    m_systemstatus = m_systemstatus & ~BTMOD_ERROR_FLAG

atcmd = ''
Opcode = ''

setMeshParams(name=Meshname, pwd=Meshpass)
"""

print_progress("                ")
print_status(m_systemstatus)
m_systemstatus = 0  # Reset system status so that new status can be updated within the loop
time.sleep(0.1)
# if DEBUG: print("Entering infinte loop")
while True:
    # Processes MQTT network traffic, callbacks and reconnections. (Blocking)
    if m_client: 
        try:
            m_client.check_msg()
        except:
            # if DEBUG: print("MQTT broker not reachable")
            m_client = None
    if m_client is None:
        time.sleep(5)   # Sth wrong! Wait 5s before we attempt anything
        m_WiFi_connected = connectWiFi()
        while not (initMQTT(m_client)):
            time.sleep(10)
            if not m_WiFi_connected:
                m_WiFi_connected = connectWiFi()
        if (m_state != "on"):
            update_hass("Bedlight", "OFF", 0, 0)
        else:
            update_hass("Bedlight", "ON", m_brightness, 0)
    check_reset()
