#!/bin/bash
rsync  -avutz -e ssh ./* edwintam@zerow2.local:/home/edwintam/BLE/
rsync  -avutz -e ssh ./* edwintam@zerow1.local:/home/edwintam/dotIoT/BLE/
rsync  -avutz -e ssh ./* edwintam@oppai.local:/home/edwintam/BLE/
rsync  -avutz -e ssh ./* edwintam@legateway.local:/home/edwintam/BLE/

