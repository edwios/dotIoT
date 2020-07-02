#!/usr/bin/env python3

##
 #  @filename   :   smartline.py
 #  @brief      :   Script to interact with Telink BLE Mesh devices via MQTT
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

import telink
from bluepy import btle
from bluepy.btle import Scanner, DefaultDelegate
from struct import unpack
from binascii import unhexlify
import time
from datetime import datetime
import pickle
import argparse
import paho.mqtt.client as mqtt
import os.path
import sys
import json
import rncryptor
import threading
import binascii

VERSION='1.2'
DEBUG = False

MESHNAME = "BLE MESH"
MESHPASS = "000000"

_ldsdevices = {}
_devmap = None
_speciaCmds = ["reset", "terminate", "settime"]
_acdevice = None
_network = None
_ndev = 0
_gotE1callback = False
_expectE1CallBack = False
_callBackCmd = 0
_callBackSubCmd = 0
_expectedCallBack = []
_meshconnected = False
_refreshmesh = False
_mqtthub = "127.0.0.1"
_lastmqttcmd = ""
_default_passcode = "00000"
ON_DATA = [1,0,0]
OFF_DATA = [0,0,0]
MAXMESHCONNFAILS =4		# Max tries before we declare the mesh is not reachable from this device
MESHREFRESHPERIOD =60	# Update mesh info every minute
CALLBACKWAIT = 5		# Wait 5s for a callback before we count it missing
SCANDURATION = 15		# Scan for BLE devices for 20s
MINDISCRSSI = -100		# Minimum signal strength we consider the device usable for connection
MAXMISSEDE1CALLBACKS = 2
StringType = type("")
IntegerType = type(9)

class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if isNewDev:
            newdev = True
        elif isNewData:
            devupdated = True


def foundLDSdevices(autoconnect=False):
    global _ldsdevices
    global _ndev
    global _devmap
    global _ldevmap
    global _devices
    global _meshname
    global _network
    global DEBUG
        
    autoconenctID = -1
    _network = telink.telink(0x0211, None, _meshname, _meshpass, callback=blecallback)
    # Reset bluetooth adaptor
    if DEBUG: print("%s Debug: Resetting Bluetooth" % time.strftime('%F %H:%M:%S'))
    _network.manager.is_adapter_powered = False
    time.sleep(2)
    _network.manager.is_adapter_powered = True
    time.sleep(2)
    _network.registerConnectableDevices(SCANDURATION)
#    if DEBUG: print("%s Debug: Telink devices found: %s " % (time.strftime('%F %H:%M:%S'), _network.devices))
    telink_scanned_devices = _network.devices

    scanned = False
    scanner = Scanner().withDelegate(ScanDelegate())
    le_scanned_devices = scanner.scan(SCANDURATION)
    lt = time.monotonic()
    while (time.monotonic() - lt < 30) and not scanned:
        try:
#            le_scanned_devices = scanner.scan(SCANDURATION)
            scanned = True
        except:
            print("Exception while trying to scan")
            scanned = False
            time.sleep(2)
    if not scanned:
        print("Fatal error: cannot scan for Bluetooth devices")
        sys.exit(255)
    time.sleep(5)
    count = 0
    maxrssi = MINDISCRSSI
    scanned_devices = []

    # Get intersection of the two scanned records and devmap
    for dev in le_scanned_devices:            
        for (adtype, desc, value) in dev.getScanData():
            if ((adtype == 9) and (value == _meshname)):
                for tdev in telink_scanned_devices:
