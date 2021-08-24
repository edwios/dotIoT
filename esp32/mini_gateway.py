DEBUG = False    # Global debug printing
USEOLED = False

import time
from umqtt.simple import MQTTClient
from machine import Pin, UART, PWM, reset, I2C
import network
import select
import esp32
import secrets
import config as config
import ujson
import os
import ubinascii
import sys
import json
import ntptime
#import esp
#esp.osdebug(None)
#import gc
#gc.collect()
from micropython import const

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
LED3 = config.LED3
LED4 = config.LED4
LED5 = config.LED5
LED6 = config.LED6
KEY1 = config.KEY1
NLED = config.N_LED

ON_DATA = [1, 1, 0]
OFF_DATA = [0, 1, 0]

WAIT_TIME = const(5)

m_WiFi_connected = False
led = []
pwmled = []
key1 = None
status_led = []
m_client = None
m_devices = None
m_expectedCallback = None
m_systemstatus = 0
m_cbreplies = []
Meshname = DEFAULT_MESHNAME
Meshpass = DEFAULT_MESHPWD

WIFI_ERROR_FLAG = const(1)
BT_ERROR_FLAG = const(2)
MQTT_ERROR_FLAG = const(4)
BTMOD_ERROR_FLAG = const(8)
ALT_CONFIG = const(16)
WIFI_CONNECTING = const(32)
MQTT_CONNECTING = const(64)
MESH_CONNECTING = const(128)
STATUS_TO_MESH = const(256)
STATUS_FROM_MESH = const(512)
EXIT_FLAG = const(0x7F)
#WIFI_ERROR_SYMB = "Wi-Fi"
#BT_ERROR_SYMB = "MESH"
#MQTT_ERROR_SYMB = "MQTT"
#BTMOD_ERROR_SYMB = "BTMOD"
#STATUS_TO_MESH_SYMB = ">>>Mesh"
#STATUS_FROM_MESH_SYMB = "Mesh>>>"
#EXIT_SYMB = "QUIT"

m_rdevstatuses = ["disabled", "enabled"]
m_rastrooffsets = ["before", "after"]
m_rastrooffsets1 = ["-", "+"]
m_rdevactions = ["off", "on", "scene"]
m_ralarmtypes = ["day", "week"]

def do_connect(ssid, pwd):
    """Connect to Wi-Fi network with 10s timeout"""
    import network
    sta_if = network.WLAN(network.STA_IF)
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
            # if DEBUG: print("Connected to Wi-Fi")
            WiFi_connected = True
        if WiFi_connected and DEBUG: print('Wi-Fi connected, network config:', sta_if.ifconfig())
        return WiFi_connected
    return True


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
    try:
        m_client.connect()   # Connect to MQTT broker
    except:
        print("ERROR: Cannot reach MQTT broker!")
        return False
#    m_client.subscribe(MQTT_SUB_TOPIC_ALL)
    m_client.subscribe(MQTT_SUB_TOPIC_CMD)
    m_client.subscribe(MQTT_PUB_TOPIC_STATUS)
    m_client.subscribe(MQTT_SUB_TOPIC_CONF)
    m_client.subscribe(MQTT_SUB_TOPIC_HASS_SET)
    m_client.publish(MQTT_PUB_TOPIC_STATUS, "Ready")
    return True


def _send_command(cmd: str = 'AT'):
    """Internal method to send AT commands to BLE module appending 0D0A to the end"""
    if DEBUG: print("DEBUG: Sending %s to BLE Module" % cmd)
    print_status(STATUS_TO_MESH)
#    cmd = cmd + '\r\n'
    m_uart.write(cmd)
    time.sleep(0.01)
    m_uart.write('\r\n')
    time.sleep(0.3)


def send_command(cmd: str = None):
    """Send AT command without AT+ prefix"""
    _send_command('AT+{:s}'.format(cmd))


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
    send_command('MESHNAME={:s}'.format(name))
    if not expect_reply('OK'):
#        print("ERROR in setting Mesh Name")
        return False
    send_command('MESHPWD={:s}'.format(pwd))
    if not expect_reply('OK'):
#        print("ERROR in setting Mesh Password")
        return False
    return True


def setMeshParams(name=DEFAULT_MESHNAME, pwd=DEFAULT_MESHPWD):
    global Mesh_Secrets
    """Set mesh parameters to BLE module and reset it to make it effective."""
    trials = 0
    while (not _setMeshParams(name, pwd)) and (trials < 4):
        time.sleep(0.5)
        trials = trials + 1
    if trials >= 4:
        print("ERROR in setting Mesh params")
        return False
    trials = 0
    while (not resetBLEModule()) and (trials < 4):
        time.sleep(0.5)
        trials = trials + 1
    if trials >= 4:
        print("ERROR: Cannot reset BLE module!")
        ble_error(1)
    else:
        ble_error(0)
    trials = 0
    while (not _setMeshParams(name, pwd)) and (trials < 4):
        time.sleep(0.5)
        trials = trials + 1
    if trials >= 4:
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
        pass
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
                devaddr = (tmp >> 8) + ((tmp & 0x0F) << 8)
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
                addr = (tmp >> 8) + ((tmp & 0x0F) << 8)
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
    if name is None:
        name = 'No name'
    return name


