from machine import Pin
import time

TRIG = Pin(17, Pin.OUT)
ECHO = Pin(16, Pin.IN)

def measure_cm():
    TRIG.low()
    time.sleep_us(2)
    TRIG.high()
    time.sleep_us(10)
    TRIG.low()

    timeout = 30000
    t0 = time.ticks_us()
    while ECHO.value() == 0:
        if time.ticks_diff(time.ticks_us(), t0) > timeout:
            return None
    start = time.ticks_us()
    while ECHO.value() == 1:
        if time.ticks_diff(time.ticks_us(), start) > timeout:
            return None
    end = time.ticks_us()
    duration = time.ticks_diff(end, start)
    return (duration * 0.0343) / 2

while True:
    d = measure_cm()
    if d is None:
        print("Sin lectura")
    else:
        print("Distancia: {:.1f} cm".format(d))
    time.sleep(1)
