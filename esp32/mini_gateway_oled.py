import time
from umqtt.simple import MQTTClient
from machine import Pin, UART, PWM, reset, I2C
import network
import select
import esp32
import secrets
import config_oled as config
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
MQTT_USER = secrets.MQTT_USER
MQTT_PASS = secrets.MQTT_PASS
MQTT_SUB_TOPIC_ALL = MQTT_TOPIC_PREFIX + '#'
MQTT_SUB_TOPIC_CMD = MQTT_TOPIC_PREFIX + 'command'
MQTT_SUB_TOPIC_CONF = MQTT_TOPIC_PREFIX + 'config'
MQTT_PUB_TOPIC_STATUS = MQTT_TOPIC_PREFIX + 'status'
MQTT_SUB_TOPIC_HASS_PREFIX = MQTT_TOPIC_PREFIX + 'hass/'
MQTT_SUB_TOPIC_HASS_SET = MQTT_SUB_TOPIC_HASS_PREFIX + '+/set'
MQTT_PUB_TOPIC_HASS_PREFIX = MQTT_TOPIC_PREFIX + 'hass/'

CACHEDIR = 'cache'
DEVICE_CACHE_NAME = 'devices.json'
MESH_SECRTES_NAME = 'meshsecrets.json'
Device_Cache = CACHEDIR + '/' + DEVICE_CACHE_NAME
Mesh_Secrets = CACHEDIR + '/' + MESH_SECRTES_NAME

LED1 = config.LED1
LED2 = config.LED2
KEY1 = config.KEY1

ON_DATA = [1, 1, 0]
OFF_DATA = [0, 1, 0]

WAIT_TIME = 5

m_WiFi_connected = False
led1 = None
led2 = None
key1 = None
status_led_1 = None
status_led_2 = None
m_client = None
m_devices = None
m_systemstatus = 0
Meshname = DEFAULT_MESHNAME
Meshpass = DEFAULT_MESHPWD

WIFI_ERROR_FLAG = 1
BT_ERROR_FLAG = 2
MQTT_ERROR_FLAG = 4
BTMOD_ERROR_FLAG = 8
STATUS_TO_MESH = 0x11
STATUS_FROM_MESH = 0x12
EXIT_FLAG = 0x80
WIFI_ERROR_SYMB = "Wi-Fi"
BT_ERROR_SYMB = "MESH"
MQTT_ERROR_SYMB = "MQTT"
BTMOD_ERROR_SYMB = "BTMOD"
STATUS_TO_MESH_SYMB = ">>>Mesh"
STATUS_FROM_MESH_SYMB = "Mesh>>>"
EXIT_SYMB = "QUIT"

def do_connect(ssid, pwd):
    """Connect to Wi-Fi network with 10s timeout"""
    import network
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        if DEBUG: print('connecting to network...')
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


def on_message(topic, msg):
    """Callback for MQTT published messages """
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


def initMQTT():
    """Initialise MQTT client and connect to the MQTT broker. """
    global m_client
    if not m_client:
        print("ERROR: No MQTT connection to init for")
        return False
    m_client.set_callback(on_message)  # Specify on_message callback
    m_client.connect()   # Connect to MQTT broker
#    m_client.subscribe(MQTT_SUB_TOPIC_ALL)
    m_client.subscribe(MQTT_SUB_TOPIC_CMD)
    m_client.subscribe(MQTT_PUB_TOPIC_STATUS)
    m_client.subscribe(MQTT_SUB_TOPIC_CONF)
    m_client.subscribe(MQTT_SUB_TOPIC_HASS_SET)
    return True


def _send_command(cmd: str = 'AT'):
    """Internal method to send AT commands to BLE module appending 0D0A to the end"""
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
        ble_error()
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
    global m_devices
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
    global m_devices
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