def mesh_send(dst=0x00, cmd=0xd0, data=[]):
    """Send to mesh using binary data"""
    length = len(data)
    if length == 0:
        return False
    atcommand = 'SEND={:x},{:d},{:02x}'.format(dst, length+1, cmd)
    for d in data:
        atcommand = atcommand + '{:02x}'.format(d)
    trials = 0
    send_command(atcommand)
    while (not expect_reply('OK')) and (trials < 4):
        time.sleep(0.1)
        send_command(atcommand)
        trials = trials + 1
    if trials >= 4:
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
    trials = 0
    send_command(atcommand)
    while (not expect_reply('OK')) and (trials < 4):
        time.sleep(0.1)
        send_command(atcommand)
        trials = trials + 1
    if trials >= 4:
        print("ERROR in sending to mesh")
        return False
    return True


def expect_reply(reply='OK'):
    """Expect from serial port some specific incoming"""
#    return True
    rpy = getReply(5)
    if rpy is None:
        return False
    for i in rpy:
        if i == reply:
            return True
    return False


def getReply(timeout=10):
    global poll, m_uart, m_cbreplies, DEBUG
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
                #if DEBUG: print("getReply: %s" % data)

    if data is not '':
        # Show the byte as 2 hex digits then in the default way
        # if DEBUG: print("DEBUG: received from BLE module: %s " % data)
        reply = []
        lines = data.split('\r\n')
        for line in lines:
            if line is not '':
                # Todo: Push +DATA reeplies to stack
                if line.startswith('+DATA'):
                    m_cbreplies.append(line)
                else:
                    reply.append(line)
        if DEBUG: print("DEBUG: received %d lines of reply as %s" % (len(reply), reply))
        if DEBUG: print("DEBUG: received %d lines of callbacks as %s" % (len(m_cbreplies), m_cbreplies))
        return reply


def check_callbacks():
    global m_cbreplies, DEBUG
    getReply(3)
    # Todo: how not to eat OK's from getReply?
    if len(m_cbreplies) == 0:
        return
    while len(m_cbreplies) > 0:
        reply = m_cbreplies.pop()
        if reply.startswith('+DATA'):
            try:
                devaddrstr, lengthstr, callback = reply[6:].split(',')
            except:
                devaddrstr = None
            if devaddrstr is not None:
                try:
                    length = int(lengthstr)
                except:
                    length = 0
                if DEBUG: print("DEBUG: Got call back from %s with %s" % (devaddrstr, callback[:length*2]))
                print_status(STATUS_FROM_MESH)
                try:
                    t = ubinascii.unhexlify(devaddrstr)
                except:
                    devaddr = -1
                else:
                    devaddr = t[0] * 256 + t[1]
                if (len(callback) != length * 2) or (length == 0) or (devaddr == -1):
                    print("ERROR: Corrupted callback packet found")
                else:
                    process_callback(devaddr, callback)