#                    print("Matching %s with %s" % (dev.addr, tdev.mac_address))
                    if (tdev.mac_address == dev.addr):
                        dev.seq = count
                        mdata = dev.getValueText(255)
                        sige = mdata.find("0001020304050607")
                        sigb = sige -4
                        sigs = mdata[sigb:sige]+"0000"
                        dev.deviceID = unpack('<i', unhexlify(sigs))[0]
                        if _ldevmap > 0:
                            for details in _devices:
                                if DEBUG: print("%s DEBUG: Matching ID %d of MAC %s with %s" % (time.strftime('%F %H:%M:%S'), dev.deviceID, dev.addr, toMACString(details['deviceMac'])))
                                if isBLEMACEqual(dev.addr, toMACString(details['deviceMac'])):
                                    dev.attr = details
                                    dev.isBad = False
                                    if DEBUG: print("%s DEBUG: %s has ID %d" % (time.strftime('%F %H:%M:%S'), dev.attr['deviceName'], dev.deviceID))
                                    count += 1
                                    _ldsdevices[count] = dev
                                    if dev.rssi > maxrssi:
                                        maxrssi = dev.rssi
                                        autoconenctID = dev.deviceID
                                        if DEBUG: print("%s DEBUG: [%s] MAC:%s RSSI: %s ID:%s" % (time.strftime('%F %H:%M:%S'), dev.seq, dev.addr, dev.rssi, dev.deviceID))

    _ndev = count
    if _ndev > 0:
        try:
            pickle.dump(_ldsdevices, open("dbcache.p", "wb"))
        except:
            print("%s ERROR: Cannot save presistance dbcache.p" % time.strftime('%F %H:%M:%S'))
        if DEBUG: print("%s DEBUG: %s devices found and saved. Will auto connect to device %s" % (time.strftime('%F %H:%M:%S'), _ndev, autoconenctID))
    return autoconenctID


def blecallback(mesh, mesg):
    global _gotE1callback, _callBackCmd, _callBackSubCmd, _expectedCallBack, DEBUG
    expectedCmd = 0
    expectedSubCmd = 0

    if DEBUG: print("%s DEBUG: Callback %s" % (time.strftime('%F %H:%M:%S'), binascii.hexlify(bytearray(mesg))))
    _callBackCmd = mesg[7]
    _callBackSubCmd = mesg[11]
    if _expectedCallBack != []:
        expectedCmd = _expectedCallBack[0]
        expectedSubCmd = _expectedCallBack[1]
    if _callBackCmd == 0xE1:
        _gotE1callback = True
    if _callBackCmd == expectedCmd and expectedCmd != 0 and _callBackSubCmd == expectedSubCmd:
        cb = binascii.hexlify(mesg[7:8]).decode("utf-8")
        cbs = binascii.hexlify(mesg[11:12]).decode("utf-8")
        data = binascii.hexlify(bytearray(mesg[12:])).decode("utf-8") 
        hexdata = " ".join(data[i:i+2] for i in range(0, len(data), 2))
        _expectedCallBack = []
        print("%s NOTI: Received %s,%s callback with %s" % (time.strftime('%F %H:%M:%S'), cb, cbs, hexdata))
    pass

def cmd(n, ac, command, data):
    global _network
    global _meshconnected
    global _refreshmesh
    global _ldsdevices
    global _groups
    global DEBUG

    psent = False

    n = int(n)
    if n<0:
        return False	# N<0 is an error carried over from somewhere else
    targetdevice = None
    connectdevice = None
    for dev in list(_ldsdevices.values()):
        if dev.deviceID == ac:
            connectdevice = dev
    if n >= 0x8000:
        for grp in _groups:
            if grp.get('groupAddress') == n:
                targetdevice = grp
                targetdeviceName = targetdevice.get('groupName')
                target = n
    else:
        for dev in _devices:
            if dev.get('deviceId') == n:
                targetdevice = dev
                targetdeviceName = targetdevice.get('deviceName')
                target = targetdevice.get('deviceAddress')
                # Device Address in device map has the HiByte and LowByte reversed
                # Therefore, to properly use the address to communicate, it must be fixed
                # Fixing Device Address
                tarH = int(target/256)
                tarL = int((target/256-tarH)*256)
                target = tarL*256+tarH
    if (targetdevice == None) or (connectdevice == None):
        print("Error: cmd error: Missing either target: %s or ac: %s" % (n, ac))
        return False
