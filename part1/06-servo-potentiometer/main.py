from machine import Pin, PWM, ADC
import time

servo = PWM(Pin(15))
servo.freq(50)

pot = ADC(26)

def angle_to_duty(angle):
    # SG90: ~0.5 ms (0°) a ~2.5 ms (180°), periodo de 20 ms
    min_us = 500
    max_us = 2500
    pulse_us = min_us + (max_us - min_us) * angle / 180
    return int(pulse_us * 65535 / 20000)

while True:
    raw = pot.read_u16()           # 0..65535
    angle = raw * 180 // 65535     # 0..180
    servo.duty_u16(angle_to_duty(angle))
    print("Pot={}  Angulo={} grados".format(raw, angle))
    time.sleep(0.1)