def process_callback(devaddr, callback):
    global m_client, m_rdevactions, m_ralarmtypes, m_rdevstatuses,  DEBUG, s1, s2, m_expectedCallback
    gc.collect()
    mesg = {}
    if DEBUG: print("Processing call back from %04x" % devaddr)
    name = rev_lookup_device(devaddr)
    if (name is None) or (callback is None):
        print("ERROR: process_callback(): cannot find device name with address %d or no callback is given" % devaddr)
        return
    if ((len(callback) % 2) != 0) or (len(callback) == 0):
        print("ERROR: process_callback(): corrupted callback %s from %s" % (callback, name))
        return
    try:
        data = ubinascii.unhexlify(callback)
    except:
        print("ERROR: process_callback(): corrupted callback %s from %s" % (callback, name))
        return
    if (data is None):
        return   
    if len(data) == 0:
        return
    opcode = data[0]   
    mesg['device_name'] = name
    mesg['device_id'] = devaddr
    if opcode == 0xDC:
        # Status notify report
        if DEBUG: print("process_callback(): Got status call back from %s (%04x)" % (name, devaddr))
        bgt = data[1]
        cct = data[2]
        state = None
        if bgt is not None:
            if bgt > 0:
                state = 'on'
            else:
                state = 'off'
            mesg['state'] = state
            mesg['brightness'] = bgt
        if cct is not None:
            mesg['cct'] = cct
        update_hass(name, state, bgt, cct)
    elif opcode == 0xDB:
        # User_all notify report
        # +DATA:DB1102006464FF
        bgt = data[5]
        state = None
        if bgt is not None:
            if bgt > 0:
                state = 'on'
            else:
                state = 'off'
            mesg['state'] = state
            mesg['brightness'] = bgt
        update_hass(name, state, bgt, None)
    elif opcode == 0xE7:
        # +DATA:0001,23,E71102A50192097F170A0000
        cbs = data[3]
        if cbs == 0xA5:
            # alarm_get() return
            alrm_index = data[4]
            alrm_event = data[5]
            alrm_action = alrm_event & 0x0f
            alrm_actionStr = m_rdevactions[alrm_action]
            alrm_type = (alrm_event & 0x70) >> 4
            alrm_typeStr = m_ralarmtypes[alrm_type]
            alrm_status = (alrm_event & 0x80) >> 7
            alrm_statusStr = m_rdevstatuses[alrm_status]
            alrm_month = data[6]
            alrm_dayom = data[7]
            if (alrm_type == 0):
                alrm_dayomStr = '{:02d}/{:02d}'.format(alrm_month, alrm_dayom)
            else:
                alrm_dayomStr = '{:07b}'.format(alrm_dayom)
                week = 'smtwtfs'
                weekstr = ''
                for i in range(7):
                    if alrm_dayomStr[6-i] == '1':
                        weekstr = weekstr + week[i].upper()
                    else:
                        weekstr = weekstr + week[i]
                alrm_dayomStr = weekstr
            alrm_hour  = data[8]
            alrm_min   = data[9]
            alrm_sec   = data[10]
            alrm_scene = data[11]
            alrm_sceneStr = '{:d}'.format(alrm_scene)
            alrm_indexStr = '{:d}'.format(alrm_index)
            timeStr = '{:02d}:{:02d}:{:02d}'.format(alrm_hour, alrm_min, alrm_sec)
            #if DEBUG: print("%s INFO: %s has timer set to turn %s %s %s %s %s at %s and is %s" % (time.strftime('%F %H:%M:%S'), callbackDeviceName, actionStr, offset_hStr, offset_mStr, offsettypeStr, rtype, timeStr, statusStr))
            mesg.update({"type":"timer", "time":timeStr, "scene_index":alrm_sceneStr, "alarm_index":alrm_indexStr, "alarm_type":alrm_typeStr, "alarm_status":alrm_statusStr, "action":alrm_actionStr, "alarm_days":alrm_dayomStr})
    elif opcode == 0xE9 or opcode == 0xE4:
        # Time get
        year = data[3] + (data[4] << 8)
        month = data[5]
        day = data[6]
        date_str = '{:d}-{:02d}-{:02d}'.format(year, month, day)
        hr = data[7]
        mi = data[8]
        sc = data[9]
        time_str = '{:02d}:{:02d}:{:02d}'.format(hr, mi, sc)
        mesg['time'] = time_str
        mesg['date'] = date_str
        if opcode == 0xE9:
            mesg['type'] = 'get_time'
        else:
            mesg['type'] = 'set_time'
    elif opcode == 0xEB:
        # Astro timers
        cbs = data[4]       # data[3] is fixed to 0x01
        if cbs == 0x80:     # Countdown timer, [enable, HH, MM, hh, mm]
            ena = data[5]
            state = None
            if ena == 1:
                state = "enabled"
            else:
                state = "disabled"
            HH = data[6]
            MM = data[7]
            hh = data[8]
            mm = data[9]
            mesg.update({'type':'countdown', 'state':state, 'config':{'hour':HH, 'minute':MM}, 'remain':{'hour':hh, 'minute':mm}})
        elif cbs == 0x81:     # astro time geo settings
            if (data[5] == 0):
                meridian = 'East'
            else:
                meridian = 'West'
            long_deg = data[6]
            long_min = data[7]/60.0
            longstr = '{:0.6f}'.format(long_deg + long_min)
            if (data[8] == 0):
                equator = 'South'
            else:
                equator = 'North'
            lat_deg = data[9]
            lat_min = data[10]/60.0
            latstr = '{:0.6f}'.format(lat_deg + lat_min)
            if (data[11] == 0):
                tz_ew = 'East'
            else:
                tz_ew = 'West'
            tz = data[12]
            mesg.update({"type":"astro", "meridian":meridian, "longitute":longstr, "equator":equator, "latitude":latstr, "timezone_dir":tz_ew, "timezone":tz})
        elif cbs == 0x82 or cbs == 0x83:     # Got Sunrise/Sunset time report
            time_h = data[5]
            time_m = data[6]
            if cbs == 0x82:
                rtype = "Sunrise"
            elif cbs == 0x83:     # Got Sunset time
                rtype = "Sunset"
            if data[14] != 0xFF:
                statusStr = m_rdevstatuses[data[7]]
                actionStr = m_rdevactions[data[8]]
                offsettypeStr = m_rastrooffsets[data[9]]
                offset_h = data[10]
                offset_m = data[11]
                # offset_hStr = '{:02d} hour'.format(offset_h)
                # offset_mStr = '{:02d} min'.format(offset_m)
                timeStr = '{:02d}:{:02d}'.format(time_h, time_m)
                offsetStr = '{:02d}:{:02d}'.format(offset_h, offset_m)
                mesg.update({"type":"astro", rtype:timeStr, "offset":offsetStr, "position":offsettypeStr, "action":actionStr, "status":statusStr})
            else:
                mesg['type'] = 'astro'
        elif cbs == 0x84:
            # Get DST
            summer_start_month = data[5]
            summer_start_day = data[6]
            summer_start_str = '{:02d}/{:02d}'.format(summer_start_day, summer_start_month)
            if (data[7] == 0):
                summer_comp = -1
            else:
                summer_comp = 1
            summer_offset = summer_comp * data[8]
            winter_start_month = data[9]
            winter_start_day = data[10]
            winter_start_str = '{:02d}/{:02d}'.format(winter_start_day, winter_start_month)
            if (data[11] == 0):
                winter_comp = -1
            else:
                winter_comp = 1
            winter_offset = winter_comp * data[12]
            mesg.update({"summer_start_d_m":summer_start_str, "summer_offset":summer_offset, "winter_start_d_m":winter_start_str, "winter_offset":winter_offset})
        elif cbs == 0x85:     # Calculated astro time settings
            # +DATA:000b,23,EB110201850000000000000000000007000003B85B7FFD   
            # We look at Adjusted data only     
            sunrise_h_dst = data[9]
            sunrise_m_dst = data[10]
            sunset_h_dst = data[11]
            sunset_m_dst = data[12]
