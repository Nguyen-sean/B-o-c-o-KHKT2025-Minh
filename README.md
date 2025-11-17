# Hệ Thống Phát Hiện & Cảnh Báo Cháy

Hệ thống phát hiện cháy phân tán được xây dựng trên các vi điều khiển ESP32 sử dụng MicroPython và giao tiếp không dây ESP-NOW. Hệ thống theo dõi 8 khu vực phát hiện cháy và gửi cảnh báo theo thời gian thực với cảnh báo rung động/LED.

## 🏗️ Kiến Trúc Hệ Thống

### Các Thành Phần

**TX (Nút Phát Tín Hiệu)**
- Theo dõi 8 khu vực phát hiện cháy qua các chân GPIO
- Gửi cảnh báo cháy qua phát sóng ESP-NOW
- Thực hiện logic xác nhận hết cháy trong 10 giây
- Ghi lại sự kiện cháy vào bộ nhớ
- Bảo vệ watchdog 20 giây

**RX (Nút Thu Tín Hiệu)**
- Nhận cảnh báo cháy và cập nhật trạng thái
- Kích hoạt mô hình rung động SOS qua động cơ rung
- Đèn LED chỉ báo đồng bộ
- Quản lý năng lượng hai chế độ:
  - **Chế độ USB**: Hoạt động liên tục khi được cấp điện
  - **Chế độ Pin**: Tối ưu hóa ngủ sâu với chu kỳ thức dậy

## 🔧 Yêu Cầu Phần Cứng

### Nút TX
- Vi điều khiển ESP32
- 8 cảm biến phát hiện cháy (GPIO 4-7, 0-3)
- Cấu hình đầu vào active-low với pull-up
- MicroPython ≥1.22

### Nút RX
- Vi điều khiển ESP32-C6 (hoặc ESP32 tương thích)
- Động cơ rung động (GPIO 17)
- Đèn LED chỉ báo (GPIO 10)
- Giám sát điện áp pin (ADC Pin 0)
- Phát hiện VBUS USB (ADC Pin 1)
- MicroPython ≥1.22

## 📡 Giao Thức Giao Tiếp

### Cấu Hình ESP-NOW
- **Kênh**: Cố định ở kênh 1 cho cả hai nút
- **Địa chỉ Phát Sóng**: `FF:FF:FF:FF:FF:FF`
- **Độ Trễ**: Siêu thấp (chế độ phát sóng)

### Định Dạng Thông Điệp TX → RX
```json
{
  "rtc": [2025, 11, 18, 14, 30, 45, 0, 0],
  "zones": [0, 1, 0, 1, 0, 0, 0, 0],
  "alerts": [2, 4]
}
```
- `zones`: Mảng 8 giá trị nhị phân (1 = phát hiện cháy)
- `alerts`: Danh sách số khu vực đang hoạt động (1-8)

### Nhịp Tim/Xác Nhận RX → TX
```json
{
  "mac": "aabbccddeeff",
  "battery": 3.45,
  "mode": "active",
  "rtc": 1734624645
}
```

## 🚀 Cài Đặt & Triển Khai

### 1. Flash MicroPython
Tải MicroPython ≥1.22 cho biến thể ESP32 của bạn và flash:
```bash
esptool.py -p COM3 erase_flash
esptool.py -p COM3 write_flash -z 0x1000 firmware.bin
```

### 2. Tải Mã
Chuyển các tệp tới thiết bị:
```
CODE/
  ├── TX.py    → Flash tới nút TX
  └── RX.py    → Flash tới nút RX
```

### 3. Khởi Động & Giám Sát
Kết nối cổng nối tiếp và kiểm tra đầu ra:
```
✅ TX MAC: a1b2c3d4e5f6
✅ RX MAC: f6e5d4c3b2a1
```

## ⚙️ Cấu Hình

### Nút TX (`TX.py`)

| Tham Số | Giá Trị | Mục Đích |
|---------|--------|---------|
| `ZONE_PINS` | `[4,5,6,7,0,1,2,3]` | Các chân GPIO cho 8 khu vực |
| `SEND_INTERVAL_MS` | 200 | Tần suất phát sóng cảnh báo cháy |
| `CLEAR_CONFIRM_MS` | 10000 | Độ ổn định cần thiết trước khi xóa cháy (10s) |
| `CHANNEL` | 1 | Kênh WiFi cho ESP-NOW |

**Sửa Đổi Khu Vực:**
```python
ZONE_PINS = [4, 5, 6, 7, 0, 1, 2, 3, 15, 16]  # Ví dụ 10 khu vực
# Số khu vực = chỉ số + 1 (không bao giờ là Khu Vực 0)
```

### Nút RX (`RX.py`)

| Tham Số | Giá Trị | Mục Đích |
|---------|--------|---------|
| `ALERT_HOLD_MS` | 300000 | Thức dậy 5 phút trong lúc cháy |
| `CLEAR_WAIT_MS` | 120000 | Thức dậy 2 phút sau khi cháy kết thúc |
| `LISTEN_TIME_MS` | 2000 | Thời gian thức dậy tối thiểu trước khi cho phép ngủ |
| `SLEEP_TIME_MS` | 20000 | Khoảng thời gian ngủ sâu (20s) |
| `VBUS_CHECK_MS` | 1000 | Tần suất kiểm tra USB |

**Điều Chỉnh Thời Gian Thức Dậy:**
```python
ALERT_HOLD_MS = 10 * 60 * 1000   # 10 phút trong lúc cảnh báo
CLEAR_WAIT_MS = 5 * 60 * 1000    # 5 phút sau khi xóa
```

## 🔄 Chế Độ Hoạt Động

### Hành Vi TX

