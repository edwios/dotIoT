import time
from umqtt.simple import MQTTClient
from machine import Pin, UART, PWM
import network
import select
import esp32
import secrets
import ujson
import os

DEBUG = True    # Global debug printing

DEFAULT_MESHNAME = secrets.DEFAULT_MESHNAME
DEFAULT_MESHPWD = secrets.DEFAULT_MESHPWD
SSID = secrets.SSID
PASS = secrets.PASS

DEFAULT_DSTADDR = "FFFF"
DEFAULT_OPCODE  = "D0"
DEFAULT_PARS    = "010100"

# MQTT_SERVER = '192.168.1.143'  # MQTT Server Address (Change to the IP address of your Pi)
MQTT_SERVER = '10.0.1.250'  # MQTT Server Address (Change to the IP address of your Pi)
MQTT_CLIENT_ID = 'BlueSky'
MQTT_TOPIC = 'sensornet/#'

CACHEDIR = 'cache'
DEVICE_CACHE_NAME = 'devices.json'
MESH_SECRTES_NAME = 'meshsecrets.json'
Device_Cache = CACHEDIR + '/' + DEVICE_CACHE_NAME
Mesh_Secrets = CACHEDIR + '/' + MESH_SECRTES_NAME

LED1 = Pin(33)
LED2 = Pin(32)

ON_DATA = [1, 1, 0]
OFF_DATA = [0, 1, 0]

m_WiFi_connected = False
wifierr = None
m_client = None
m_devices = None
led1 = PWM(Pin(33), freq=20000, duty=1023)
led2 = PWM(Pin(32), freq=20000, duty=1023)
Meshname = DEFAULT_MESHNAME
Meshpass = DEFAULT_MESHPWD

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
    if (t == 'sensornet/command'):
        process_command(m)
    if (t == 'sensornet/status'):
        process_status(m)
    if (t == 'sensornet/config'):
        process_config(m)


def initMQTT():
    """Initialise MQTT client and connect to the MQTT broker. """
    global m_client
    if not m_client:
        print("ERROR: No MQTT connection to init for")
        return False
    m_client.set_callback(on_message)  # Specify on_message callback
    m_client.connect()   # Connect to MQTT broker
    m_client.subscribe('sensornet/#')
    return True


def _send_command(cmd: str = 'AT'):
    """Internal method to send AT commands to BLE module appending 0D0A to the end"""
    if DEBUG: print("DEBUG: Sending %s to BLE Module" % cmd)
    m_uart.write(cmd + '\r\n')
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
    else:
        led2.duty(896)
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
        if DEBUG: print("DEBUG: received from BLE module: %s " % data)
        reply = []
        lines = data.split('\r\n')
        for line in lines:
            if line is not '':
                reply.append(line)
        if DEBUG: print("DEBUG: received %d lines of text as %s" % (len(reply), reply))
        return reply


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


def cmd(device_addr, op_code, pars):
    """Properly format mesh command before sending to mesh"""
    if DEBUG: print("Sending to %s op code %s and pars %s" % (device_addr, op_code, pars))
    Dstdev = '{:d}'.format(device_addr)
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
    """Flash LED upon Wi-Fi connection failed"""
    wifierr = esp32.RMT(0, pin=LED1, clock_div=255)
    wifierr.loop(True)
    wifierr.write_pulses((16384, 1, 16384, 16384, 1), start=0)


def mqtt_error():
    """Flashes LED upon MQTT connection failure"""
    wifierr.write_pulses((32767, 1, 32767, 8192, 1), start=1)


def ble_error():
    """Flashes LED upon communication problem with the BLE module"""
    r = esp32.RMT(1, pin=LED2, clock_div=255)
    r.loop(True)
    r.write_pulses((16384, 1, 16384, 16384, 1), start=0)


if DEBUG: print("Connecting to Wi-Fi")
m_WiFi_connected = do_connect(SSID, PASS)

if m_WiFi_connected:
    if DEBUG: print("Connecting to MQTT server at %s" % MQTT_SERVER)
    led1.duty(896)
    try:
        m_client = MQTTClient(MQTT_CLIENT_ID, MQTT_SERVER)
    except:
        m_client = None
    if not initMQTT():
        mqtt_error()
else:
    wifi_error()


# Main()

print("INFO: Starting mini-gateway")
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
m_uart = UART(2, tx=18, rx=4)                         # init with given baudrate
m_uart.init(115200, bits=8, parity=None, stop=1, timeout=10)

poll = select.poll()
poll.register(m_uart, select.POLLIN)

if not checkBLEModule():
    print("ERROR: Cannot find BLE module!")

atcmd = ''
Opcode = ''

setMeshParams(name=Meshname, pwd=Meshpass)

if DEBUG: print("Entering infinte loop")
while True:
    # Processes MQTT network traffic, callbacks and reconnections. (Blocking)
    if m_client: m_client.check_msg()
    getReply(3)