#            sunrise_h_dst = data[5]
#            sunrise_m_dst = data[6]
#            sunset_h_dst = data[7]
#            sunset_m_dst = data[8]
            sunrise_dst = '{:02d}:{:02d}'.format(sunrise_h_dst, sunrise_m_dst)
            sunset_dst = '{:02d}:{:02d}'.format(sunset_h_dst, sunset_m_dst)
            if DEBUG: print("INFO: Sunrise at %02d:%02d, sunset at %02d:%02d" % (sunrise_h_dst, sunrise_m_dst, sunset_h_dst, sunset_m_dst))
            mesg.update({"sunrise":sunrise_dst, "sunset":sunset_dst})
        else:
            if DEBUG: print("Unsupported call back subcommand %02X (%02X)" % (opcode, cbs))
            return
    elif opcode == 0xC1:
        #c1110201e1ppppppppeeeeeeee
        cbs = data[4]
        if cbs == 0xE1:
            # Get_MajorUsage
            r1or2 = data[3]    #first or second report
            if r1or2 == 1:
                # First report contains the power and energy usages
                kwh = (data[8]<<24) + (data[7]<<16) + (data[6]<<8) + data[5]
                wattage = (data[12]<<24) + (data[11]<<16) + (data[10]<<8) + data[9]
                mesg.update({"type":"power", "power":{"value":wattage, "unit":"W"}, "energy":{"value":kwh, "unit":"kWh"}})
            if r1or2 == 2:
                voltage = (data[8]<<24) + (data[7]<<16) + (data[6]<<8) + data[5]
                current = (data[12]<<24) + (data[11]<<16) + (data[10]<<8) + data[9]
                mesg.update({"type":"electricity", "voltage":{"value":voltage, "unit":"V"}, "current":{"value":current, "unit":"A"}})
            update_hass2(mesg)
    elif m_expectedCallback is not None:
        if len(m_expectedCallback) > 1:
            """
            Todo:
            m_expectedCallback shall be a stack consists of the array [device id, opcode, subcommand, pars]
            As more and more opcode callbacks are supported, m_expectedCallback will have mush less significant
            """
            if (opcode == m_expectedCallback[1]):
                if DEBUG: print("Call back subcommand: %02X" % opcode)
                if DEBUG: print("Call back pars: {:s}".format(callback[2:]))
                mesg.update({"opcode":'{:02X}'.format(opcode), "pars":callback[2:26], "type":"callback"})
                m_expectedCallback = None
    else:
        if DEBUG: print("Unsupported call back opcode %02X" % opcode)
        return
    mesg['timestamp'] = str(time.time())
    update_status_mqtt(mesg)
    gc.collect()


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
            cct = 100 - cct
            hasscct = int(cct * 347 / 100 + 153)
        hass_mesg['color_temp'] = hasscct
    hass_mesg['timestamp'] = str(time.time())
    try:
        if m_client:
            m_client.publish(hass_state_topic, json.dumps(hass_mesg).encode('utf-8'))
    except:
        print("ERROR: update_hass(hass_mesg) has invalid content")
        return


