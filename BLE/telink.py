# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Contains code derived from python-tikteck,
# Copyright 2016 Matthew Garrett <mjg59@srcf.ucam.org>

import random
import threading
import time
import binascii

import gatt
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

def hex_to_str(hex_str):
    return str(bytearray([int(n, 16) for n in hex_str]))

def encrypt(key, data):
    k = AES.new(bytes(reversed(key)), AES.MODE_ECB)
    data = reversed(list(k.encrypt(bytes(reversed(data)))))
    rev = []
    for d in data:
        rev.append(d)
    return rev
 
def generate_sk(name, password, data1, data2):
    name = name.ljust(16, chr(0))
    password = password.ljust(16, chr(0))
    key = [ord(a) ^ ord(b) for a,b in zip(name,password)]
    data = data1[0:8]
    data += data2[0:8]
    return encrypt(key, data)

def key_encrypt(name, password, key):
    name = name.ljust(16, chr(0))
    password = password.ljust(16, chr(0))
    data = [ord(a) ^ ord(b) for a,b in zip(name,password)]
    return encrypt(key, data)

def encrypt_packet(sk, address, packet):
#    print("Debug: Encrypting from ", sk, address, binascii.hexlify(bytearray(packet)))
    auth_nonce = [address[0], address[1], address[2], address[3], 0x01, packet[0], packet[1], packet[2], 15, 0, 0, 0, 0, 0, 0, 0]
    
    authenticator = encrypt(sk, auth_nonce)
    
    for i in range(15):
        authenticator[i] = authenticator[i] ^ packet[i+5]
    
    mac = encrypt(sk, authenticator)

    for i in range(2):
        packet[i+3] = mac[i]

    iv = [0, address[0], address[1], address[2], address[3], 0x01, packet[0], packet[1], packet[2], 0, 0, 0, 0, 0, 0, 0]
    temp_buffer = encrypt(sk, iv)
    for i in range(15):
        packet[i+5] ^= temp_buffer[i]

#    print("Debug: Encrypted ", binascii.hexlify(bytearray(packet)))
    return packet

def decrypt_packet(sk, address, packet):
    print("Debug: decrypting from ", sk, address, packet, type(packet))
    iv = [address[0], address[1], address[2], packet[0], packet[1], packet[2],
          packet[3], packet[4], 0, 0, 0, 0, 0, 0, 0, 0] 
    plaintext = [0] + iv[0:15]

    result = encrypt(sk, plaintext)

    for i in range(len(packet)-7):
        packet[i+7] ^= result[i]
#    print("Debug: Decrypted ", binascii.hexlify(bytearray(packet)))
    return packet

class TelinkDeviceManager(gatt.DeviceManager):
    def device_discovered(self, device):
        pass
#        print("Discovered [%s] %s" % (device.mac_address, device.alias()))

class Peripheral(gatt.Device):
    serviceResolved = False
    link = None
    callback = None
    c_values = {}
    def connect_succeeded(self):
        super().connect_succeeded()
        self.serviceResolved = False
        print("[%s] Connected" % (self.mac_address))

    def connect_failed(self, error):
        super().connect_failed(error)
        print("[%s] Connection failed: %s" % (self.mac_address, str(error)))

    def disconnect_succeeded(self):
        super().disconnect_succeeded()
        print("[%s] Disconnected" % (self.mac_address))

    def services_resolved(self):
        super().services_resolved()
        self.serviceResolved = True
#        self.connectedCallback()

    def setNotificationCallback(self, link, callback):
        self.link = link
        self.callback = callback
    
    def getValue(self, characteristic):
        c_uuid = str(characteristic.uuid)
        value = self.c_values.get(c_uuid)
        return value

    def characteristic_value_updated(self, characteristic, value):
        value = list(value)
        c_uuid = str(characteristic.uuid)
        self.c_values[c_uuid] = value
        print("Debug: Characteristic %s value update %s" % (characteristic.uuid, binascii.hexlify(bytearray(self.c_values.get(c_uuid)))))
        if c_uuid == '00010203-0405-0607-0809-0a0b0c0d1911':
            print("Debug: received notication from 1911 with ", binascii.hexlify(bytearray(value)))
            if self.link is not None:
                print("Debug: callback exists, decrypting received value from 1911")
                decrypted = decrypt_packet(self.link.sk, self.link.macdata, value)
                self.callback(self.link.mesh, decrypted)

    
    def getCharacteristics(self, characteristic_uuid):
        for s in self.services:
            for c in s.characteristics:
#                print("Debug: Matching characteristic %s to %s" % (c.uuid, characteristic_uuid))
                if c.uuid == characteristic_uuid:
                    print("Debug: Found matched charateristic ", characteristic_uuid)
                    return c



