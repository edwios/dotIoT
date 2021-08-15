#!/usr/bin/env python3

from binascii import unhexlify
import time
from datetime import datetime
import argparse
import os.path
import sys
import json
import rncryptor
import secrets

_default_passcode='00000'

"""
Define mesh credentials in secrets.py
E.g.:
MESH_NAME = "MyMeshName"
MESH_PASS = "MyMeshPassword"
"""
_default_meshname=secrets.MESH_NAME
_default_meshpass=secrets.MESH_PASS
_default_name='Exported home'


def decrypt_share(enc_file, passcode):
    cryptor = rncryptor.RNCryptor()
    filename = enc_file
    f = open(filename, mode='rb')
    data = f.read()
    decrypted_data = cryptor.decrypt(data, passcode)
    f.close()
    return decrypted_data


def encrypt_share(text_file, passcode):
    cryptor = rncryptor.RNCryptor()
    filename = text_file
    f = open(filename, mode='rb')
    data = f.read()
    encrypted_data = cryptor.encrypt(data, passcode)
    f.close()
    return encrypted_data


def convert_encrypt(intent_file, passcode):
    s = 'EXECUTE intent: '
    cryptor = rncryptor.RNCryptor()
    devicelists = ''
    with open(intent_file, mode='r') as f:
        jdatas = f.read()
    f.close()
    k = jdatas.find(s)
    if (k != -1):
        jdatas = jdatas[len(s):]
    devicelists = parse_to_devices(json.loads(jdatas))
    print("DEBUG: ", devicelists)
    encrypted_data = cryptor.encrypt(devicelists, passcode)
    return encrypted_data      


def reverseEndian(v16):
    rv16 = 0
    i = unhexlify(v16)
    rv16 = (i[1] << 8) + i[0]
    return rv16


def parse_to_devices(jdata):
    devices = jdata['devices']
    l = len(devices)
    if (l == 0):
        return None
    sharedlist = {}
    devicelist = []
    for device in devices:
        adevice = {}
        customData = device['customData']
        devAddr = customData['newDeviceAddres']
        adevice.update({"deviceAddress":devAddr})
        adevice.update({"deviceName":customData['deviceName']})
        adevice.update({"deviceMac":int(customData['macAddress'], 16)})
        adevice.update({"deviceProductId":reverseEndian(customData['productUUID'])})
        adevice.update({"deviceId":(devAddr >> 8)})
        adevice.update({"deviceSort":((devAddr-1) >> 8)})
        devicelist.append(adevice)
    sharedlist.update({"devices":devicelist})
    sharedlist.update({"groups": []})
    space = {}
    space.update({"meshSpaceName": _default_name})
    space.update({"meshNetworkName": _default_meshname})
    space.update({"meshNetworkPassword": _default_meshpass})
    space.update({"meshAdmin": True})
    sharedlist.update({"space":space})
    """
    clients = []
    clientInfo = {}
    clientInfo.update({"version":"1.0.4"})
    clientInfo.update({"id": 1})
    clientInfo.update({})
    clients.append(clientInfo)
    sharedlist.update({"clients":clients})
    """
    return json.dumps(sharedlist)


def main():
    parser = argparse.ArgumentParser(description='Script to encrypt and decrypt SL Flow share from and into JSON. It can also converts a BLE SS Execute Inttent request JSON for SL Flow share.')
    parser.add_argument("-s", "--shared", help="Shared file (.proove) of device details. Default None", default=None, nargs=1)
    parser.add_argument("-p", "--passcode", help="Passcode to decrypt shared file. Default "+_default_passcode, default=_default_passcode)
    parser.add_argument("-e", "--encrypt", help="Encrypt instead of decrypt. Default No", action="store_true", default=False)
    parser.add_argument("-c", "--convert", help="Convert from a BLE SS EXECUTE intent into a shared file (.proove). Implied --encrypt", default=None, nargs=1)
    args = parser.parse_args()

    sharedname = args.shared
    convertfile = args.convert
    if sharedname != None:
        sharedbase = os.path.splitext(sharedname[0])[0]
    elif convertfile != None:
        sharedbase = os.path.splitext(convertfile[0])[0]
    else:
        print("Error! Either -c or -s must be specified!")
        exit(255)
    passcode = args.passcode
    encrypt = args.encrypt
    sharedbin = sharedbase+".proove"
    sharedtxt = sharedbase+".json"
    if (convertfile is None):
        if (encrypt and sharedtxt != sharedname[0]):
            sharedtxt = sharedname[0]
        elif (not encrypt and sharedbin != sharedname[0]):
            sharedbin = sharedname[0]
    else:
        convertfile = convertfile[0]
    if (convertfile != None and os.path.exists(convertfile)):
        print('Converting {:s} into {:s}'.format(convertfile, sharedbin))
        encrypted_data = convert_encrypt(convertfile, passcode)
        with open(sharedbin, 'wb') as f:
            f.write(encrypted_data)
            f.close()
    elif sharedname != None:
        if os.path.exists(sharedbin) and not encrypt:
            print('Decoding {:s} into {:s}'.format(sharedbin, sharedtxt))
            decrypted_data = decrypt_share(sharedbin, passcode)
            _devmap = json.loads(decrypted_data)
            with open(sharedtxt, 'w', encoding='utf-8') as f:
                json.dump(_devmap, f, ensure_ascii=False, indent=4)
        elif os.path.exists(sharedtxt) and encrypt:
            print('Generating share {:s}'.format(sharedbin))
            encrypted_data = encrypt_share(sharedtxt, passcode)
            with open(sharedbin, 'wb') as f:
                f.write(encrypted_data)
                f.close()
    else:
        """
        Usage: {:s} [-s file | -c file] [-e]

        """.format(os.path.basename(__file__))


if __name__ == '__main__':
    main()

