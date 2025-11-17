# fire_rx_wait2min.py
# ESP32-C6 / MicroPython ≥1.22
# RX: Rung theo SOS khi có cháy, chờ 2 phút sau khi hết cháy mới cho phép sleep

import network, espnow, machine, time, ujson, ubinascii

# =======================
# Cấu hình phần cứng
# =======================
VIB_PIN = 17
LED_PIN = 10
ADC_BAT_PIN = 0
ADC_VBUS_PIN = 1

FS_VOLTAGE = 3.9
DIV_RATIO = 2.0
SCALE = 1.05

LISTEN_TIME_MS = 2000
SLEEP_TIME_MS = 20000
ALERT_HOLD_MS = 5 * 60 * 1000     # Giữ thức 5 phút khi cháy
CLEAR_WAIT_MS = 2 * 60 * 1000     # 💡 Giữ thức 2 phút sau khi hết cháy
VBUS_CHECK_MS = 1000
CHANNEL = 1

BROADCAST = b'\xff' * 6

# SOS pattern (on/off luân phiên)
sos_pattern = [200,200,200,200,200,600,200,600,200,600,200,200,200,200,200]

# =======================
# I/O setup
# =======================
vib = machine.Pin(VIB_PIN, machine.Pin.OUT)
led = machine.Pin(LED_PIN, machine.Pin.OUT)
vib.off(); led.off()

adc_bat = machine.ADC(machine.Pin(ADC_BAT_PIN))
adc_vbus = machine.ADC(machine.Pin(ADC_VBUS_PIN))
for a in (adc_bat, adc_vbus):
    a.atten(machine.ADC.ATTN_11DB)
    a.width(machine.ADC.WIDTH_12BIT)

def read_battery():
    raw = adc_bat.read()
    v_adc = (raw / 4095) * FS_VOLTAGE
    return v_adc * DIV_RATIO * SCALE

def read_vbus():
    raw = adc_vbus.read()
    v_adc = (raw / 4095) * FS_VOLTAGE
    return v_adc * DIV_RATIO

def is_usb():
    return read_vbus() > 4.0

# =======================
# Wi-Fi + ESP-NOW
# =======================
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
    time.sleep_ms(200)
    return sta, ap

def init_espnow():
    sta, ap = wifi_reset()
    e = espnow.ESPNow(); e.active(True)
    try: e.add_peer(BROADCAST)
    except OSError: pass
    mac = ubinascii.hexlify(sta.config('mac')).decode()
    print("✅ RX MAC:", mac)
    return e, mac, sta

def send_ack(e, mac, mode):
    data = {
        "mac": mac,
        "battery": round(read_battery(), 2),
        "mode": mode,
        "rtc": int(time.time())
    }
    try: e.send(BROADCAST, ujson.dumps(data), False)
    except: pass

# =======================
# Rung SOS không blocking
# =======================
def sos_update(state):
    now = time.ticks_ms()
    if now >= state["next"]:
        if state["on"]:
            vib.off(); led.off()
            state["on"] = False
        else:
            vib.on(); led.on()
            state["on"] = True
        duration = state["pattern"][state["idx"]]
        state["next"] = time.ticks_add(now, duration)
        state["idx"] = (state["idx"] + 1) % len(state["pattern"])

