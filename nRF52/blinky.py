import time
from board import *
from pulseio import *
from digitalio import DigitalInOut, Direction, Pull

led = DigitalInOut(LED1)
led.direction = Direction.OUTPUT

# Setup BLUE and RED LEDs as PWM output (default frequency is 500 Hz)
ledb = PWMOut(LED2_B)
ledr = PWMOut(LED2_R)

button = DigitalInOut(SW1)
button.direction = Direction.INPUT
button.pull = Pull.UP

# Set the BLUE LED to have a duty cycle of 5000 (out of 65535, so ~7.5%)
ledb.duty_cycle = 5000

# Setup pin A0 as a standard PWM out @ 50% to test on the oscilloscope.
# You should see a 50% duty cycle waveform at ~500Hz on the scope when you
# connect a probe to pin A0
#a0 = PWMOut(A0)
#a0.duty_cycle = int(65535/2)

def checkButton():
	led.value = button.value

# Constantly pulse the RED LED
while True:
    for i in range(100):
    	checkButton()
        ledr.duty_cycle = int(i / 100 * 65535)
        time.sleep(0.01)
    for i in range(100, -1, -1):
    	checkButton()
        ledr.duty_cycle = int(i / 100 * 65535)
        time.sleep(0.01)
