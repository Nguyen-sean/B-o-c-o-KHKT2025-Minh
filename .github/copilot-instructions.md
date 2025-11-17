# Fire Detection System - AI Coding Agent Guide

## Project Overview

This is a **distributed fire detection & alert system** running on ESP32 microcontrollers with MicroPython. It uses ESP-NOW for low-latency wireless communication between two nodes:
- **TX (Transmitter)**: Monitors 8 fire zones via GPIO pins, sends alerts when activated
- **RX (Receiver)**: Receives alerts and triggers vibration/LED warnings with intelligent power management

## Architecture & Communication

### ESP-NOW Protocol
- **Broadcast address**: `b'\xff' * 6` (all devices on channel 1)
- **Channel**: Fixed at 1 across both TX and RX
- **Message format**: JSON strings via `ujson`

### TX → RX Data Flow
```
TX sends: {"rtc": time_tuple, "zones": [0,1,0,1,...], "alerts": [1,4]}
RX sends: {"mac": "...", "battery": 3.45, "mode": "active", "rtc": timestamp}
```

## Critical Patterns & Workflows

### 1. Zone Management (TX)
- **Hardware**: 8 GPIO pins configured as active-low inputs with pull-ups
- **Read pattern**: `zones[i] = 1` when pin reads LOW (fire detected)
- **Active zones**: Computed from index + 1: Zone 1-8 (never Zone 0)
- **Debounce**: Polling every 50ms; fire confirmed if alerts persist across multiple reads

### 2. Alert Confirmation Logic (TX)
- **Fire onset**: Send immediately with zone list on every `SEND_INTERVAL_MS` (200ms)
- **Fire clearing**: Requires 10 seconds (`CLEAR_CONFIRM_MS`) of stability before sending empty alerts
- **Heartbeat**: 1-second interval sends even when no fire (zone & alert arrays empty)
- **Watchdog**: 20-second timeout reset each loop via `machine.WDT()`

### 3. Vibration Patterns (RX)
- **SOS pattern**: Non-blocking state machine in `sos_update()` alternates on/off durations
- **Pattern array**: `[200,200,200,200,200,600,200,600,200,600,200,200,200,200,200]` (ms)
- **Critical**: Pattern loops via modulo; vibration and LED are synchronized

### 4. Power Management (RX)
- **USB mode**: Continuous operation when powered; exits to battery mode on disconnect
- **Battery mode**: Deep sleep after stability periods
- **Hold times**:
  - `ALERT_HOLD_MS = 5 * 60 * 1000`: Stay awake 5 minutes while fire active
  - `CLEAR_WAIT_MS = 2 * 60 * 1000`: Stay awake 2 more minutes after fire clears
  - `LISTEN_TIME_MS = 2000`: Minimum awake time before sleep allowed
- **Battery voltage**: ADC division ratio 2.0, scale factor 1.05; FS voltage 3.9V

### 5. Persistent Logging (TX)
- **File**: `fire_log.txt` (append-only)
- **Entry**: `"HH:MM:SS CLEAR\n"` when fire clears after 10s stability
- **Wrapped in try-except**: Silently skips on file system errors

## Key Developer Tasks

### Adding a New Zone
1. Extend `ZONE_PINS` in TX with new GPIO number
2. Zone number auto-derives from index: len(ZONE_PINS) zones numbered 1 to N
3. Verify RX can handle alert list up to new count (no hard-coded limit)

### Tuning Timings
- **TX fire confirmation**: Modify `CLEAR_CONFIRM_MS` (default 10000 = 10s)
- **RX alert hold**: Modify `ALERT_HOLD_MS` (default 300000 = 5 min)
- **RX post-clear hold**: Modify `CLEAR_WAIT_MS` (default 120000 = 2 min)
- **Heartbeat interval**: Modify TX send loop condition (currently 1000ms)

### Testing Without Hardware
- **Mock pins**: Replace `machine.Pin()` with mock returning fixed values
- **Mock ADC**: Return hardcoded battery/VBUS voltage for RX testing
- **Time simulation**: Advance `time.ticks_ms()` in test loop

## Common Pitfalls

1. **Active-low confusion**: `pin.value() == 0` means fire detected (active), returns 1 in zone array
2. **Zone numbering off-by-one**: Always `i + 1` when converting index to zone number
3. **WiFi reset timing**: 50-200ms delays after state changes are critical for ESP-NOW init
4. **Pattern state persistence**: `sos_state` dict must be preserved across iterations (not recreated)
5. **MAC address caching**: Recalculate after WiFi reset in case hardware changes
6. **JSON serialization**: Both TX ACK and main data use `ujson.dumps()`; handle malformed input gracefully

## Files & Roles

| File | Purpose | Key Exports |
|------|---------|-------------|
| `TX.py` | Fire detection & transmission | `read_zones()`, `send_data()`, zone polling loop |
| `RX.py` | Alert reception & vibration | `mode_usb()`, `mode_battery()`, `sos_update()` state machine |

## Important Hardware Mappings

**TX**:
- Zones: GPIO 4-7, 0-3 (8 total)
- Watchdog: 20s timeout

**RX**:
- Vibrator: GPIO 17
- LED: GPIO 10
- Battery ADC: Pin 0 (voltage divider ratio 2.0)
- VBUS ADC: Pin 1 (USB detection threshold 4.0V)
- Deep sleep interval: 20 seconds
