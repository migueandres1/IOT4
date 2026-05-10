from machine import Pin
import dht
import time

sensor = dht.DHT22(Pin(15))

while True:
    try:
        sensor.measure()
        t = sensor.temperature()
        h = sensor.humidity()
        print("Temperatura: {:.1f} C   Humedad: {:.1f} %".format(t, h))
    except Exception as e:
        print("Error leyendo DHT22:", e)
    time.sleep(2)
