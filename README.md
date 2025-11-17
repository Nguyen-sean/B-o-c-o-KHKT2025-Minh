# Hệ Thống Phát Hiện & Cảnh Báo Cháy

ESP32 · MicroPython · ESP-NOW — Hệ thống cảnh báo cháy thời gian thực dành cho người khiếm thính/khiếm thanh.

## Mục Lục
- [Giới thiệu](#giới-thiệu)
- [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
  - [TX (Bộ phát)](#tx-bộ-phát)
  - [RX (Bộ nhận)](#rx-bộ-nhận)
- [Phần cứng](#phần-cứng)
- [Giao tiếp ESP-NOW](#giao-tiếp-esp-now)
- [Định dạng thông điệp](#định-dạng-thông-điệp)
- [Cài đặt & Triển khai](#cài-đặt--triển-khai)
- [Cấu hình chính](#cấu-hình-chính)
- [Hành vi hệ thống](#hành-vi-hệ-thống)
- [Mã rung SOS](#mã-rung-sos)
- [Quản lý năng lượng (RX)](#quản-lý-năng-lượng-rx)
- [Cấu trúc dự án](#cấu-trúc-dự-án)
- [Mẹo phát triển & Kiểm thử](#mẹo-phát-triển--kiểm-thử)
- [Mục tiêu dự án](#mục-tiêu-dự-án)

## Giới thiệu

Dự án xây dựng hệ thống phát hiện và cảnh báo cháy phân tán dựa trên ESP32 chạy MicroPython. Hệ thống nhận tín hiệu từ 8 zone (active-low), truyền cảnh báo theo broadcast qua ESP-NOW và đưa ra cảnh báo rung/LED trên thiết bị nhận.

## Kiến trúc hệ thống

### TX (Bộ phát)
- Đọc 8 zone báo cháy (active-low) qua các chân GPIO.
- Chuyển đổi an toàn từ tín hiệu 24V qua optocoupler (PC817).
- Gửi dữ liệu dạng JSON qua ESP-NOW (broadcast).
- Ghi nhật ký "CLEAR" vào `fire_log.txt` khi xác nhận hết cháy.
- Watchdog 20s đảm bảo tự phục hồi.

### RX (Bộ nhận)
- Nhận gói tin broadcast từ TX.
- Kích hoạt mô hình rung SOS và LED đồng bộ khi cảnh báo.
- Quản lý nguồn: chế độ USB (liên tục) và chế độ Pin (deep sleep, chu kỳ nghe).

## Phần cứng

- TX: ESP32, 8 optocoupler PC817, screw terminals cho 8 zone.
- RX: ESP32 (ví dụ ESP32-C6), động cơ rung (GPIO 17), LED (GPIO 10), ADC đo pin (ADC0) và VBUS (ADC1).

## Giao tiếp ESP-NOW

- Kênh mặc định: `1`.
- Địa chỉ broadcast: `FF:FF:FF:FF:FF:FF`.
- Dữ liệu truyền là chuỗi JSON (`ujson.dumps()`).

## Định dạng thông điệp

### Gói TX → RX
```json
{
  "rtc": [2025,11,18,14,30,45,0,0],
  "zones": [0,1,0,1,0,0,0,0],
  "alerts": [2,4]
}
```
- `zones`: mảng 8 phần tử (1 = phát hiện cháy tại zone tương ứng).
- `alerts`: danh sách các số zone đang cháy (zone bắt đầu từ 1).

### Gói RX → TX (ACK / Heartbeat)
```json
{
  "mac": "aabbccddeeff",
  "battery": 3.45,
  "mode": "active",
  "rtc": 1734624645
}
```

## Cài đặt & Triển khai

### 1. Flash MicroPython
```bash
esptool.py -p COM3 erase_flash
esptool.py -p COM3 write_flash -z 0x1000 firmware.bin
```

### 2. Tải mã nguồn lên thiết bị
Chép `TX.py` lên thiết bị đóng vai TX và `RX.py` lên thiết bị đóng vai RX (qua ampy, rshell, mpremote, hoặc tool tương tự).

## Cấu hình chính

### `TX.py` (tham số quan trọng)

| Tên | Mô tả | Mặc định |
|-----|-------|---------|
| `ZONE_PINS` | Danh sách GPIO đọc 8 zone | `[4,5,6,7,0,1,2,3]` |
| `SEND_INTERVAL_MS` | Tần suất gửi khi cháy | `200` ms |
| `CLEAR_CONFIRM_MS` | Thời gian ổn định để xác nhận hết cháy | `10000` ms (10s) |
| `CHANNEL` | Kênh ESP-NOW | `1` |

### `RX.py` (tham số quan trọng)

| Tên | Mô tả | Mặc định |
|-----|-------|---------|
| `ALERT_HOLD_MS` | Giữ thức khi đang cháy | `300000` ms (5 phút) |
| `CLEAR_WAIT_MS` | Thời gian giữ thêm sau khi hết cháy | `120000` ms (2 phút) |
| `LISTEN_TIME_MS` | Thời gian tối thiểu để nghe | `2000` ms |
| `SLEEP_TIME_MS` | Thời gian deep sleep | `20000` ms (20s) |

## Hành vi hệ thống

### TX
- Khi phát hiện cháy: gửi danh sách `alerts` mỗi `SEND_INTERVAL_MS` (mặc định 200ms).
- Khi tất cả zone không còn cháy: khởi tạo bộ đếm `CLEAR_CONFIRM_MS` (10s). Nếu ổn định trong 10s, gửi mảng `alerts` rỗng và ghi `HH:MM:SS CLEAR` vào `fire_log.txt`.
- Khi không có cháy, gửi heartbeat mỗi 1 giây.

### RX
- **Chế độ USB**: hoạt động liên tục, rung/LED khi nhận `alerts` không rỗng; gửi ACK định kỳ.
- **Chế độ Pin**: wake-sleep chu kỳ (deep sleep). Khi cháy → giữ thức ít nhất `ALERT_HOLD_MS`. Khi hết cháy → giữ thêm `CLEAR_WAIT_MS` trước khi sleep.

## Mã rung SOS

Mô hình Morse SOS: `... --- ...`

Khối thời gian mẫu (ms):
```py
sos_pattern = [200,200,200,200,200,600,200,600,200,600,200,200,200,200,200]
```

RX lặp mô hình này không blocking bằng state machine.

## Quản lý năng lượng (RX)

- ADC đo điện áp pin: `ADC_BAT_PIN` (tỷ lệ chia và scale được định nghĩa trong `RX.py`).
- ADC phát hiện VBUS (USB) để chuyển đổi giữa chế độ USB và Pin.

## Cấu trúc dự án

```
/
├── CODE/
│   ├── TX.py
│   └── RX.py
└── README.md
```

## Mẹo phát triển & Kiểm thử

- Thêm zone mới: mở rộng `ZONE_PINS` trong `TX.py` (zone số = index + 1).

Ví dụ:
```py
ZONE_PINS = [4,5,6,7,0,1,2,3,15,16]  # mở rộng thành 10 zone
```

- Kiểm thử không có phần cứng: mô phỏng `machine.Pin` và `machine.ADC` để trả giá trị cố định.

Ví dụ mô phỏng đơn giản:
```py
class MockPin:
    def __init__(self, v=1):
        self.v = v
    def value(self):
        return self.v
```

## Mục tiêu dự án

- Hỗ trợ người khiếm thính/khiếm thanh bằng cảnh báo rung/LED.
- Độ trễ cảnh báo thấp (<1s trong điều kiện thông thường).
- An toàn: chỉ đọc tín hiệu tủ báo cháy, không can thiệp hay cấp nguồn trở lại tủ.

---

*Cập nhật: Tháng 11/2025 — MicroPython ≥ 1.22*
Hệ Thống Phát Hiện & Cảnh Báo Cháy Cho Người Khiếm Thính/Khiếm Thanh

ESP32 – MicroPython – ESP-NOW – Real-Time Alerting System

1. Giới thiệu

Dự án xây dựng hệ thống cảnh báo cháy phân tán dựa trên ESP32, nhằm hỗ trợ người khiếm thính/khiếm thanh bằng cách cung cấp cảnh báo rung và đèn LED thời gian thực.
Hệ thống lấy tín hiệu trực tiếp từ tủ báo cháy qua mạch cách ly PC817, xử lý bằng ESP32-C3 và phát cảnh báo qua giao thức ESP-NOW.

Hệ thống bao gồm hai thiết bị:

TX (Transmitter): Đọc 8 zone báo cháy từ tủ trung tâm, xử lý và phát cảnh báo.

RX (Receiver): Thiết bị đeo tay/thiết bị phụ trợ nhận cảnh báo và tạo rung/đèn.

2. Kiến trúc hệ thống
2.1. TX – Bộ phát cảnh báo

Đọc tín hiệu báo cháy từ 8 zone (mức active-low).

Sử dụng 8 module PC817 để chuyển 24V → 3.3V an toàn.

Gửi cảnh báo bằng ESP-NOW (broadcast).

Lưu nhật ký vào fire_log.txt.

Xác nhận trạng thái hết cháy sau 10 giây.

Tự động phục hồi bằng watchdog.

2.2. RX – Bộ nhận cảnh báo

Nhận gói tin cảnh báo từ TX bằng ESP-NOW.

Tạo rung động theo mô hình SOS bằng động cơ rung.

Nháy LED đồng bộ với mô hình rung.

Hai chế độ hoạt động:

USB mode: chạy liên tục.

Battery mode: deep sleep tiết kiệm năng lượng.

Giám sát điện áp pin và trạng thái USB bằng ADC.

3. Phần cứng
3.1. Mạch cách ly PC817

Tín hiệu báo cháy 24V được chuyển thành mức 3.3V theo cách ly bằng PC817 để đảm bảo an toàn.
Sơ đồ mạch mỗi zone:

Input_24V → R3 (3KΩ) → PC817 → R4 (10KΩ pull-up 3.3V) → GPIO ESP32


Lợi ích:

Cách ly hoàn toàn giữa tủ báo cháy và ESP32.

Không gây ảnh hưởng đến đường giám sát (supervision).

Chống nhiễu, chống xung điện.

3.2. Bo mạch 8-zone

8 module PC817 hoạt động độc lập.

ESP32-C3 đặt tại trung tâm bo.

Đầu nối screw-terminal cho 8 zone vào.

Mạch cách ly và nguồn được thiết kế an toàn 24/7.

4. Truyền thông ESP-NOW

Độ trễ thấp: 5–20 ms.

Không cần Wi-Fi hoặc router.

Truyền broadcast nhiều thiết bị cùng lúc.

Ổn định trong môi trường có nhiều vật cản.

TX sử dụng địa chỉ broadcast:

FF:FF:FF:FF:FF:FF

5. Định dạng thông điệp
5.1. Gói TX gửi → RX
{
  "rtc": [2025, 11, 18, 14, 30, 45, 0, 0],
  "zones": [0,1,0,1,0,0,0,0],
  "alerts": [2,4]
}


zones: trạng thái 8 khu vực (0 = bình thường, 1 = cháy).

alerts: danh sách zone đang cháy.

5.2. Gói RX gửi → TX (heartbeat)
{
  "mac": "aabbccddeeff",
  "battery": 3.45,
  "mode": "active",
  "rtc": 1734624645
}

6. Cài đặt
6.1. Flash MicroPython
esptool.py -p COM3 erase_flash
esptool.py -p COM3 write_flash -z 0x1000 firmware.bin

6.2. Tải mã nguồn
TX.py → Thiết bị TX
RX.py → Thiết bị RX

7. Cấu hình
7.1. TX.py
Tham số	Mô tả
ZONE_PINS	GPIO đọc 8 zone
SEND_INTERVAL_MS	Chu kỳ gửi cảnh báo (200ms)
CLEAR_CONFIRM_MS	Xác nhận hết cháy (10s)
CHANNEL	Kênh ESP-NOW (1)
7.2. RX.py
Tham số	Mô tả
ALERT_HOLD_MS	Thức 5 phút khi đang cháy
CLEAR_WAIT_MS	Thức 2 phút khi hết cháy
LISTEN_TIME_MS	Lắng nghe tối thiểu
SLEEP_TIME_MS	Chu kỳ deep sleep
VBUS_CHECK_MS	Kiểm tra trạng thái USB
8. Hành vi hệ thống
8.1. TX

Khi phát hiện cháy:

Gửi cảnh báo mỗi 200 ms.

Gửi danh sách zone đang cháy.

Khi hết cháy: đợi 10 giây.

Ghi "CLEAR" vào fire_log.txt.

Khi không cháy:

Gửi heartbeat mỗi 1 giây.

8.2. RX

USB mode:

Hoạt động liên tục.

Rung và nháy LED ngay lập tức.

Battery mode:

Deep sleep 20 giây → Thức 2 giây để nhận → ngủ lại.

Khi cháy: thức 5 phút.

Khi hết cháy: thức 2 phút trước khi ngủ lại.

9. Mã rung SOS

Dạng Morse:

... --- ...


Thời gian rung:

[200,200,200, 600,600,600, 200,200,200] ms

10. Quản lý năng lượng

ADC0: đo điện áp pin.

ADC1: phát hiện USB 5V.

Chuyển đổi tự động USB ↔ Pin.

Chế độ Deep sleep tối ưu hóa thời gian sử dụng.

11. Cấu trúc dự án
/
├── CODE/
│   ├── TX.py
│   └── RX.py
└── README.md

12. Mẹo phát triển
Thêm zone mới
ZONE_PINS = [4,5,6,7,0,1,2,3,15,16]

Mô phỏng không có phần cứng
class MockPin:
    def value(self): return 0

Gỡ lỗi RX
host, msg = e.recv(300)
print(msg)

13. Mục tiêu dự án

Hỗ trợ người khiếm thính/khiếm thanh.

Độ trễ cảnh báo dưới 1 giây.

An toàn tuyệt đối với tủ báo cháy (chỉ đọc, không can thiệp).

Chi phí thấp, dễ lắp đặt, dễ mở rộng.

Vận hành 24/7.