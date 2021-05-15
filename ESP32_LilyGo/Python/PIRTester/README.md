# README

PIRTester is a simple tool to perform testing on the BLE PIR sensor by simulating the actions of a PIR.

It utilise a TTGO T-display v1.1 board with is a ESP32 4MB Flash board with a colour TFT display.

The SPI speed of the TTGO board is max'ed at 20MHz, and SPI 1 must be used.

E.g. when initialising the SPI on the TTGO board:

`spi = SPI(1, baudrate=20000000, ...`

Display is also configured to landscape orientation by specifying width, height as 240, 135 respectivaly. This require the support of the modified micropython driver (see below) in order to work.

Install
=====

PIRTester requires two modules (included):

ST7789 driver for micropython<br/>
https://github.com/edwios/TTGO_TFT

Memory based font renderer for python<br/>
https://github.com/russhughes/ttgo-hershey-fonts

Build
=====

Build micropython with the ST7789 driver and flash to the TTGO board.

Copy everything in the `PIRTester` director onto the TTGO board.


Run
====

Optionally rename `PIRTester.py` to `main.py` on the TTGO board to auto-run the tester.

