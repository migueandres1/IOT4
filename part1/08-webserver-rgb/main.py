"""
Web server para controlar un LED RGB con PWM.
Incluye un cliente interno que prueba el server cada 8s para mantener
la ruta del gateway de Wokwi activa.
"""

import network
import socket
import time
from machine import Pin, PWM

WIFI_SSID     = "Wokwi-GUEST"
WIFI_PASSWORD = ""

led_r = PWM(Pin(2)); led_r.freq(1000)
led_g = PWM(Pin(3)); led_g.freq(1000)
led_b = PWM(Pin(4)); led_b.freq(1000)

current = (0, 0, 0)

def set_rgb(r, g, b):
    global current
    current = (r, g, b)
    led_r.duty_u16(int(r / 255 * 65535))
    led_g.duty_u16(int(g / 255 * 65535))
    led_b.duty_u16(int(b / 255 * 65535))

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

PAGE = """<!DOCTYPE html><html><head>
<meta charset="UTF-8"><title>Control RGB</title>
<style>
body{{font-family:sans-serif;background:#0f172a;color:#f1f5f9;
     padding:24px;text-align:center}}
h1{{margin-bottom:8px}}
.swatch{{display:inline-block;width:80px;height:80px;border-radius:50%;
         background:rgb({r},{g},{b});border:3px solid #334155;margin:16px}}
.btns a{{display:inline-block;padding:14px 22px;margin:6px;border-radius:8px;
        text-decoration:none;color:#fff;font-weight:600}}
.r{{background:#ef4444}} .g{{background:#22c55e}} .b{{background:#3b82f6}}
.y{{background:#eab308;color:#000}} .c{{background:#06b6d4;color:#000}}
.m{{background:#a855f7}} .w{{background:#fff;color:#000}} .o{{background:#475569}}
</style></head><body>
<h1>Control de LED RGB</h1>
<div class="swatch"></div>
<p>RGB actual: ({r}, {g}, {b})</p>
<div class="btns">
<a class="r" href="/c?r=255&g=0&b=0">Rojo</a>
<a class="g" href="/c?r=0&g=255&b=0">Verde</a>
<a class="b" href="/c?r=0&g=0&b=255">Azul</a>
<a class="y" href="/c?r=255&g=255&b=0">Amarillo</a>
<a class="c" href="/c?r=0&g=255&b=255">Cian</a>
<a class="m" href="/c?r=255&g=0&b=255">Magenta</a>
<a class="w" href="/c?r=255&g=255&b=255">Blanco</a>
<a class="o" href="/c?r=0&g=0&b=0">Apagar</a>
</div></body></html>"""

def parse_color(req):
    try:
        q = req.split(" ")[1].split("?")[1]
        params = dict(p.split("=") for p in q.split("&"))
        return (int(params["r"]), int(params["g"]), int(params["b"]))
    except Exception:
        return None

def handle_one_request(server_sock):
    conn = None
    try:
        conn, peer = server_sock.accept()
        conn.settimeout(3)
        req = conn.recv(1024).decode("utf-8", "ignore")
        line = req.split("\r\n")[0] if req else "(vacio)"
        print("[SERVER] <-", peer[0], "|", line)

        if "GET /c?" in req:
            color = parse_color(req)
            if color:
                set_rgb(*color)
                print("[SERVER] RGB ->", color)

        r, g, b = current
        page = PAGE.format(r=r, g=g, b=b)
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

    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(addr)
    server.listen(5)
    server.settimeout(0.5)
    print("[SERVER] Escuchando en puerto 80\n")

    last_self_test = time.time()
    counter = 0
    # Ciclo de colores para el self-test
    colors = ["/c?r=255&g=0&b=0", "/c?r=0&g=255&b=0", "/c?r=0&g=0&b=255",
              "/c?r=255&g=255&b=0", "/c?r=0&g=0&b=0"]

    while True:
        handle_one_request(server)

        if time.time() - last_self_test >= 8:
            path = colors[counter % len(colors)]
            counter += 1
            print("[CLIENTE] -> envia GET", path)
            self_test_request(path, ip)
            last_self_test = time.time()

main()