#        print("Debug: Wrong target device address ", target)
#        print("Debug: Corrected target device address ", target)
    if DEBUG: print("%s DEBUG: Sending to %s via %s" % (time.strftime('%F %H:%M:%S'), target, connectdevice.attr.get('deviceAddress')))
    if not _meshconnected:
#        print("%s INFO: Connecting to mesh %s (%s) via device %s of ID %d and MAC %s" % (time.strftime('%F %H:%M:%S'), _meshname, _meshpass, connectdevice.attr.get('deviceName'), connectdevice.deviceID, connectdevice.addr))
#        if _network == None or _network.mac != connectdevice.addr:
        if _network == None:
            _network = telink.telink(0x0211, connectdevice.addr, _meshname, _meshpass, callback=blecallback)
        tries = 0
        mesh_dev = None
        # The BLE connection may not always happen on a Raspberry Pi due to the hardware limitation
        # Therefore, let's give it a few chances
        while (not _meshconnected) and (tries < MAXMESHCONNFAILS):
            if DEBUG: print("%s DEBUG: attempt to connect to %s" % (time.strftime('%F %H:%M:%S'), connectdevice.addr))
            mesh_dev = _network.connect(connectdevice.addr)
            lt = time.monotonic()
            while (time.monotonic() - lt < 5) and (mesh_dev is not None):
                time.sleep(0.2)
                if mesh_dev.is_connected():
                    _meshconnected = True
                    print("%s INFO: Connected to mesh" % time.strftime('%F %H:%M:%S'))
                    time.sleep(2)	# We wait a bit until the 1st wave of notifications passed
                    break
            if not _meshconnected:
                tries += 1
                print("Reconnecting attempt %d" % tries)
                _meshconnected = False
                time.sleep(2)
        if not _meshconnected:
            print("%s ERROR: Cannot connect to mesh!" % time.strftime('%F %H:%M:%S'))
            _lastmqttcmd = None
            if tries >= MAXMESHCONNFAILS:
#                connectdevice.isBad = True
                for dev in list(_ldsdevices.values()):
                    if dev.deviceID == ac:
                        dev.isBad = True
                _refreshmesh = True
    if _meshconnected:
        if DEBUG: print("%s DEBUG: Sending to %s of address %s with Cmd: %s and Data: %s" % (time.strftime('%F %H:%M:%S'), targetdeviceName, target, command, data))
        try:
            _network.send_packet(target, command, data)
            psent = True
        except:
            pass
    return psent


# Callback when connected successfully to the MQTT broker
def on_connect(client, userdata, flags, rc):
    global connected, DEBUG

    connected = True
    if DEBUG: print("%s Debug: MQTT broker connected" % time.strftime('%F %H:%M:%S'))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    #    client.subscribe([("sensornet/env/home/balcony/temperature", 0), ("sensornet/env/home/balcony/humidity", 0), ("sensornet/env/home/living/aqi", 0)])
    client.subscribe([("sensornet/env/balcony/brightness", 0), ("sensornet/all", 0), ("sensornet/command", 0)])

def on_disconnect(client, userdata, rc):
    global connected, DEBUG
    connected = False
    if rc != 0:
        print("%s INFO: MQTT broker disconnected, will not try agian" % time.strftime('%F %H:%M:%S'))

def on_publish(client, userdata, result):
    pass

# The callback for when a PUBLISH message is received from the broker.
def on_message(client, userdata, msg):
    global _lastmqttcmd
    global _meshconnected, _refreshmesh
    global _ldsdevices
    global _groups
    global _acdevice
    global _network
    global _expectedCallBack
    global DEBUG

    topic = getattr(msg, 'topic', None)
    payload = getattr(msg, 'payload', None)
    if DEBUG: print("%s DEBUG: got mqtt message %s, topic %s" % (time.strftime('%F %H:%M:%S'), payload, topic))
    if (topic == "sensornet/command" and payload is not None):
        mqttcmd = str(payload.decode("utf-8"))
        _lastmqttcmd = mqttcmd
        dids, hcmd = mqttcmd.split('/')
        hcmd = hcmd.lower()
        did = None
        for dev in _devices:
            devname = dev.get('deviceName')
            devid = dev.get('deviceId')