def update_hass2(mesg):
    global DEBUG, m_client, MQTT_PUB_TOPIC_HASS_PREFIX
    name = mesg['device_name']
    if name is None:
        return
    if DEBUG: print("update_hass2(): Pub status for %s" % (name))
    hass_state_topic = '{:s}{:s}'.format(MQTT_PUB_TOPIC_HASS_PREFIX, name)
    mesg['timestamp'] = str(time.time())
    try:
        if m_client:
            m_client.publish(hass_state_topic, json.dumps(mesg).encode('utf-8'))
    except:
        print("ERROR: update_hass(mesg) has invalid content")
        return


def update_status_mqtt(mesg):
    global DEBUG, MQTT_PUB_TOPIC_STATUS, m_client
    if mesg is None:
        return
    if mesg == {}:
        return
    topic = MQTT_PUB_TOPIC_STATUS
    try:
        jstr = json.dumps(mesg)
    except:
        print("ERROR: update_status_mqtt(mesg) has invalid mesg")
        return
    if DEBUG: print("DEBUG: JSON to publish %s" % jstr)
    if m_client:
        m_client.publish(topic, jstr.encode('utf-8'))


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
    global DEBUG, Meshname, Meshpass, m_expectedCallback
    if DEBUG: print("Process command %s" % mqttcmd)
    print_progress(mqttcmd[:16])
    if mqttcmd is not '':
        if '/' not in mqttcmd:
            if (mqttcmd == "debug"):
                print("Info: Debug on")
                DEBUG = True
                return
            elif (mqttcmd == "nodebug"):
                print("Info: Debug off")
                DEBUG = False
                return
            elif (mqttcmd == "refresh"):
                setMeshParams(name=Meshname, pwd=Meshpass)
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
            elif (hcmd == "get_geo"):
                cmd(did, 0xea, [0x08, 0x81])
                m_expectedCallback = [did, 0xeb, 0x81]       
            elif (hcmd == "get_sunrise"):
                cmd(did, 0xea, [0x08, 0x82])
                m_expectedCallback = [did, 0xeb, 0x82]
            elif (hcmd == "get_sunset"):
                cmd(did, 0xea, [0x08, 0x83])
                m_expectedCallback = [did, 0xeb, 0x83]
            elif (hcmd == "get_dst"):
                cmd(did, 0xea, [0x08, 0x84])
                m_expectedCallback = [did, 0xeb, 0x84]
            elif (hcmd == "get_astro"):
                cmd(did, 0xea, [0x08, 0x85])
                m_expectedCallback = [did, 0xeb, 0x85]
            elif (hcmd == "get_time"):
                cmd(did, 0xe8, [0x10])
                m_expectedCallback = [did, 0xe9, 0x00]
            elif (hcmd == "get_power"):
                cmd(did, 0xc0, [0x08, 0xe1])
                m_expectedCallback = [did, 0xc1, 0xe1]
            elif (hcmd == "get_status"):
                cmd(did, 0xda, [0x10])
                m_expectedCallback = [did, 0xdb, 0x00]
            elif (hcmd == "get_countdown"):
                cmd(did, 0xea, [0x10, 0x80])
                m_expectedCallback = [did, 0xeb, 0x01]
            elif (hcmd == "get_timer"):
                if (hexdata != ''):
                    try:
                        i = int(hexdata)
                    except:
                        print("ERROR: invalid parameters")
                    if (i > 16):
                        print("ERROR: Only 16 timers")
                    else:
                        data = i.to_bytes(1, 'big')
                        cmd(did, 0xe6, [0x10] + list(data))
                        m_expectedCallback = [did, 0xe7, 0xa5]
            elif (hcmd == "get_scene"):
                if (hexdata != ''):
                    try:
                        i = int(hexdata)
                    except:
                        print("ERROR: invalid parameters")
                    if (i > 16):
                        print("ERROR: Only 16 scenes")
                    else:
                        data = i.to_bytes(1, 'big')
                        cmd(did, 0xc0, [0x10] + list(data))
                        m_expectedCallback = [did, 0xc1, 0x00]
            elif (hcmd == "del_scene"):
                if (hexdata != ''):
                    try:
                        i = int(hexdata)
                    except:
                        print("ERROR: invalid parameters")
                    if (i > 16):
                        print("ERROR: Only 16 scenes")
                    else:
                        data = i.to_bytes(1, 'big')
                        cmd(did, 0xee, [0x00] + list(data))
                        m_expectedCallback = None
            elif (hcmd == "set_time"):
                if (hexdata == '' or hexdata == 'now'):
                    (yyyy,mo,dd,hh,mm,ss,_,_) = time.localtime()
                if (hexdata != ''):
                    # Parse date time string yyyy,mo,dd,hh,mm,ss
                    try:
                        (yyyy,mo,dd,hh,mm,ss) = hexdata.split(',')
                    except:
                        print("ERROR: invalid parameters, yyyy,mo,dd,hh,mm,ss")
                        return
                settimeStr(did, yyyy,mo,dd,hh,mm,ss)
            elif (hcmd == "set_dst"):
                if (hexdata != ''):
                    # Parse DST string Bmm,Bdd,Emm,Edd,Offset,Enabled
                    try:
                        (bmm, bdd, emm, edd, ofs, ena) = hexdata.split(',')
                    except:
                        print("ERROR: invalid parameters, Bmm,Bdd,Emm,Edd,Offset (int),Enabled (0|1)")
                    else:
                        setdst(did, bmm, bdd, emm, edd, ofs, ena)
            elif (hcmd == "set_countdown"):
                # Set Countdown F5 11 02 06 HH MM
                if (hexdata != ''):
                    try:
                        i = int(hexdata)
                    except:
                        i = 1
                    if i == 0:
                        # 0 means disable countdown
                        cmd(did, 0xf5, [0x07, 0x00])
                    else:
                        hh = i // 60
                        mm = i % 60
                        cmd(did, 0xf5, [0x06, hh, mm])
                        time.sleep(0.1)
                        cmd(did, 0xf5, [0x07, 0x01])
                    m_expectedCallback = None
            elif (hcmd == "set_group"):
                # Set Countdown D7 11 02 01 LL HH
                if (hexdata != ''):
                    try:
                        if (hexdata[:2] == '0x' or hexdata[:2] == '0X'):
                            i = int(hexdata, 16)
                        else:
                            i = int(hexdata)
                    except:
                        i = 0x8001
                    data = i.to_bytes(2, 'little')
                    cmd(did, 0xD7, [0x01] + list(data))
                    m_expectedCallback = None
            elif (hcmd == "del_group"):
                # Set Countdown D7 11 02 00 LL HH
                if (hexdata != ''):
                    try:
                        if (hexdata[:2] == '0x' or hexdata[:2] == '0X'):
                            i = int(hexdata, 16)
                        else:
                            i = int(hexdata)
                    except:
                        i = 0x8001
                    data = i.to_bytes(2, 'little')
                    cmd(did, 0xD7, [0x00] + list(data))
                    m_expectedCallback = None
            elif (hcmd == "set_remote"):
                # Set Countdown F6 11 02 LL HH
                if (hexdata != ''):
                    try:
                        if (hexdata[:2] == '0x' or hexdata[:2] == '0X'):
                            i = int(hexdata, 16)
                        else:
                            i = int(hexdata)
                    except:
                        i = 0x8001
                    data = i.to_bytes(2, 'little')
                    cmd(did, 0xF6, list(data))
                    m_expectedCallback = None
            elif (hcmd == "power"):
                cmd(did, 0xC0, [0x08, 0xE1])
                m_expectedCallback = None
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
                        m_expectedCallback = [did, int(t[0])]
                    except:
                        print("ERROR: Illegal callback in raw %s" % hexlist[1])
                        m_expectedCallback = None
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
            elif (hcmd == 'at'):
                if hexdata != '':
                    c = hexdata.upper()
                    send_command(c)
                    r = getReply()
                    print('AT command returned: {:s}'.format(r))


