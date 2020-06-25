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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--shared", help="Shared file (no extension) of device details. Default /tmp/share", default="/tmp/shared.bin")
    parser.add_argument("-p", "--passcode", help="Passcode to decrypt shared file. Default "+_default_passcode, default=_default_passcode)
    args = parser.parse_args()

    sharedbase = args.shared
    passcode = args.passcode
    sharedbin = sharedbase+".bin"
    sharedtxt = sharedbase+".json"
    if os.path.exists(sharedbin):
        decrypted_data = decrypt_share(sharedbin, passcode)
        _devmap = json.loads(decrypted_data)
        with open(sharedtxt, 'w', encoding='utf-8') as f:
            json.dump(_devmap, f, ensure_ascii=False, indent=4)
    else:
        print("Usage: -s shared")

if __name__ == '__main__':
    main()