#            print("Debug: ", devname, devid)
            if (dids.isdigit()):
                if (int(devid) == int(dids)):
                    did = dev.get('deviceId')
            elif (devname == dids):
                did = dev.get('deviceId')
        if (did is None):
            for grp in _groups:
                grpname = grp.get('groupName')
                grpaddr = grp.get('groupAddress')
                if (grpname == dids):
                    did = grpaddr
        if (did > 0):
            if DEBUG: print("%s DEBUG: Recevied %s from MQTT > ID: %s, cmd: %s, autoconnect: %d" % (time.strftime('%F %H:%M:%S'), mqttcmd, did, hcmd, _acdevice))
            if (hcmd == "on"):
                cmd(did, _acdevice, 0xd0, ON_DATA)
            elif (hcmd == "off"):
                cmd(did, _acdevice, 0xd0, OFF_DATA)
            elif (hcmd == "alarm"):
                cmd(did, _acdevice, 0xd0, ON_DATA)
                time.sleep(0.2)
                cmd(did, _acdevice, 0xe2, [0x04, 0xFF, 0x00, 0x00])
            elif (hcmd == "disarm"):
                cmd(did, _acdevice, 0xd0, ON_DATA)
                time.sleep(0.2)
                cmd(did, _acdevice, 0xe2, [0x05, 0x26])
            elif (hcmd == "get_sunrise"):
                cmd(did, _acdevice, 0xea, [0x08, 0x82])
                _expectedCallBack = [0xeb, 0x82]
            elif (mcmd == "get_sunset"):
                cmd(did, _acdevice, 0xea, [0x08, 0x83])
                _expectedCallBack = [0xeb, 0x83]
            elif (hcmd == "disconnect"):
                if _meshconnected:
                    _network.disconnect()
                    _meshconnected = False
            elif (hcmd == "reset"):
                if _meshconnected:
                    _network.disconnect()
                _meshconnected = False
                _refreshmesh = True
            elif (hcmd == "terminate"):
                if _meshconnected:
                    _network.disconnect()
                print("INFO: Received termination command, exiting.")
                sys.exit(0)								
            elif (hcmd == "settime"):
                settime(did)
            elif (hcmd.startswith('raw:')):
                _,hexdata = hcmd.split(':')
                if hexdata != '':
                    hexlist = list(hexdata[i:i+2] for i in range(0, len(hexdata), 2))
                    c = hexlist[0]
                    _expectedCallBack = hexlist[1]
                    d = hexlist[2:]
                    cmd(did, _acdevice, c, d)

def settime(did):
    # Set current time to device
    dtnow = datetime.now()
    yh = dtnow.year // 256
    yl = dtnow.year % 256
    data = [yh, yl, dtnow.month, dtnow.day, dtnow.hour, dtnow.minute, dtnow.second]
    # Let's do it by setting the time to ALL devices (thus 0xFFFF)
    cmd(0xffff, _acdevice, 0xe4, data)

def checkMeshConnection(acdevice, autoconnect):
    global _expectE1CallBack
    global _callBackCmd
    global _refreshmesh

    if DEBUG: print("%s DEBUG: validating mesh connection" % time.strftime('%F %H:%M:%S'))
    if (acdevice >= 0) and autoconnect:
        sendok = cmd(acdevice, acdevice, 0xe0, [0xff, 0xff])
        if sendok:
            _expectE1CallBack=True 	# Expect call back, if not, device's ded
        else:
            # Device's ded, let's see what's out there again
            _refreshmesh = True

