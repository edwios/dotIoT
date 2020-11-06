import time
from umqtt.simple import MQTTClient
from machine import Pin, UART, PWM
import network
import select
import esp32
import secrets

DEBUG=False

DEFAULT_MESHNAME = secrets.DEFAULT_MESHNAME
DEFAULT_MESHPWD = secrets.DEFAULT_MESHPWD
SSID = secrets.SSID
PASS = secrets.PASS

DEFAULT_DSTADDR = "FFFF"
DEFAULT_OPCODE  = "D0"
DEFAULT_PARS    = "010100"

#MQTT_SERVER = '192.168.1.143'  # MQTT Server Address (Change to the IP address of your Pi)
MQTT_SERVER = '10.0.1.250'  # MQTT Server Address (Change to the IP address of your Pi)
MQTT_CLIENT_ID = 'BlueSky'
MQTT_TOPIC = 'sensornet/#'

LED1 = Pin(33)
LED2 = Pin(32)

ON_DATA = [1,1,0]
OFF_DATA = [0,1,0]

m_WiFi_connected = False
m_client = None
led1 = PWM(Pin(33), freq=20000, duty=1023)
led2 = PWM(Pin(32), freq=20000, duty=1023)

def do_connect(ssid, pwd):
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

# Callback fires when a published message is received.
def on_message(topic, msg):
	# Decode temperature and humidity values from binary message paylod.
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
    global m_client
    if not m_client:
        print("ERROR: No MQTT connection to init for")
        return False
    m_client.set_callback(on_message)  # Specify on_message callback
    m_client.connect()   # Connect to MQTT broker
    m_client.subscribe('sensornet/#')
    return True

def _send_command(cmd='AT'):
    if DEBUG: print("DEBUG: Sending %s to BLE Module" % cmd)
    m_uart.write(cmd + '\r\n')
    time.sleep(0.3)

def send_command(cmd):
    command = 'AT+'+cmd
    _send_command(command)

def checkBLEModule():
    _send_command()
    if not expect_reply():
        print("ERROR: Cannot get in touch with BLE module!")
        return False
    return True

def resetBLEModule():
    _send_command('AT+RST')
    if not expect_reply():
        print("ERROR: Cannot get in touch with BLE module!")
        return False
    return True

def setMeshParams(name=DEFAULT_MESHNAME, pwd=DEFAULT_MESHPWD):
    send_command('MESHNAME=' + name)
    if not expect_reply('OK'):
        print("ERROR in setting Mesh Name")
        return False
    send_command('MESHPWD=' + pwd)
    if not expect_reply('OK'):
        print("ERROR in setting Mesh Password")
        return False
    return True    

def mesh_send(dst=0x00, cmd=0xd0, data=[]):
    length = len(data)
    atcommand = 'SEND={:x},{:d},{:02x}'.format(dst, length+1, cmd)
    for d in data:
        atcommand = atcommand + '{:02x}'.format(d)
    send_command(atcommand)
    if not expect_reply('OK'):
        print("ERROR in sending to mesh")
        return False
    return True    

def mesh_send_asc(dst, cmd, data):
    length = len(data)>>1
    atcommand = 'SEND={:s},{:s},{:s}{:s}'.format(dst, str(length), cmd, data)
    if DEBUG: print("Sending to UART: %s" % atcommand)
    send_command(atcommand)
    if not expect_reply('OK'):
        print("ERROR in sending to mesh")
        return False
    return True

def _test_mesh_send(dst=0x00, cmd=0xd0, data=[]):
    length = len(data)
    atcommand = 'SEND={:0x},{:d},'.format(dst, length+1)
    atcommand = atcommand + chr(cmd)
    for d in data:
        atcommand = atcommand + chr(d)
    send_command(atcommand)
    if not expect_reply('OK'):
        print("ERROR in sending to mesh")
        return False
    return True    

def expect_reply(reply='OK'):
    rpy = getReply(5)
    if rpy is None:
        return False
    for i in rpy:
        if i == reply:
            return True
    return False

def getReply(timeout=10):
    events = poll.poll(timeout)
    data = ''
    while (len(events) > 0):
        events = poll.poll(timeout)
        for file in events:
            # file is a tuple
            if file[0] == m_uart:
                ch = m_uart.read(1)
                #print('Got ', ch)
                data = data + chr(ch[0])

    if data is not '':
        # Show the byte as 2 hex digits then in the default way
        if DEBUG: print("DEBUG: received from BLE module: %s " % data)
        #print(data)
        reply = []
        lines = data.split('\r\n')
        for l in lines:
            if l is not '':
                reply.append(l)
        if DEBUG: print("DEBUG: received %d lines of text as %s" % (len(reply), reply))
        return reply

def process_command(mqttcmd):
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
            hcmd,hexdata = mhcmd.split(':')
        else:
            hcmd = mhcmd
        did = int(dids)
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
    if DEBUG: print("Sending to %s op code %s and pars %s" % (device_addr, op_code, pars))
    Dstdev = '{:d}'.format(device_addr)
    Opcode = '{:02x}'.format(op_code)
    Params = ''
    for i in pars:
        Params = Params + '{:02x}'.format(i)
    mesh_send_asc(dst=Dstdev, cmd=Opcode, data=Params)

def process_status(status):
    if DEBUG: print("Process status %s" % status)

def process_config(config):
    if DEBUG: print("Process config %s" % config)

wifierr = None
def wifi_error():
    wifierr = esp32.RMT(0, pin=LED1, clock_div=255)
    wifierr.loop(True)
    wifierr.write_pulses((16384, 1, 16384, 16384, 1), start=0)

def mqtt_error():
    wifierr.write_pulses((32767, 1, 32767, 8192, 1), start=1)

def ble_error():
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

if DEBUG: print("Initialising UART to BLE")
m_uart = UART(2, tx=18, rx=4)                         # init with given baudrate
m_uart.init(115200,bits=8,parity=None,stop=1,timeout=10)

poll = select.poll()
poll.register(m_uart, select.POLLIN)

if not checkBLEModule():
    print("ERROR: Cannot find BLE module!")

atcmd = ''
Opcode = ''

Meshname = DEFAULT_MESHNAME
Meshpass = DEFAULT_MESHPWD
setMeshParams(name=Meshname, pwd=Meshpass)
if not resetBLEModule():
    print("ERROR: Cannot reset BLE module!")
    ble_error()
else:
    led2.duty(896)
setMeshParams(name=Meshname, pwd=Meshpass)

if DEBUG: print("Entering infinte loop")
while True:
    # Processes MQTT network traffic, callbacks and reconnections. (Blocking)
    if m_client: m_client.check_msg()
    getReply(3)
