from machine import Pin, PWM
import time

led1 = PWM(Pin(33), freq=20000, duty=0)
led2 = PWM(Pin(32), freq=20000, duty=1023)

def breath_once():
    for i in range(1023):
        led1.duty(i)
        led2.duty(1023-i)
        time.sleep(0.002)
    for i in range(1023):
        led1.duty(1023-i)
        led2.duty(i)
        time.sleep(0.002)

def main():
    while(True):
        breath_once()

if __name__ == "__main__":
    main()

main()

 