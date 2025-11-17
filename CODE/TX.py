# fire_tx.py
# ESP32 / MicroPython ≥1.22
# TX: Gửi cảnh báo cháy qua ESP-NOW, xác nhận hết cháy sau 10 giây ổn định

import network, espnow, machine, time, ujson, ubinascii

# ==========================
# Cấu hình phần cứng
# ==========================
ZONE_PINS = [4, 5, 6, 7, 0, 1, 2, 3]  # 8 Zone input
SEND_INTERVAL_MS = 200
CLEAR_CONFIRM_MS = 10_000
CHANNEL = 1
BROADCAST = b'\xff' * 6

# ==========================
# Chuẩn bị I/O
# ==========================
pins = [machine.Pin(p, machine.Pin.IN, machine.Pin.PULL_UP) for p in ZONE_PINS]

def read_zones():
    """Đọc zone, active-low (0 = kích hoạt)"""
    return [1 if pin.value() == 0 else 0 for pin in pins]

def active_zones(zones):
    return [i + 1 for i, v in enumerate(zones) if v]

# ==========================
# Wi-Fi + ESP-NOW
# ==========================
def wifi_reset():
    sta = network.WLAN(network.WLAN.IF_STA)
    ap = network.WLAN(network.WLAN.IF_AP)
    ap.active(False)
    sta.active(False)
    time.sleep_ms(50)
    sta.active(True)
    try: sta.disconnect()
    except: pass
    try: sta.config(channel=CHANNEL)
    except: pass
    return sta, ap

def init_espnow():
    sta, ap = wifi_reset()
    e = espnow.ESPNow()
    e.active(True)
    try: e.add_peer(BROADCAST)
    except OSError: pass
    mac = ubinascii.hexlify(sta.config('mac')).decode()
    print("✅ TX MAC:", mac)
    return e

# ==========================
# Gửi dữ liệu
# ==========================
def send_data(e, zones, alerts):
    data = {
        "rtc": time.localtime(),
        "zones": zones,
        "alerts": alerts
    }
    try:
        e.send(BROADCAST, ujson.dumps(data), False)
    except Exception as ex:
        print("⚠️ Send err:", ex)

# ==========================
# Main loop
# ==========================
print("🚨 TX khởi động...")
e = init_espnow()
wdt = machine.WDT(timeout=20_000)

last_send = time.ticks_ms()
last_state = read_zones()
last_alert = bool(any(last_state))
clear_timer = None
clear_sent = False

while True:
    wdt.feed()
    zones = read_zones()
    alerts = active_zones(zones)
    now = time.ticks_ms()
    fire_active = bool(alerts)

    # ==== Khi có cháy ====
    if fire_active:
        clear_timer = None
        clear_sent = False
        if time.ticks_diff(now, last_send) >= SEND_INTERVAL_MS:
            send_data(e, zones, alerts)
            last_send = now
            print("🔥 Gửi cháy:", alerts)

    # ==== Khi hết cháy ====
    else:
        if last_alert and clear_timer is None:
            clear_timer = now
            print("🕒 Kiểm tra hết cháy (10s)...")

        if clear_timer:
            # Nếu lại cháy → huỷ kiểm tra
            if fire_active:
                clear_timer = None
                print("❌ Lại cháy → reset timer")
            else:
                # Ổn định đủ 10s
                if time.ticks_diff(now, clear_timer) >= CLEAR_CONFIRM_MS and not clear_sent:
                    send_data(e, zones, [])
                    clear_sent = True
                    print("✅ Gửi HẾT CHÁY (ổn định 10s)")
                    try:
                        with open("fire_log.txt", "a") as f:
                            t = time.localtime()
                            f.write(f"{t[3]:02d}:{t[4]:02d}:{t[5]:02d} CLEAR\n")
                    except: pass

        # Gửi heartbeat mỗi 1 giây
        if time.ticks_diff(now, last_send) >= 1000:
            send_data(e, zones, [])
            last_send = now

    last_state = zones
    last_alert = fire_active
    time.sleep_ms(50)