def isDst(day, month, dow):
    if (month < 3) or (month > 10):
        return False
    if (month > 3) and (month < 10):
        return True

    previousSunday = day - dow

    if (month == 3):
        return (previousSunday >= 25)
    if (month == 10):
        return (previousSunday < 25)

    return False  # this line never gonna happend



def setdst(did, bmm, bdd, emm, edd, offset, enabled):
    try:
        bm = int(bmm)
        bd = int(bdd)
        em = int(emm)
        ed = int(edd)
        of = int(offset)
        en = int(enabled)
    except:
        return
    ofs = 1 # 1 = +ve, 0 = -ve
    if of < 0:
        ofs = 0
        of = abs(of)
    data = [en, bm, bd, ofs, of, em, ed, 1 - ofs, 0]
    # Let's do it by setting the time to ALL devices (thus 0xFFFF)
    cmd(did, 0xf5, [0x0a] + list(data))
    


def settimeStr(did, yyyy='0',mo='0',dd='0',hh='0',mm='0',ss='0'):
    try:
        y = int(yyyy)
        m = int(mo)
        d = int(dd)
        h = int(hh)
        n = int(mm)
        s = int(ss)
    except:
        return
    settime(did, y, m, d, h, n, s)


def settime(did, yyyy=0,mo=0,dd=0,hh=0,mm=0,ss=0):
    if (yyyy <= 1970):
        # Set current time to device
        (yyyy,mo,dd,hh,mm,ss,_,_) = time.localtime()
    yh = yyyy // 256
    yl = yyyy % 256
    data = [yl, yh, mo, dd, hh, mm, ss]
    # Let's do it by setting the time to ALL devices (thus 0xFFFF)
    cmd(did, 0xe4, data)


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
            hassct = 0
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
    pass


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