class telink:
    def __init__(self, vendor, mac, name, password, mesh=None, callback=None):
        self.vendor = vendor
        self.mac = mac
        if (mac is not None):
            self.macarray = mac.split(':')
            self.macdata = [int(self.macarray[5], 16), int(self.macarray[4], 16), int(self.macarray[3], 16), int(self.macarray[2], 16), int(self.macarray[1], 16), int(self.macarray[0], 16)]
        self.name = name
        self.password = password
        self.callback = callback
        self.mesh = mesh
        self.packet_count = random.randrange(0xffff)
        self.scanned = False
        self.manager = TelinkDeviceManager(adapter_name='hci0')
        self.manager.is_adapter_powered = True
        thread = threading.Thread(target=self.startManager)
        thread.daemon = True
        thread.start()


    def startManager(self):
        if (self.manager is None):
            print("Error: Device manager not defined!")
        else:
            print("Debug: Thread starting manager")
            self.manager.run()

    def set_sk(self, sk):
        self.sk = sk

    def registerConnectableDevices(self, scanTime = 10):
        print("Debug: registering devices")
        self.manager.start_discovery()
        time.sleep(scanTime)
        self.manager.stop_discovery()
        self.devices = self.manager.devices()
        self.scanned = True

    def disconnect(self):
        if (self.mac is not None):
            self.device.disconnect()

    def connect(self, mac):
        self.mac = mac
        self.macarray = mac.split(':')
        self.macdata = [int(self.macarray[5], 16), int(self.macarray[4], 16), int(self.macarray[3], 16), int(self.macarray[2], 16), int(self.macarray[1], 16), int(self.macarray[0], 16)]
        print("Debug: connecting to %s" % self.mac)
        if (not self.scanned):
            print("Debug: no device have registered")
            self.registerConnectableDevices()
            lt = time.monotonic()
            while (time.monotonic() - lt < 15):
                time.sleep(0.5)
                if (self.scanned):
                    break
        if (self.scanned):
            self.device = Peripheral(mac_address = self.mac, manager = self.manager)
    #        self.device.setConnectedCallback(callback = onConnected)
            self.device.connect()
            print("Debug: waiting for service to resolve")
            lt = time.monotonic()
            while (time.monotonic() - lt < 5):
                time.sleep(0.2)
                if (self.device.serviceResolved):
                    break
            if (self.device.serviceResolved):
    #    def onConnected(self):
                print("Debug: all services resolved")
                self.notification = self.device.getCharacteristics("00010203-0405-0607-0809-0a0b0c0d1911")
                self.notification.enable_notifications()
                self.control = self.device.getCharacteristics("00010203-0405-0607-0809-0a0b0c0d1912")
                self.pairing = self.device.getCharacteristics("00010203-0405-0607-0809-0a0b0c0d1914")

                data = [0] * 16
                random_data = get_random_bytes(8)
                for i in range(8):
                    data[i] = random_data[i]
                enc_data = key_encrypt(self.name, self.password, data)
                packet = [0x0c]
                packet += data[0:8]
                packet += enc_data[0:8]
                self.pairing.write_value(bytes(packet))
                time.sleep(1)
                self.pairing.c_value = None
                lt = time.monotonic()
                data2 = None
                self.pairing.read_value()
                while time.monotonic() - lt < 5 and data2 is None:
                    data2 = self.device.getValue(self.pairing)
                    time.sleep(0.1)
                if data2 is None:
                    print("Exception: unable to connect")
                    return None

                self.sk = generate_sk(self.name, self.password, data[0:8], data2[1:9])
                print("Debug: sk, mac, macdata: ", self.sk, self.mac, self.macdata)
                if self.callback is not None:
                    print("Debug: setting notification call back")
                    self.device.setNotificationCallback(self, self.callback)
                    self.notification.write_value(bytes([0x1]))
            else:
                print("Warning: no service resolved for %s" % self.device.alias())
            return self.device
        else:
            print("Error: scanning failed, check BT hardware!")
        return None

    def send_packet(self, target, command, data):
        packet = [0] * 20
        packet[0] = self.packet_count & 0xff
        packet[1] = self.packet_count >> 8 & 0xff
        packet[5] = target & 0xff
        packet[6] = (target >> 8) & 0xff
        packet[7] = command
        packet[8] = self.vendor & 0xff
        packet[9] = (self.vendor >> 8) & 0xff
        for i in range(len(data)):
            packet[10 + i] = data[i]
        print("send_packet verify plain: ", binascii.hexlify(bytearray(bytes(packet))))
        enc_packet = encrypt_packet(self.sk, self.macdata, packet)
        print("send_packet verify encrypted: ", binascii.hexlify(bytearray(bytes(enc_packet))))
#        dec_packet = decrypt_packet(self.sk, self.macdata, enc_packet)
#        print("send_packet verify decrypted: ", binascii.hexlify(bytearray(bytes(dec_packet))))
        self.packet_count += 1
        if self.packet_count > 65535:
            self.packet_count = 1

        # BLE connections may not be stable. Spend up to 10 seconds trying to
        # reconnect before giving up.
        initial = time.monotonic()
        while True:
            if time.monotonic() - initial >= 10:
    #        raise Exception("Unable to connect")
                print("Write failed")
                break
            try:
                print("Writing bytes")
                self.control.write_value(bytes(enc_packet))
                print("Write successful")
                break
            except:
                self.connect()