def check_callbacks():
    replies = getReply(3)
    if replies is None:
        return
    for reply in replies:
        if reply.startswith('+DATA'):
            try:
                devaddrstr, lengthstr, callback = reply[6:].split(',')
            except:
                devaddrstr = None
            if devaddrstr is not None:
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
    global m_client, DEBUG
    if DEBUG: print("Processing call back from %04x" % devaddr)
    name = rev_lookup_device(devaddr)
    if name is None:
        print("ERROR: process_callback(): cannot find device name with address %d" % devaddr)
        return
    opcode = callback[:2]
    if opcode == 'DC':
        # Status notify report
        if DEBUG: print("process_callback(): Got status call back from %s (%04x)" % (name, devaddr))
        topic = MQTT_PUB_TOPIC_STATUS
        par1 = callback[2:4]
        par2 = callback[4:6]
        bgt = None
        state = None
        if par1 != '':
            try:
                bgt = ubinascii.unhexlify(par1)[0]
            except:
                bgt = 0
            if bgt > 0:
                state = 'on'
            else:
                state = 'off'
        cct = None
        if par2 != '':
            try:
                cct = ubinascii.unhexlify(par2)[0]
            except:
                cct = 0
        mesg = '"device_name":"{:s}"'.format(name)
        if bgt is not None:
            mesg = mesg + ', "state":"{:s}", "brightness":{:d}'.format(state, bgt)
        if cct is not None:
            mesg = mesg + ', "cct":{:d}'.format(cct)
        mesg = '{' + mesg + '}'
        if m_client:
            m_client.publish(topic, mesg.encode('utf-8'))
        update_hass(name, state, bgt, cct)
    else:
        if DEBUG: print("Unsupported call back opcode %s" % opcode)
        return


def update_hass(name, state, brightness, cct):
    global DEBUG, m_client, MQTT_PUB_TOPIC_HASS_PREFIX
    if DEBUG: print("update_hass(): Pub status for %s" % (name))
    hass_state_topic = MQTT_PUB_TOPIC_HASS_PREFIX + name
    hass_mesg = '"device_name":"{:s}"'.format(name)
    if state is not None:
        hass_mesg = hass_mesg + ',"state":"{:s}"'.format(state.upper())
    if brightness is not None:
        hass_mesg = hass_mesg + ',"brightness":{:d}'.format(brightness)
    if cct is not None:
        hasscct = cct
        if cct <= 100:
            cct = 100 - cct
            hasscct = int(cct * 347 / 100 + 153)
        hass_mesg = hass_mesg + ',"color_temp":{:d}'.format(hasscct)
    hass_mesg = '{' + hass_mesg + '}'
    if DEBUG: print("update_hass(): Pub mesg: %s" % hass_mesg)
    if m_client:
        m_client.publish(hass_state_topic, hass_mesg.encode('utf-8'))