def wifi_error(e):
    """Flash LED upon Wi-Fi connection failed"""
    if e == 1:
        print_status(WIFI_ERROR_FLAG)
    elif e == 2:
        print_status(WIFI_CONNECTING)
    else:
        print_status(~WIFI_CONNECTING)
        print_status(~WIFI_ERROR_FLAG)


def mqtt_error(e):
    """Flashes LED upon MQTT connection failure"""
    if e == 1:
        print_status(MQTT_ERROR_FLAG)
    else:
        print_status(~MQTT_ERROR_FLAG)


def ble_error(e):
    """Flashes LED upon communication problem with the BLE module"""
    if e == 1:
        print_status(BT_ERROR_FLAG)
    else:
        print_status(~BT_ERROR_FLAG)

def blemodu_error(e):
    """Flashes LED upon communication problem with the BLE module"""
    if e == 1:
        print_status(BTMOD_ERROR_FLAG)
    else:
        print_status(~BTMOD_ERROR_FLAG)



def exit_mode():
    """Exit willingly"""
    global m_WiFi_connected, SSID, PASS
    m_WiFi_connected = do_connect(SSID, PASS) # If we want webrepl afterwards
    print_status(EXIT_FLAG)
    time.sleep(3)
    sys.exit(0)


def board_init():
    global LED1, LED2, LED3, LED4, LED5, LED6, KEY1, NLED, led, pwmled, key1, status_led
    KEY1.init(mode=Pin.IN, pull=Pin.PULL_UP)
    key1 = KEY1
    LED1.init(mode=Pin.OUT)
    led.append(LED1)
    LED2.init(mode=Pin.OUT)
    led.append(LED2)
    LED3.init(mode=Pin.OUT)
    led.append(LED3)
    LED4.init(mode=Pin.OUT)
    led.append(LED4)
    LED5.init(mode=Pin.OUT)
    led.append(LED5)
    LED6.init(mode=Pin.OUT)
    led.append(LED6)
    for i in range(0, NLED):
        pwmled.append(None)
        status_led.append(None)
        rmt = esp32.RMT(i, pin=led[i])
        rmt.deinit()
        pwm = PWM(led[i])
        pwm.deinit()
        led[i].init(mode=Pin.OUT)
        led[i].value(1)

m_rstcnt = 0
def check_reset():
    global m_rstcnt, key1, DEBUG
    if key1.value() == 0:
#        print_progress("Reset/Exit?")
        if m_rstcnt == 0:
            m_rstcnt = time.ticks_ms()  # start timer at first keypress
    else:
        if m_rstcnt == 0:
            return  # no key pressed so far
        # key released, check elapsed time on keypress
        t = time.ticks_ms() - m_rstcnt
        if DEBUG: print("Elapse time: %f" % t)
        if t > 50 and t < 1000:
            # perform reset only when key is pressed down for a while (debounce) but not too long (exit)
            print_status(0)
            reset()
        if t > 5:
            # Quit when key hold for > 5s
            exit_mode()
        # Key released but not meant for reset, clear timer
        m_rstcnt = 0


def displayInit():
    return


def print_progress(msg):
    if DEBUG: print("Progress: %s" % msg)
    return


def print_status(statusflag):
    global m_systemstatus, DEBUG
    if DEBUG: print("print_status(): flag = %d" % statusflag)
    st = statusflag
    if (not USEOLED) and ((statusflag == STATUS_FROM_MESH) or (statusflag == STATUS_TO_MESH)):
        return
    if st !=  EXIT_FLAG:
        if st < 0:
            m_systemstatus = m_systemstatus & st
        else:
            m_systemstatus = m_systemstatus | st
        st = m_systemstatus

    if DEBUG: print("print_status(): st = %d" % st)
    if st & WIFI_ERROR_FLAG:
        error_indicator(1, 1)
    elif st & WIFI_CONNECTING:
        error_indicator(1, 1)
    else:
        error_indicator(1)
    if st & BT_ERROR_FLAG:
        error_indicator(2, 1)
    else:
        error_indicator(2)
    if st & MQTT_ERROR_FLAG:
        error_indicator(1, 2)
    else:
        pass
    if st & BTMOD_ERROR_FLAG:
        error_indicator(2, 3)
    else:
        pass
    if st & ALT_CONFIG:
        pass
    else:
        error_indicator(1)
    if st == 0:
        error_indicator(1)
    if st == EXIT_FLAG:
        error_indicator(0, 1)

