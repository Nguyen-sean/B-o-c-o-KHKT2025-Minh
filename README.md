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