def process_command(mqttcmd):
    """Process mesh commands received from MQTT
        MQTT commands take forms:
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
    global DEBUG
    if DEBUG: print("Process command %s" % mqttcmd)
    print_progress(mqttcmd[:16])
    if mqttcmd is not '':
        if '/' not in mqttcmd:
            if (mqttcmd == "debug"):
                DEBUG = True
                return
            elif (mqttcmd == "nodebug"):
                DEBUG = False
                return
            else:
                return
        dids, mhcmd = mqttcmd.split('/')
        mhcmd = mhcmd.lower()
        hexdata = ''
        if ':' in mhcmd:
            hcmd, hexdata = mhcmd.split(':')
        else:
            hcmd = mhcmd
        try:
            did = int(dids)
        except:
            did = lookup_device(dids)
        if (did > 0):
            if DEBUG: print("DEBUG: Recevied %s from MQTT > ID: %s, cmd: %s" % (mqttcmd, did, hcmd))
            if (hcmd == "on"):
                cmd(did, 0xd0, ON_DATA)
            elif (hcmd == "off"):
                cmd(did, 0xd0, OFF_DATA)
            elif (hcmd == "dim"):
                if hexdata != '':
                    try:
                        i = int(hexdata)
                    except:
                        i = 25
                    if (i > 100 or i < 0):
                        print("ERROR: Lumnance value must be between 0 and 100")
                    else:
                        data = i.to_bytes(1, 'big')
                        cmd(did, 0xd2, list(data))
            elif (hcmd == "cct"):
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
                        data = i.to_bytes(2, 'big')
                        cmd(did, 0xf5, [0x10] + list(data))
                        time.sleep(0.2)
                        data = ct.to_bytes(1, 'big')
                        cmd(did, 0xe2, [0x05] + list(data))
            elif (hcmd == "rgb"):
                if hexdata != '':
                    i = int(hexdata, 16)
                    if (i > 0xFFFFFF):
                        print("ERROR: RGB value must be 3 bytes")
                    else:
                        data = i.to_bytes(3, 'big')
                        cmd(did, 0xe2, [0x04] + list(data))
            elif (hcmd == "get_sunrise"):
                cmd(did, 0xea, [0x08, 0x82])
                _expectedCallBack = [0xeb, 0x82]
            elif (hcmd == "get_sunset"):
                cmd(did, 0xea, [0x08, 0x83])
                _expectedCallBack = [0xeb, 0x83]
            elif (hcmd == "get_astro"):
                cmd(did, 0xea, [0x08, 0x85])
                _expectedCallBack = [0xeb, 0x85]
            elif (hcmd == "get_power"):
                cmd(did, 0xc0, [0x08, 0xe1])
                _expectedCallBack = [0xc1, 0xe1]
            elif (hcmd == "get_status"):
                cmd(did, 0xda, [0x10])
                _expectedCallBack = [0xdb, 0x00]
            elif (hcmd == "get_timer"):
                if (hexdata != ''):
                    i = int(hexdata)
                    if (i > 15):
                        print("ERROR: Only 16 timers")
                    else:
                        data = i.to_bytes(1, 'big')
                        cmd(did, 0xe6, [0x10] + list(data))
                        _expectedCallBack = [0xe7, 0xa5]
            elif (hcmd == "get_scene"):
                if (hexdata != ''):
                    i = int(hexdata)
                    if (i > 15):
                        print("ERROR: Only 16 scenes")
                    else:
                        data = i.to_bytes(1, 'big')
                        cmd(did, 0xc0, [0x10] + list(data))
                        _expectedCallBack = [0xc1, 0x00]
            elif (hcmd == 'raw'):
                if hexdata != '':
                    hexlist = list(hexdata[i:i+2] for i in range(0, len(hexdata), 2))
                    try:
                        t = ubinascii.unhexlify(hexlist[0])
                        c = int(t[0])
                    except:
                        print("ERROR: Illegal op code in raw %s" % hexlist[0])
                        return
                    try:
                        t = ubinascii.unhexlify(hexlist[1])
                        _expectedCallBack = int(t[0])
                    except:
                        print("ERROR: Illegal callback in raw %s" % hexlist[1])
                        _expectedCallBack = 0
                    parsstr = hexlist[2:]
                    pars = []
                    for par in parsstr:
                        try:
                            t = ubinascii.unhexlify(par)
                            p = int(t[0])
                        except:
                            p = 0
                        pars.append(p)
                    cmd(did, c, pars)


def process_hass(topic, msg):
    global DEBUG
    if DEBUG: print("Process HASS command %s at topic %s" % (msg, topic))
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
    if device_name is not None:
        if DEBUG: print("HASS control of device %s" % device_name)
        try:
            mqtt_json = json.loads(msg)
        except:
            print("ERROR: JSON format error")
            return
        try:
            state = mqtt_json['state']
        except:
            state = None
        else:
            state = state.lower()
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
        did = 0
        try:
            did = int(device_name)
        except:
            did = lookup_device(device_name)
        else:
            device_name = rev_lookup_device(did)
        if DEBUG: print("HASS control %s for state: %s, brightness %s, cct: %s, color: %s" % (device_name, state, brightness, cct, color))
        if (did > 0):
            if DEBUG: print("DEBUG: Recevied %s from MQTT > ID: %s" % (msg, did))
            if (state == "on"):
                cmd(did, 0xd0, ON_DATA)
            if (state == "off"):
                cmd(did, 0xd0, OFF_DATA)
            if (brightness is not None):
                hexdata = brightness
                try:
                    # Make sure we are dealing with int not string
                    i = int(hexdata)
                except:
                    i = 5
                if (i > 100 or i < 0):
                    print("ERROR: Lumnance value must be between 0 and 100")
                else:
                    data = i.to_bytes(1, 'big')
                    cmd(did, 0xd2, list(data))
            if (cct is not None):
                hexdata = cct
                ct = 0
                try:
                    # Make sure we are dealing with int not string
                    i = int(hexdata)
                except:
                    i = 0
                if i > 100:
                    if (i >= 153) and (i <= 500):
                        # We've got HASS color temp
                        ct = int(100 * (i - 153)/347)
                        ct = 100 - ct
                    # We've got Kelvin
                    elif (i < 1800 or i > 6500):
                        print("ERROR: CCT value must be between 1800K and 6500K")
                        return
                    else:
                        ct = int(100 * (i - 2700)/3800)
                else:
                    ct = i
                if ct < 0:
                    ct = 0
                if ct > 100:
                    ct = 100
                i = int(ct * 3800 / 100 + 2700)
                data = i.to_bytes(2, 'big')
                cmd(did, 0xf5, [0x10] + list(data))
                time.sleep(0.2)
                data = ct.to_bytes(1, 'big')
                cmd(did, 0xe2, [0x05] + list(data))
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
                    i = int(hexdata, 16)
                    if (i > 0xFFFFFF):
                        print("ERROR: RGB value must be 3 bytes")
                        return
                    else:
                        data = i.to_bytes(3, 'big')
                        cmd(did, 0xe2, [0x04] + list(data))
            hassct = None
            if cct is not None:
                ct = 100 - ct
                hassct = int(ct * 347 / 100 + 153)
            update_hass(device_name, state, brightness, hassct)


def cmd(device_addr, op_code, pars):
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
    if DEBUG: print("Process status %s" % status)


def process_config(conf):
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
    return True


def wifi_error():
    global status_led_1
    """Flash LED upon Wi-Fi connection failed"""
    print_status(WIFI_ERROR_FLAG)


def mqtt_error():
    global status_led_1
    """Flashes LED upon MQTT connection failure"""
    print_status(MQTT_ERROR_FLAG)


def ble_error():
    global status_led_2
    """Flashes LED upon communication problem with the BLE module"""
    print_status(BT_ERROR_FLAG)


def exit_mode():
    global LED1, LED2, status_led_1, status_led_2
    """Exit willingly"""
    m_WiFi_connected = do_connect(SSID, PASS) # If we want webrepl afterwards
    print_status(EXIT_FLAG)
    time.sleep(3)
    sys.exit(0)


def board_init():
    global LED1, LED2, KEY1, led1, led2, key1
    KEY1.init(mode=Pin.IN, pull=Pin.PULL_UP)
    key1 = KEY1
    LED1.init(mode=Pin.OUT)
    led1 = LED1
    led1.value(1)

m_rstcnt = 0
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


def displayInit():
  oled.fill(0)
  # oled.text(String,X-pixels,y-Pixels)
  wri_m.set_textpos(oled, 0, 0)  # verbose = False to suppress console output
  wri_m.printstring('BleuSky')
  # Show on display
  oled.show()


def print_progress(msg):
    wri_m.set_textpos(oled, 32, 0)  # verbose = False to suppress console output
    wri_m.printstring("                            ")
    wri_m.set_textpos(oled, 32, 0)  # verbose = False to suppress console output
    wri_m.printstring(msg)
    oled.show()


def print_status(statusflag):
    global m_systemstatus
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



if DEBUG: print("Connecting to Wi-Fi")
m_WiFi_connected = do_connect(SSID, PASS)

if m_WiFi_connected:
    print_progress("Wi-Fi OK")
    m_systemstatus = m_systemstatus & ~WIFI_ERROR_FLAG
    if DEBUG: print("Connecting to MQTT server at %s" % MQTT_SERVER)
    if MQTT_USER == '':
        MQTT_USER = None
    if MQTT_PASS == '':
        MQTT_PASS = None
    try:
        m_client = MQTTClient(MQTT_CLIENT_ID, MQTT_SERVER, user=MQTT_USER, password=MQTT_PASS)
    except:
        m_client = None
    if not initMQTT():
        mqtt_error()
    else:
        print_progress("MQTT OK")
        m_systemstatus = m_systemstatus & ~BT_ERROR_FLAG
else:
    wifi_error()


# Main()

print("INFO: Starting mini-gateway")
print_progress("Starting up")

try:
    os.mkdir(CACHEDIR)
except:
    print("WARNING: Cannot create dir %s" % CACHEDIR)

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

print_progress("                ")
print_status(m_systemstatus)
m_systemstatus = 0  # Reset system status so that new status can be updated within the loop
time.sleep(0.1)
if DEBUG: print("Entering infinte loop")
while True:
    # Processes MQTT network traffic, callbacks and reconnections. (Blocking)
    if m_client: m_client.check_msg()
    check_callbacks()
    check_reset()

