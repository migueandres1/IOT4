from machine import Pin
import time

red    = Pin(15, Pin.OUT)
yellow = Pin(14, Pin.OUT)
green  = Pin(13, Pin.OUT)

def all_off():
    red.off(); yellow.off(); green.off()

while True:
    all_off()
    green.on()
    time.sleep(4)

    all_off()
    yellow.on()
    time.sleep(1.5)

    all_off()
    red.on()
    time.sleep(4)
