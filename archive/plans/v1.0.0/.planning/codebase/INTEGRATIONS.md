# External Integrations

**Analysis Date:** 2026-03-07

## APIs & External Services

**Hardware Control:**
- KMBox Serial Device - Hardware input simulation (mouse/keyboard)
  - SDK/Client: `pyserial` (`core/ferrum_controller.py`)
  - Connection: COM2 (default) or COM3 (CP210x)
  - Protocol: Text commands over serial @ 115200 baud
  - Commands: `km.move()`, `km.click()`, `km.press()`, `km.wheel()`

**Computer Vision:**
- DXCam - Screen capture via DXGI
  - Library: `dxcam` (`core/vision_engine.py`)
  - Output: BGR format frames
  - Method: GPU-accelerated desktop duplication

- RapidOCR - Optical Character Recognition
  - Library: `rapidocr_onnxruntime`
  - Usage: Account name recognition from game UI
  - Model: ONNX Runtime backend

- OpenCV - Template matching
  - Library: `opencv-python` (cv2)
  - Method: `cv2.matchTemplate()` with `TM_CCOEFF_NORMED`
  - Usage: UI element detection from template images

**Windows System:**
- Win32 API - Cursor position and system integration
  - Library: `pywin32` (`win32api`)
  - Functions: `GetCursorPos()`, `GetAsyncKeyState()`
  - Usage: Mouse tracking and interrupt handling

- Windows DPI Awareness
  - Library: `ctypes`
  - Call: `ctypes.windll.user32.SetProcessDPIAware()`

## Data Storage

**Databases:**
- None - File-based JSON storage only

**File Storage:**
- Local filesystem
  - `account_config.json` - Account character counts
  - `slot_progress_archive.json` - Daily progress tracking
  - `assets/*.png` - Template images for CV matching
  - `debug_*.png` - Debug screenshots (auto-cleaned on startup)

**Caching:**
- In-memory only
  - VisionEngine lazy-loads OCR model on first use
  - Slot progress cached in memory during execution

## Authentication & Identity

**Auth Provider:**
- None - No external authentication
- Account identification via OCR from game UI
- Regex cleaning: `re.sub(r'[^\w\u4e00-\u9fa5]', '', text)`

## Monitoring & Observability

**Error Tracking:**
- None - Console print statements only
- Pattern: `print(f"[标签] 消息")`
- Exception handling with `traceback.print_exc()`

**Logs:**
- Console output only
- No structured logging framework
- Key events logged: task start/stop, character switches, donations

## CI/CD & Deployment

**Hosting:**
- Desktop executable (not cloud-hosted)
- Distribution: Manual file copy

**CI Pipeline:**
- None - Manual build process
- Build command: `pyinstaller FerrumBot_v1.spec`
- Output: `dist/FerrumBot_v1.exe`

## Environment Configuration

**Required env vars:**
- None - All config in JSON files

**Secrets location:**
- No secrets management
- Hardware connection via serial port (local only)

## Webhooks & Callbacks

**Incoming:**
- None - No network services

**Outgoing:**
- None - No network calls

## Hardware Dependencies

**KMBox Device:**
- USB serial device (CP210x chip)
- Default port: COM2
- Alternative: COM3 (CP210x detection)
- Baudrate: 115200
- Protocol: Text commands terminated with `\r\n`

**Input Simulation:**
- HID key codes hardcoded:
  - 24 = U key
  - 38 = Up arrow
  - 40 = Down arrow / Enter
  - 41 = ESC
  - 226 = Left Alt

**Screen Requirements:**
- Resolution: 2560x1440 (hardcoded coordinates)
- Color format: BGR (OpenCV standard)
- GPU acceleration: DXCam uses DXGI

---

*Integration audit: 2026-03-07*
