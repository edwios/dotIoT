#!/usr/bin/env python3

from binascii import unhexlify
import time
from datetime import datetime
import argparse
import os.path
import sys
import json
import rncryptor

_default_passcode='00000'

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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--shared", help="Shared file (no extension) of device details. Default shared", default="shared")
    parser.add_argument("-p", "--passcode", help="Passcode to decrypt shared file. Default "+_default_passcode, default=_default_passcode)
    parser.add_argument("-e", "--encrypt", help="Encrypt instead of decrypt. Default No", action="store_true", default=False)
    args = parser.parse_args()

    sharedbase = args.shared
    passcode = args.passcode
    encrypt = args.encrypt
    sharedbin = sharedbase+".proove"
    sharedtxt = sharedbase+".json"
    if os.path.exists(sharedbin) and not encrypt:
        decrypted_data = decrypt_share(sharedbin, passcode)
        _devmap = json.loads(decrypted_data)
        with open(sharedtxt, 'w', encoding='utf-8') as f:
            json.dump(_devmap, f, ensure_ascii=False, indent=4)
    elif os.path.exists(sharedtxt) and encrypt:
        encrypted_data = encrypt_share(sharedtxt, passcode)
        with open(sharedbin, 'wb') as f:
            f.write(encrypted_data)
            f.close()
    else:
        print("Usage: -s shared")

if __name__ == '__main__':
    main()