def refreshMesh(autoconnect):
    global _expectE1CallBack, _refreshmesh

    acdevice = -1
    if len(_ldsdevices) > 0:
        maxrssi = MINDISCRSSI
        for d in list(_ldsdevices.values()):
            if not d.isBad:
                if d.rssi > maxrssi:
                    maxrssi = d.rssi
                    acdevice = d.deviceID
    if acdevice == -1:
        if DEBUG: print("%s DEBUG: Refreshing mesh data" % time.strftime('%F %H:%M:%S'))
        print("Warning: lost contact with ALL devices. Attempting to refresh")
        acdevice = foundLDSdevices(autoconnect)
        if (acdevice >= 0) and autoconnect:
            sendok = cmd(acdevice, acdevice, 0xe0, [0xff, 0xff])
            if sendok:
                _expectE1CallBack=True 	# Expect 0xE1 call back, if not, device's ded
            else:
                _refreshmesh = True
        else:
            if autoconnect:
                print("%s ERROR: No auto-connectable device was found" % time.strftime('%F %H:%M:%S'))
                _refreshmesh = True
    return acdevice

def listMeshDevices(map, gmap):
    print("Devices and Groups available to control:")
    if map is not None:
        for dev in map:
            print("[%s] %s" % (dev['deviceId'], dev['deviceName']))
    if gmap is not None:
        for grp in gmap:
            print("[%s] %s" % (grp['groupId'], grp['groupName']))


def main():
    global _ndev
    global _meshdevid
    global _ldsdevices
    global _meshname
    global _meshpass
    global _acdevice
    global _refreshmesh
    global _gotE1callback
    global _expectE1CallBack
    global _devmap
    global _ldevmap
    global _devices
    global _groups
    global _mqtthub
    global MESHPASS, MESHNAME
    global DEBUG
    global VERSION

    print("%s INFO: Starting Smartline Flow gateway v%s" % (time.strftime('%F %H:%M:%S'), VERSION))
    print("For MQTT, send message with topic 'sensornet/command'\n")
    print("MQTT message formats:")
    print("    deviceID/command      e.g. 12/on")
    print("    deviceName/command    e.g. Hall light/off")
    print("    groupID/command       e.g. 1/off")
    print("    groupAddress/command  e.g. 32769/on")
    print("    groupName/command     e.g. Living room/off")
    print("\n")
    print("Supported commands:")
    print("    on, off                 -- switch device on or off")
    print("    alarm, disarm           -- set RGBW/RGBWC bubl to Red or warm white colour")
    print("    get_sunrise, get_sunset -- get the sunrise or sunset time")
    print("    disconnect              -- disconnect from mesh")
    print("    reset                   -- disconnect and refresh, reconnect to the mesh")
    print("    terminate               -- disconnect and quit")
    print("    settime                 -- set the current time to the device or group")
    print("    raw:ABC                 -- send raw data with command A, callback B and values C to device or group")
    print("                               e.g. PlugA/raw:EAEB0880 send Get_coundown to the device called PlugA")
    print("\n--help for usages\n")
    parser = argparse.ArgumentParser()
    parser.add_argument("-N", "--meshname", help="Name of the mesh network", default="")
    parser.add_argument("-P", "--meshpass", help="Password of the mesh network", default="")
    parser.add_argument("-d", "--did", help="Device to control", type=int, default=1)
    parser.add_argument("-c", "--choose", help="Choose from a list of devices to control", action="store_true")
    parser.add_argument("-a", "--auto", help="Auto connect to mesh upon start", action="store_true", default=True)
    parser.add_argument("-s", "--shared", help="Shared file (no extension) of device details. Default /tmp/share", default="/tmp/shared.bin")
    parser.add_argument("-R", "--refresh", help="Refresh cache. Use when mesh was updated", action="store_true", default=False)
    parser.add_argument("-m", "--mqtthost", help="MQTT host", default='127.0.0.1')
    parser.add_argument("-v", "--verbose", help="Debugly verbose", action="store_true", default=False)
    parser.add_argument("action", help="on, off to turn on off device, wait to wait for mqtt input, settime to set the date time to the device")
    args = parser.parse_args()
    meshaction = args.action
    if meshaction == "on":
        data = ON_DATA
    if meshaction == "off":
        data = OFF_DATA
    _meshname = args.meshname
    _meshpass = args.meshpass
    _meshdevid = args.did
    autoconnect = args.auto
    sharedbase = args.shared
    sharedbin = sharedbase+".bin"
    sharedtxt = sharedbase+".json"
    choosefromlist = args.choose
    refreshCache = args.refresh
    _mqtthub = args.mqtthost
    DEBUG = args.verbose
    if DEBUG: print("--- Debug mode ---")
    tmpMeshName = ""
    tmpMeshPass = ""

    if (os.path.exists(sharedtxt)):