**Phát Hiện Cháy** (Chân Zone = LOW)
```
1. Ngay lập tức phát sóng cảnh báo với danh sách khu vực mỗi 200ms
2. Tiếp tục gửi khi cháy vẫn còn
3. Ghi vào fire_log.txt khi cuối cùng hết cháy
```

**Hết Cháy** (Tất cả Chân Zone = HIGH)
```
1. Chờ 10 giây xác nhận độ ổn định
2. Nếu cháy tiếp → khởi động lại bộ đếm
3. Nếu 10s qua → gửi mảng cảnh báo trống
4. Thêm "HH:MM:SS CLEAR" vào fire_log.txt
```

**Nhịp Tim** (Không Có Cháy)
```
1. Gửi zones/alerts trống mỗi 1 giây
2. Giữ liên kết giao tiếp hoạt động
3. Cho phép RX phát hiện TX ngoại tuyến
```

### Hành Vi RX - Chế Độ USB
- Được cấp điện qua cáp USB
- Hoạt động liên tục
- Phản ứng cảnh báo tức thì
- Rung động SOS khi cảnh báo cháy
- Thoát khi rút USB

### Hành Vi RX - Chế Độ Pin
- Ngủ sâu giữa các chu kỳ lắng nghe
- Thức dậy mỗi 20 giây
- Lắng nghe 2 giây mỗi chu kỳ
- **Giai Đoạn Cảnh Báo**: Thức dậy tối thiểu 5 phút
- **Giai Đoạn Xóa**: Thức dậy thêm 2 phút
- Quay lại ngủ sau khi ổn định

## 📊 Mô Hình Rung Động (SOS)

RX phát mã Morse SOS qua động cơ rung:
```
. . . - - - . . .
(3 ngắn, 3 dài, 3 ngắn)

Thời gian: [200,200,200,200,200,600,200,600,200,600,200,200,200,200,200] ms
```

Mô hình lặp liên tục cho đến khi cháy kết thúc.

## 🔋 Quản Lý Năng Lượng (RX)

### Giám Sát Pin
- **ADC Pin 0**: Điện áp pin (tỷ lệ chia 2.0, scale 1.05, FS 3.9V)
- **ADC Pin 1**: Phát hiện VBUS (ngưỡng 4.0V cho sự hiện diện USB)

### Chiến Lược Ngủ Sâu
```
USB Kết Nối → Chế Độ Liên Tục
        ↓
    Cảnh Báo Cháy
        ↓
    Rung SOS + Thức Dậy 5 phút
        ↓
    Cháy Kết Thúc
        ↓
    Thức Dậy 2 phút nữa → Sau Đó Ngủ 20s
```

## 📝 Ghi Nhật Ký

Nút TX tạo `fire_log.txt` với dấu thời gian xóa:
```
14:30:45 CLEAR
14:35:12 CLEAR
14:45:08 CLEAR
```

Hữu ích cho việc kiểm toán lịch sử sự kiện cháy.

## 🐛 Khắc Phục Sự Cố

| Sự Cố | Giải Pháp |
|-------|----------|
| Rung RX không hoạt động khi cháy | Kiểm tra danh sách cảnh báo không trống trong phát sóng TX |
| RX không ngủ trong chế độ pin | Xác minh `LISTEN_TIME_MS` < thời gian giữ cảnh báo |
| Wifi reset thất bại | Tăng sleep_ms delay sau các lệnh `sta.active()` |
| Trạng thái mô hình bị gãy | Đừng tạo lại từ điển `sos_state` giữa mô hình |
| Số khu vực sai | Nhớ: Khu Vực = chỉ số + 1 (Khu Vực 1-8, không bao giờ là 0) |
| Lỗi ghi tệp | TX im lặng bỏ qua nếu SD không gắn |

## 🔐 Logic Active-Low

**QUAN TRỌNG**: Cảm biến cháy là active-LOW:
- **Cảm biến kích hoạt** → GPIO chuyển sang LOW (0)
- **Trong mã**: `pin.value() == 0` → `zones[i] = 1`
- **Khu vực hoạt động**: Chỉ các chỉ số khác không xuất hiện trong cảnh báo

Ví dụ:
```python
# Nếu GPIO 4 (Khu Vực 1) có cháy:
zones = [1, 0, 0, 0, 0, 0, 0, 0]
alerts = [1]  # Khu Vực 1 đang hoạt động

# Nếu GPIO 5 (Khu Vực 2) cũng có cháy:
zones = [1, 1, 0, 0, 0, 0, 0, 0]
alerts = [1, 2]  # Khu Vực 1 & 2 đang hoạt động
```

## 📚 Cấu Trúc Tệp

```
CODE/
├── TX.py              # Nút phát (phát hiện cháy & phát sóng)
└── RX.py              # Nút thu (cảnh báo & điều khiển rung)

.github/
└── copilot-instructions.md  # Hướng dẫn phát triển cho tác nhân AI
```

## 🛠️ Mẹo Phát Triển

### Thêm Khu Vực Mới
1. Mở rộng mảng `ZONE_PINS` trong TX.py
2. Số khu vực tự động suy ra: pin mới = khu vực N+1
3. RX xử lý động theo bất kỳ số lượng cảnh báo nào

### Kiểm Tra Mà Không Có Phần Cứng
Mô phỏng `machine.Pin()` và `machine.ADC()` để trả về giá trị cố định:
```python
class MockPin:
    def __init__(self, num, mode, pull=None):
        self.value_state = 0
    def value(self, val=None):
        return self.value_state
    def on(self): pass
    def off(self): pass
```

### Gỡ Lỗi Giao Tiếp
Thêm vào RX để xác minh thông điệp đến:
```python
host, msg = e.recv(300)
if msg:
    print("Nhận được:", msg)
    data = ujson.loads(msg)
    print("Cảnh báo:", data.get("alerts"))
```


