#!/usr/bin/python3

from gpiozero import LED
from time import sleep

boot = LED(21)
en = LED(20)

def reset():
    en.off()
    sleep(0.5)
    en.on()
    sleep(0.1)

def pgm_mode():
    boot.off()
    reset()

def main():
    boot.on()
    reset()

if __name__ == "__main__":
    main()

