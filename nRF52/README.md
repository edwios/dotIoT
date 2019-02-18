AQISensor v1.0
===============

Air quality sensor on nRF52840 Dongle, part of dotIoT.

An air quality sensor utilising a nRF52840 Dongle and AdaFruit's Curcuitpython to collect the air quality indices using a SGP30 sensor and made available the data as a BLE peripheral.

The Air Quqlity indices shown including:

* eCO₂ in ppm
* eTVoC in ppm
* AQI

**Preparations**

Download AdaFruit's CircuitPython from github: https://github.com/adafruit/circuitpython

Follow instructions below to compile the firmware

**Compile firmware**

```
git clone https://github.com/adafruit/circuitpython.git circuitpython
cd circuitpython
git submodule update --init
make -C mpy-cross
```

You will need the Bluetooth stack for this to work, therefore download the softdevice from Nordic Semi:
`./bluetooth/download_ble_stack.sh`

To compile for the nRF52840 Dongle with the soft device, perform the following:
`make BOARD=pca10059 SD=s140`

**Flash firmware to the nRF52840 Dongle**

Launch the nRF Connect on your PC/Mac

Launch the Programmer on the nRF Connect

Select the dongle. If you don't see your dongle, push the Reset button on the dongle, the LED shall flashes Red and you should be able to choose the dongle for programming.

Load both hex files of the circuitpython and the soft device and click 'write' to write the firmware to the dongle.

Once the dongle rebooted, you shall see a CIRCUITPY disk available on your Desktop.

**Installation**

Copy the `lib` folder and the code.py to the CIRCUITPY disk.

Once the copy is done, you should see a Blue LED flashing on the Dongle. You can now connect to the dongle by using nRF Connect on your phone and read the sensor data off.


