from machine import Pin
import time

print("=== Blink iniciado ===")

led = Pin(15, Pin.OUT)
counter = 0

while True:
    counter += 1
    led.value(1)
    print("LED ON  -", counter)
    time.sleep(0.5)
    led.value(0)
    print("LED OFF -", counter)
    time.sleep(0.5)