#        print("%s INFO: Found plain shared" % time.strftime('%F %H:%M:%S'))
        _devmap = json.load(open(sharedtxt))
    elif os.path.exists(sharedbin):
#        print("%s INFO: Found shared, attempt to decrypt" % time.strftime('%F %H:%M:%S'))
        decrypted_data = decrypt_share(sharedbin, _default_passcode)
        _devmap = json.loads(decrypted_data)
        if DEBUG: print("%s DEBUG: Writing decrypted file to %s" % (time.strftime('%F %H:%M:%S'), sharedtxt))
        with open(sharedtxt, 'w', encoding='utf-8') as f:
            json.dump(_devmap, f, ensure_ascii=False, indent=4)
    if _devmap is not None:
        _devices = _devmap['devices']
        _groups = _devmap['groups']
        _ldevmap = len(_devices)
        if (_ldevmap > 0):
            print("%s INFO: Loaded %d devices and %d groups in map file" % (time.strftime('%F %H:%M:%S'), _ldevmap, len(_groups)))
            tmpMeshName = _devmap['space']['meshNetworkName']
            tmpMeshPass = _devmap['space']['meshNetworkPassword']
            listMeshDevices(_devices, _groups)
        else:
            print("%s ERROR: Something's wrong, no device included in sharing or decryption failed" % time.strftime('%F %H:%M:%S'))


    if (_meshname == "" and tmpMeshName == ""):
        _meshname = input("Input the mesh name [3S11ZFCS]: ") or MESHNAME
    if (_meshpass == "" and tmpMeshPass == ""):
        _meshpass = input("Input the mesh password [096355]: ") or MESHPASS
    if (_meshname == "" and tmpMeshName != ""):
        _meshname = tmpMeshName
    if (_meshpass == "" and tmpMeshPass != ""):
        _meshpass = tmpMeshPass

    if DEBUG: print("%s DEBUG: Using mesh name %s and passcode %s" % (time.strftime('%F %H:%M:%S'), _meshname, _meshpass))
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_publish = on_publish
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    if DEBUG: print("%s DEBUG: Connecting to mqtt host %s" % (time.strftime('%F %H:%M:%S'), _mqtthub))
    client.connect_async(_mqtthub, 1883, 60)
    client.loop_start() #start loop to process received messages

    if autoconnect:
        _acdevice = refreshMesh(autoconnect)
        _meshdevid = _acdevice
        if DEBUG: print("%s DEBUG: Autoconnect device ID: %d" % (time.strftime('%F %H:%M:%S'), _acdevice))
    else:
        # Instead of looking for devices everytime, let's use a cache :)
        if os.path.exists("dbcache.p") and (not choosefromlist) and (not refreshCache):
            _ldsdevices = pickle.load(open("dbcache.p", "rb"))
            _ndev = len(_ldsdevices)
            if DEBUG: print("%s DEBUG: Loaded %s devices from cache" % (time.strftime('%F %H:%M:%S'), _ndev))
        else:
            # Ahem, first time, let's do it the hard way
            refreshMesh(autoconnect)
        devn = 0
        _meshdevid = 0
        while (devn == 0) or (devn > _ndev) or (_meshdevid == 0):
            devn = int(input("Which device ID you want to connect to join the mesh? ") or "0")
            for dev in list(_ldsdevices.values()):
                if dev.deviceID == devn:
                    _meshdevid = dev.deviceID
        _acdevice = _meshdevid

    if (choosefromlist):
        print("%s INFO: Will have device in mesh %s from below list to %s" % (time.strftime('%F %H:%M:%S'), _meshname, args.action))
    else:
        print("%s INFO: Will have device #%s in mesh %s to %s" % (time.strftime('%F %H:%M:%S'), _meshdevid, _meshname, args.action))

    if (_meshdevid >= 0) and (_ndev > 0) and (_acdevice >= 0):
        if (meshaction == "on") or (meshaction == "off"):
            # currently only simple ON/OFF is implemented
            # For other commands, look into the Telink manuals
            cmd(_meshdevid, _acdevice, 0xd0, data)
        if meshaction == "settime":
            settime(_meshdevid)
        else:
            lt = time.monotonic()
            cblt = time.monotonic()
            missedE1Callbacks = 0
            while (_acdevice >= 0):
                time.sleep(0.1)
