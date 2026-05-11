"""
Proyecto final - Monitor de tanque IoT.

- DHT22: temperatura y humedad
- HC-SR04: distancia (nivel del tanque)
- LED RGB: cambia color segun rango de temperatura
- LED rojo: alarma de tanque casi vacio (< 10 cm)
- LED bomba: controlado desde el web server
- Web server con dashboard

Autor: Miguel Lopez
"""

import network
import socket
import time
import dht
from machine import Pin, PWM

WIFI_SSID     = "Wokwi-GUEST"
WIFI_PASSWORD = ""

dht_sensor = dht.DHT22(Pin(15))

TRIG = Pin(17, Pin.OUT)
ECHO = Pin(16, Pin.IN)

led_r = PWM(Pin(2)); led_r.freq(1000)
led_g = PWM(Pin(3)); led_g.freq(1000)
led_b = PWM(Pin(4)); led_b.freq(1000)

led_tank_empty = Pin(5, Pin.OUT)
led_pump       = Pin(6, Pin.OUT)

pump_state = False
last_temp  = None
last_hum   = None
last_dist  = None

def read_dht():
    try:
        dht_sensor.measure()
        return dht_sensor.temperature(), dht_sensor.humidity()
    except Exception as e:
        print("DHT22 error:", e)
        return None, None

def read_distance():
    try:
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
        return round((duration * 0.0343) / 2, 1)
    except Exception as e:
        print("HC-SR04 error:", e)
        return None

def set_rgb(r, g, b):
    led_r.duty_u16(int(r / 255 * 65535))
    led_g.duty_u16(int(g / 255 * 65535))
    led_b.duty_u16(int(b / 255 * 65535))

def apply_temp_color(temp):
    if temp is None:
        set_rgb(0, 0, 0)
        return
    if temp < 18:
        set_rgb(0, 0, 255)
    elif temp <= 28:
        set_rgb(0, 255, 0)
    else:
        set_rgb(255, 0, 0)

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Conectando a", WIFI_SSID, "...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        for _ in range(30):
            if wlan.isconnected():
                break
            time.sleep(1)
    return wlan.ifconfig()[0] if wlan.isconnected() else None

