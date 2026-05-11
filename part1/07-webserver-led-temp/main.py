"""
Web server con LED y monitor de temperatura.
Incluye un cliente interno que prueba el server cada 8s para mantener
la ruta del gateway de Wokwi activa y demostrar el flujo HTTP completo
en la consola.
"""

import network
import socket
import time
import dht
from machine import Pin

WIFI_SSID     = "Wokwi-GUEST"
WIFI_PASSWORD = ""

led    = Pin(15, Pin.OUT)
sensor = dht.DHT22(Pin(14))

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Conectando a", WIFI_SSID, "...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        for _ in range(20):
            if wlan.isconnected():
                break
            time.sleep(1)
    return wlan.ifconfig()[0] if wlan.isconnected() else None

def read_dht():
    try:
        sensor.measure()
        return sensor.temperature(), sensor.humidity()
    except Exception:
        return None, None

PAGE = """<!DOCTYPE html><html><head>
<meta charset="UTF-8"><title>LED + Temp</title>
<meta http-equiv="refresh" content="5">
<style>
body{{font-family:sans-serif;background:#0f172a;color:#f1f5f9;
     padding:24px;text-align:center}}
.card{{background:#1e293b;border:1px solid #334155;border-radius:12px;
       padding:20px;margin:12px auto;max-width:320px}}
.btn{{padding:10px 24px;border:none;border-radius:8px;font-weight:600;
      cursor:pointer;font-size:1rem}}
.on{{background:#22c55e;color:#000}} .off{{background:#ef4444;color:#fff}}
</style></head><body>
<h1>LED + Monitor de Temperatura</h1>
<div class="card"><h2>{temp} C</h2><p>Humedad: {hum} %</p></div>
<div class="card">LED: <strong>{led_state}</strong><br><br>
<form action="/toggle" method="get">
<button class="btn {btn_cls}">{btn_label}</button></form></div>
</body></html>"""

def build_page(temp, hum, led_on):
    return PAGE.format(
        temp = temp if temp is not None else "--",
        hum  = hum  if hum  is not None else "--",
        led_state = "ENCENDIDO" if led_on else "APAGADO",
        btn_cls   = "off" if led_on else "on",
        btn_label = "Apagar LED" if led_on else "Encender LED",
    )

def handle_one_request(server_sock, led_on):
    conn = None
    try:
        conn, peer = server_sock.accept()
        conn.settimeout(3)
        req = conn.recv(1024).decode("utf-8", "ignore")
        line = req.split("\r\n")[0] if req else "(vacio)"
        print("[SERVER] <-", peer[0], "|", line)

        if "GET /toggle" in req:
            led_on = not led_on
            led.value(1 if led_on else 0)
            print("[SERVER] LED ->", "ON" if led_on else "OFF")

        t, h = read_dht()
        page = build_page(t, h, led_on)
        body_bytes = page.encode("utf-8")
        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/html; charset=utf-8\r\n"
            "Content-Length: " + str(len(body_bytes)) + "\r\n"
            "Connection: close\r\n\r\n"
        ).encode("utf-8") + body_bytes
        conn.sendall(response)
        print("[SERVER] -> 200 OK,", len(response), "bytes")
    except OSError:
        pass
    except Exception as e:
        print("[SERVER] err:", e)
    finally:
        if conn is not None:
            try: conn.close()
            except: pass

    return led_on

def self_test_request(path, my_ip):
    cs = None
    try:
        cs = socket.socket()
        cs.settimeout(5)
        cs.connect((my_ip, 80))
        req = "GET " + path + " HTTP/1.1\r\nHost: " + my_ip + "\r\nConnection: close\r\n\r\n"
        cs.sendall(req.encode("utf-8"))
        time.sleep_ms(100)
    except Exception as e:
        print("[CLIENTE] err:", e)
    finally:
        if cs is not None:
            try: cs.close()
            except: pass

def main():
    ip = connect_wifi()
    if ip is None:
        print("Sin WiFi"); return
    print("WiFi OK ->", ip)
    print("Web server: http://" + ip)
    print("Cliente automatico cada 8s\n")

    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(addr)
    server.listen(5)
    server.settimeout(0.5)
    print("[SERVER] Escuchando en puerto 80\n")

    led_on = False
    last_self_test = time.time()
    counter = 0

    while True:
        led_on = handle_one_request(server, led_on)

        if time.time() - last_self_test >= 8:
            counter += 1
            path = "/toggle" if counter % 2 == 0 else "/"
            print("[CLIENTE] -> envia GET", path)
            self_test_request(path, ip)
            last_self_test = time.time()

main()