# We don't do periodic refresh due to blocking mesh refresh
# This should be handled by a separated thread
# So we now only check and refresh upon error
                if (time.monotonic() - lt > MESHREFRESHPERIOD):
                    lt = time.monotonic()
                    if DEBUG: print("%s DEBUG: Periodic mesh ping" % time.strftime('%F %H:%M:%S'))
                    checkMeshConnection(_acdevice, autoconnect)
                    cblt = time.monotonic()
                if (time.monotonic() - cblt > CALLBACKWAIT) and _expectE1CallBack:
                    cblt = time.monotonic()
                    # We expect to have callback
                    if not _gotE1callback:
                        # Oops, we don't have one
                        print("%s WARN: Didn't receive any E1 callback" % time.strftime('%F %H:%M:%S'))
                        missedE1Callbacks = missedE1Callbacks + 1
                        if (missedE1Callbacks > MAXMISSEDE1CALLBACKS):
                            missedE1Callbacks = 0
                            _refreshmesh = True
                if (time.monotonic() - cblt <= CALLBACKWAIT) and _expectE1CallBack:
                        if DEBUG: print("%s DEBUG: Got E1 callback" % time.strftime('%F %H:%M:%S'))
                        _gotE1callback = False
                        _expectE1CallBack = False

                if _refreshmesh:
                    _refreshmesh = False
                    _acdevice = refreshMesh(autoconnect)
                    cblt = time.monotonic()
                    lt = cblt
                pass
            print("%s FATAL: No device to connect to the mesh, aborted" % time.strftime('%F %H:%M:%S'))
            sys.exit(255)
    else:
        print("%s FATAL: no device or no mesh can be connected. Aborted." % time.strftime('%F %H:%M:%S'))
        sys.exit(255)

def toMACString(mac_int):
#    mac_hex = "{:012x}".format(mac_int)
#    mac_str = ":".join(mac_hex[i:i+2] for i in range(0, len(mac_hex), 2))
    mac_hex = "{:08x}".format(mac_int)
    l = len(mac_hex)
    mac_str = ":".join(mac_hex[l-i-2:l-i] for i in range(0, len(mac_hex), 2))
    return mac_str

def isBLEMACEqual(mac1, mac2):
    mac1s = mac1
    mac2s = mac2
    if (len(mac1) == 17):
        mac1s = mac1[6:]
    if (len(mac2) == 17):
        mac2s = mac2[6:]
    return (mac1s == mac2s)

def decrypt_share(enc_file, passcode):
    cryptor = rncryptor.RNCryptor()
    filename = enc_file
    f = open(filename, mode='rb')
    data = f.read()
    decrypted_data = cryptor.decrypt(data, passcode)
    f.close()
    return decrypted_data

if __name__ == '__main__':
    main()