def error_indicator(n, flashmode=0, onoff=1):
    global led, status_led, pwmled, DEBUG
#    if DEBUG: print("error_indicator(): n = %d, flashmode = %d, onoff = %d" % (n, flashmode, onoff))
    if n > 0:
        n = n - 1
        led[n].value(1)
        if flashmode == 0:
                if status_led[n] is not None:
#                    if DEBUG: print("error_indicator(): resetting RMT/PWM for LED %d" % n)
                    status_led[n].loop(False)
                    status_led[n].deinit()
                if pwmled[n] is not None:
                    pwmled[n].deinit()
                    pwmled[n] = None
                pwmled[n] = PWM(led[n], freq=20000, duty=1023-200*onoff)
        else:
            if status_led[n] is not None:
                status_led[n].deinit()
                status_led[n] = None
            if pwmled[n] is not None:
                pwmled[n].deinit()
                pwmled[n] = None
            status_led[n] = esp32.RMT(n, pin=led[n], clock_div=255)
            status_led[n].loop(True)
        if flashmode == 1:
            if status_led[n] is not None:
                status_led[n].write_pulses((32767, 1, 32767, 8192, 1), start=1)
        elif flashmode == 2:
            if status_led[n] is not None:
                status_led[n].write_pulses((16384, 1, 16384, 16384, 1), start=0)
        elif flashmode == 3:
            if status_led[n] is not None:
                status_led[n].write_pulses((32767, 1, 8192, 8192, 1), start=0)
    else:
        if flashmode == 0:
            for i in range(0, NLED):
                if status_led[i] is not None:
                    status_led[i].loop(False)
                    status_led[i].deinit()
                    status_led[i] = None
                #led[i].init(mode=Pin.OUT)
                if pwmled[i] is not None:
                    pwmled[i].deinit()
                    pwmled[i] = None
                if i % 2 == 0:
                    pwmled[i] = PWM(led[i], freq=20000, duty=1023)
                else:
                    pwmled[i] = PWM(led[i], freq=20000, duty=1023-200*onoff)
        else:
            # Exiting
            for i in range(0, NLED):
                if status_led[i] is not None:
                    status_led[i].loop(False)
                    status_led[i].deinit()
                    status_led[i] = None
                if pwmled[i] is not None:
                    pwmled[i].deinit()
                    pwmled[i] = None
                led[i].init(mode=Pin.OUT)
                led[i].value(1)




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
#error_indicator(2, 0)

if released:
    """Button pressed during boot, change to config #2"""
    if DEBUG: print("DEBUG: Switch to alt config")
    import config_alt
    import secrets_alt

    print_status(ALT_CONFIG)

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
    print_status(~ALT_CONFIG)

if DEBUG: print("Connecting to Wi-Fi")
wifi_error(2)
m_WiFi_connected = do_connect(SSID, PASS)

if m_WiFi_connected:
    print_progress("Wi-Fi OK")
    wifi_error(0)
    ntptime.settime()
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
        mqtt_error(1)
    else:
        print_progress("MQTT OK")
        m_systemstatus = m_systemstatus & ~BT_ERROR_FLAG
        mqtt_error(0)
else:
    if DEBUG: print("Error connecting to Wi-Fi")
    wifi_error(1)


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
m_uart = UART(2, tx=18, rx=4)                         # init with given baudrate
m_uart.init(115200, bits=8, parity=None, stop=1, timeout=10)

poll = select.poll()
poll.register(m_uart, select.POLLIN)

if not checkBLEModule():
    print("ERROR: Cannot find BLE module!")
    blemodu_error(1)
else:
    print("Found BLE module")
    blemodu_error(0)
    

atcmd = ''
Opcode = ''

setMeshParams(name=Meshname, pwd=Meshpass)

#m_systemstatus = 0  # Reset system status so that new status can be updated within the loop
print_status(m_systemstatus)
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
        m_WiFi_connected = do_connect(SSID, PASS)
        if not m_WiFi_connected:
            wifi_error(1)
            print("ERROR: Cannot connect back to Wi-Fi")
        else:
            ntptime.settime()
            try:
                m_client = MQTTClient(MQTT_CLIENT_ID, MQTT_SERVER, user=MQTT_USER, password=MQTT_PASS)
            except:
                m_client = None
            time.sleep(5)   # Wait 5s to make sure the damn network is ready
            if not initMQTT():
                mqtt_error(1)
            else:
                print_progress("MQTT OK")
                m_systemstatus = m_systemstatus & ~BT_ERROR_FLAG
                mqtt_error(0)
    check_callbacks()
    check_reset()