HTML_PAGE = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Monitor de Tanque</title>
  <meta http-equiv="refresh" content="5">
  <style>
    :root {{ --bg:#0f172a; --card:#1e293b; --border:#334155;
             --txt:#f1f5f9; --muted:#94a3b8; }}
    * {{ box-sizing:border-box; margin:0; padding:0; }}
    body {{ font-family:system-ui,sans-serif; background:var(--bg);
            color:var(--txt); min-height:100vh; padding:24px 16px; }}
    h1  {{ font-size:1.4rem; font-weight:600; margin-bottom:6px; }}
    .sub{{ color:var(--muted); font-size:.85rem; margin-bottom:28px; }}
    .grid{{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
            gap:16px; margin-bottom:24px; }}
    .card{{ background:var(--card); border:1px solid var(--border);
            border-radius:12px; padding:20px; }}
    .label{{ font-size:.75rem; color:var(--muted); text-transform:uppercase;
             letter-spacing:.05em; margin-bottom:8px; }}
    .value{{ font-size:2rem; font-weight:700; }}
    .unit {{ font-size:1rem; font-weight:400; color:var(--muted); margin-left:4px; }}
    .badge{{ display:inline-block; padding:4px 12px; border-radius:99px;
             font-size:.8rem; font-weight:500; }}
    .frio     {{ background:#1d4ed8; color:#bfdbfe; }}
    .moderado {{ background:#15803d; color:#bbf7d0; }}
    .caliente {{ background:#b91c1c; color:#fecaca; }}
    .vacio    {{ background:#7c3aed; color:#ede9fe; }}
    .ok       {{ background:#155e75; color:#cffafe; }}
    .pump-card{{ background:var(--card); border:1px solid var(--border);
                 border-radius:12px; padding:24px; display:flex;
                 align-items:center; justify-content:space-between;
                 margin-bottom:24px; }}
    .pump-label{{ font-size:1rem; font-weight:500; }}
    .pump-sub  {{ font-size:.8rem; color:var(--muted); margin-top:4px; }}
    .btn{{ padding:10px 28px; border:none; border-radius:8px; font-size:.9rem;
           font-weight:600; cursor:pointer; }}
    .btn.on {{ background:#22c55e; color:#000; }}
    .btn.off{{ background:#ef4444; color:#fff; }}
    .footer{{ color:var(--muted); font-size:.75rem; text-align:center; margin-top:8px; }}
    .dot{{ display:inline-block; width:8px; height:8px; border-radius:50%;
           background:#22c55e; margin-right:6px;
           animation:pulse 2s ease-in-out infinite; }}
    @keyframes pulse{{ 0%,100%{{opacity:1}}50%{{opacity:.4}} }}
  </style>
</head>
<body>
  <h1>Monitor de Tanque</h1>
  <p class="sub"><span class="dot"></span>Actualizando cada 5 segundos</p>

  <div class="grid">
    <div class="card">
      <div class="label">Temperatura</div>
      <div class="value">{temp}<span class="unit">&deg;C</span></div>
      <div style="margin-top:10px"><span class="badge {range_class}">{range_label}</span></div>
    </div>
    <div class="card">
      <div class="label">Humedad</div>
      <div class="value">{hum}<span class="unit">%</span></div>
    </div>
    <div class="card">
      <div class="label">Nivel del tanque</div>
      <div class="value">{dist}<span class="unit">cm</span></div>
      <div style="margin-top:10px"><span class="badge {tank_class}">{tank_label}</span></div>
    </div>
  </div>

  <div class="pump-card">
    <div>
      <div class="pump-label">Bomba de agua</div>
      <div class="pump-sub">Estado actual: <strong>{pump_status}</strong></div>
    </div>
    <form method="get" action="/pump">
      <button class="btn {pump_btn_class}" type="submit">{pump_btn_label}</button>
    </form>
  </div>

  <p class="footer">Pico W &mdash; IP: {ip_addr}</p>
</body>
</html>"""

def build_page(temp, hum, dist, pump_on, ip):
    t_str = str(temp) if temp is not None else "--"
    h_str = str(hum)  if hum  is not None else "--"
    d_str = str(dist) if dist is not None else "--"

    if temp is None:
        rc, rl = "", "sin datos"
    elif temp < 18:
        rc, rl = "frio",     "Frio"
    elif temp <= 28:
        rc, rl = "moderado", "Moderado"
    else:
        rc, rl = "caliente", "Caliente"

    if dist is None or dist >= 10:
        tc, tl = "ok",    "Nivel OK"
    else:
        tc, tl = "vacio", "Casi vacio"

    return HTML_PAGE.format(
        temp=t_str, hum=h_str, dist=d_str,
        range_class=rc, range_label=rl,
        tank_class=tc, tank_label=tl,
        pump_status="ENCENDIDA" if pump_on else "APAGADA",
        pump_btn_class="off" if pump_on else "on",
        pump_btn_label="Apagar bomba" if pump_on else "Encender bomba",
        ip_addr=ip,
    )

def refresh_sensors():
    global last_temp, last_hum, last_dist
    last_temp, last_hum = read_dht()
    last_dist = read_distance()

    apply_temp_color(last_temp)

    if last_dist is not None and last_dist < 10:
        led_tank_empty.on()
    else:
        led_tank_empty.off()

def handle_one_request(server_sock, ip):
    global pump_state
    conn = None
    try:
        conn, peer = server_sock.accept()
        conn.settimeout(3)
        req = b""
        while b"\r\n\r\n" not in req:
            chunk = conn.recv(256)
            if not chunk:
                break
            req += chunk
            if len(req) > 2048:
                break
        req_str = req.decode("utf-8", "ignore")
        line = req_str.split("\r\n")[0] if req_str else "(vacio)"
        print("[SERVER] <-", peer[0], "|", line)

        if "GET /pump" in req_str:
            pump_state = not pump_state
            led_pump.value(1 if pump_state else 0)
            print("[SERVER] Bomba ->", "ON" if pump_state else "OFF")

        page = build_page(last_temp, last_hum, last_dist, pump_state, ip)
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

    refresh_sensors()
    last_read = time.time()
    last_self_test = time.time()
    counter = 0

    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(addr)
    server.listen(5)
    server.settimeout(0.5)
    print("[SERVER] Escuchando en puerto 80\n")

    while True:
        # Refresco de sensores cada 5s
        if time.time() - last_read >= 5:
            refresh_sensors()
            print("[SENSOR] T={} H={} D={} Bomba={}".format(
                last_temp, last_hum, last_dist, pump_state))
            last_read = time.time()

        # Atender peticiones (con timeout 0.5s)
        handle_one_request(server, ip)

        # Self-test cada 8s
        if time.time() - last_self_test >= 8:
            counter += 1
            path = "/pump" if counter % 3 == 0 else "/"
            print("[CLIENTE] -> envia GET", path)
            self_test_request(path, ip)
            last_self_test = time.time()

main()
