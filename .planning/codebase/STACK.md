# Technology Stack

**Analysis Date:** 2026-03-07

## Languages

**Primary:**
- Python 3.13.12 - Entire codebase (automation bot, GUI, computer vision, hardware control)

**Secondary:**
- None - Pure Python implementation

## Runtime

**Environment:**
- Python 3.13.12 (Windows)
- Target platform: Windows 10/11 (win32)

**Package Manager:**
- pip (standard Python package manager)
- No lockfile detected (requirements.txt not present)

## Frameworks

**Core:**
- Tkinter (built-in) - GUI interface for launcher (`gui_launcher.py`)
- OpenCV (cv2) - Computer vision and template matching (`core/vision_engine.py`)
- DXCam - Screen capture library for BGR frame capture
- RapidOCR (rapidocr_onnxruntime) - OCR text recognition from screen regions
- PyInstaller - Executable bundling (`FerrumBot_v1.spec`)

**Hardware Interface:**
- pyserial - Serial communication with KMBox hardware device
- pywin32 (win32api) - Windows API access for cursor position

**Input/Control:**
- keyboard - Global hotkey registration (F10, F11, END)
- ctypes - Windows DPI awareness setting

**Build/Dev:**
- PyInstaller 6.x - Single-file executable creation
- UPX compression enabled (`upx=True` in spec file)

## Key Dependencies

**Critical:**
- `pyserial` - Serial port communication with KMBox hardware
- `opencv-python` (cv2) - Template matching for UI element detection
- `dxcam` - High-performance screen capture using DXGI
- `rapidocr-onnxruntime` - OCR for account identification
- `keyboard` - Global hotkey handling
- `pywin32` - Windows API integration

**Infrastructure:**
- `numpy` - Array processing for OpenCV image data
- `Pillow` (likely, via PyInstaller) - Image handling

**Standard Library (Heavy Usage):**
- `threading` - Non-blocking task execution
- `time` - Precise delays and timing
- `json` - Configuration and progress tracking
- `os`, `sys`, `glob` - File system operations
- `datetime` - Date-based progress archiving
- `re` - Text cleaning for OCR results
- `ctypes` - Windows system calls

## Configuration

**Environment:**
- No `.env` file detected
- Configuration stored in JSON files:
  - `account_config.json` - Maps account names to character counts
  - `slot_progress_archive.json` - Tracks daily processing progress
- Hardcoded ROI coordinates for 2560x1440 resolution

**Build:**
- `FerrumBot_v1.spec` - PyInstaller spec file
  - Entry point: `gui_launcher.py`
  - Bundled directories: `assets/`, `core/`, `modules/`
  - Output: `dist/FerrumBot_v1.exe`
  - Console disabled (windowed mode)

## Platform Requirements

**Development:**
- Windows 10/11 (uses win32api)
- Python 3.10+ (type hints compatible)
- Serial port access (COM2/COM3 for KMBox)
- 2560x1440 screen resolution (hardcoded coordinates)

**Production:**
- Windows target only
- KMBox (or compatible) USB serial device on COM2/COM3
- CP210x USB-to-UART bridge driver
- Game running at 2560x1440 resolution

---

*Stack analysis: 2026-03-07*