# =======================
# USB mode (liên tục)
# =======================
def mode_usb(e, mac):
    print("⚡ USB mode → hoạt động liên tục")
    alarm_state = False
    sos_state = {"pattern": sos_pattern, "idx": 0, "next": time.ticks_ms(), "on": False}
    last_ack = time.ticks_ms()
    last_vbus = time.ticks_ms()

    while True:
        try:
            host, msg = e.recv(300)
            if msg:
                data = ujson.loads(msg)
                alerts = data.get("alerts", [])
                if alerts and not alarm_state:
                    alarm_state = True
                    print("🔥 Báo cháy Zone:", alerts)
                elif not alerts and alarm_state:
                    print("✅ Hết cháy → dừng rung")
                    vib.off(); led.off()
                    alarm_state = False
                    sos_state["on"] = False
        except: pass

        if alarm_state:
            sos_update(sos_state)

        if time.ticks_diff(time.ticks_ms(), last_ack) > 5000:
            send_ack(e, mac, "active"); last_ack = time.ticks_ms()

        if time.ticks_diff(time.ticks_ms(), last_vbus) > VBUS_CHECK_MS:
            last_vbus = time.ticks_ms()
            if not is_usb():
                print("🔋 USB rút → sang battery mode")
                vib.off(); led.off()
                return "battery"

        time.sleep_ms(50)

# =======================
# Battery mode
# =======================
def mode_battery():
    print("🔋 Battery mode → deep sleep sau khi ổn định")
    e, mac, sta = init_espnow()
    start = time.ticks_ms()
    alarm_state = False
    sos_state = {"pattern": sos_pattern, "idx": 0, "next": time.ticks_ms(), "on": False}
    alert_start = None
    clear_time = None
    last_ack = start
    last_vbus = start

    while True:
        elapsed = time.ticks_diff(time.ticks_ms(), start)
        try:
            host, msg = e.recv(200)
            if msg:
                data = ujson.loads(msg)
                alerts = data.get("alerts", [])
                if alerts:
                    if not alarm_state:
                        print("🔥 Báo cháy Zone:", alerts)
                        alarm_state = True
                    if alert_start is None:
                        alert_start = time.ticks_ms()
                    clear_time = None  # huỷ đếm hết cháy
                else:
                    # khi nhận hết cháy
                    if alarm_state:
                        alarm_state = False
                        print("✅ Nhận HẾT CHÁY → bắt đầu đếm 2 phút...")
                        vib.off(); led.off()
                        sos_state["on"] = False
                        alert_start = None
                        clear_time = time.ticks_ms()
        except: pass

        if alarm_state:
            sos_update(sos_state)

        # ACK định kỳ
        if time.ticks_diff(time.ticks_ms(), last_ack) > 5000:
            send_ack(e, mac, "active"); last_ack = time.ticks_ms()

        # Kiểm tra USB
        if time.ticks_diff(time.ticks_ms(), last_vbus) > VBUS_CHECK_MS:
            last_vbus = time.ticks_ms()
            if is_usb():
                print("⚡ USB cắm → sang USB mode")
                vib.off(); led.off()
                return "usb"

        # Giữ thức khi cháy
        if alert_start:
            if time.ticks_diff(time.ticks_ms(), alert_start) > ALERT_HOLD_MS:
                print("✅ Quá 5 phút, có thể ngủ lại.")
                break

        # Khi hết cháy → chờ thêm 2 phút
        if clear_time:
            if time.ticks_diff(time.ticks_ms(), clear_time) > CLEAR_WAIT_MS:
                print("💤 Đã yên 2 phút → cho phép sleep.")
                break

        # Nếu yên tĩnh 2s mà chưa cháy
        if not alarm_state and not clear_time and elapsed > LISTEN_TIME_MS:
            break

        time.sleep_ms(50)

    send_ack(e, mac, "sleep")
    vib.off(); led.off()
    try: e.active(False)
    except: pass
    try: sta.active(False)
    except: pass
    print("🌙 Deep sleep 20s...")
    machine.deepsleep(SLEEP_TIME_MS)

# =======================
# Main
# =======================
print("=== RX khởi động ===")
print("VBUS:", round(read_vbus(),2), "V | Pin:", round(read_battery(),2), "V")

e, mac, sta = init_espnow()
while True:
    if is_usb():
        res = mode_usb(e, mac)
        if res == "battery":
            e.active(False); sta.active(False)
            e, mac, sta = init_espnow()
    else:
        res = mode_battery()
        if res == "usb":
            e, mac, sta = init_espnow()
