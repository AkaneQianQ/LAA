# Testing Patterns

**Analysis Date:** 2026-03-07

## Test Framework

**Runner:** Not detected
- No pytest configuration
- No unittest runner
- No test discovery setup

**Assertion Library:** Not applicable (no tests)

**Run Commands:**
```bash
# No test commands defined
# No test runner scripts in package.json equivalent
# Manual testing only via: python gui_launcher.py
```

## Test File Organization

**Location:** No test files present
- No `tests/` directory
- No `test_*.py` files
- No `*_test.py` files
- No `conftest.py`

**Naming:** Not applicable

**Structure:**
```
Project layout (no test structure):
.
├── core/
│   ├── ferrum_controller.py
│   └── vision_engine.py
├── modules/
│   ├── auto_login.py
│   └── guild_donation.py
├── gui_launcher.py
├── main.py
└── trigger_action.py
```

## Test Structure

**Suite Organization:** Not implemented

**Patterns:** None observed

## Mocking

**Framework:** Not detected
- No `unittest.mock` imports
- No `pytest-mock` or `mock` library usage
- No monkeypatching

**Patterns:** None

**What to Mock:**
- Hardware serial communication (`serial.Serial`)
- Screen capture (`dxcam.create`)
- OCR engine (`RapidOCR`)
- Win32 API calls (`win32api.GetCursorPos`, `win32api.GetAsyncKeyState`)
- Time delays (`time.sleep`)
- File system operations (JSON config read/write)

**What NOT to Mock:**
- Internal data structures and configuration dictionaries
- Pure functions without side effects

## Fixtures and Factories

**Test Data:** None

**Location:** Not applicable

**Recommended Fixture Pattern:**
```python
# Suggested pattern (not implemented)
@pytest.fixture
def mock_controller():
    """Create mock FerrumController for testing"""
    with patch('serial.Serial') as mock_serial:
        controller = FerrumController(port="COM1")
        yield controller

@pytest.fixture
def mock_vision():
    """Create mock VisionEngine with static frame"""
    vision = VisionEngine()
    vision.camera = Mock()
    vision.camera.grab.return_value = np.zeros((1440, 2560, 3), dtype=np.uint8)
    return vision
```

## Coverage

**Requirements:** None enforced
- No coverage target set
- No `.coveragerc` or `coverage.ini`

**View Coverage:**
```bash
# No coverage command configured
# To implement: pip install pytest-cov
# pytest --cov=. --cov-report=html
```

**Current Coverage:** 0% (no tests)

## Test Types

**Unit Tests:** Not implemented
- No isolated function testing
- No class method testing

**Integration Tests:** Not implemented
- No workflow testing
- No module interaction testing

**E2E Tests:** Manual only
- Human-in-the-loop testing via GUI
- Visual confirmation of automation steps
- Hardware-dependent validation

**Hardware-in-Loop Testing:**
- Requires physical KMBox device connected
- Requires game client running at 2560x1440
- Requires specific in-game states (character selection, guild menu)

## Common Patterns (Recommended)

**Async Testing:**
```python
# Pattern for testing threaded code (not implemented)
def test_stop_event_cancels_loop():
    stop_event = threading.Event()

    def long_running():
        while not stop_event.is_set():
            time.sleep(0.01)

    thread = threading.Thread(target=long_running)
    thread.start()
    stop_event.set()
    thread.join(timeout=1.0)
    assert not thread.is_alive()
```

**Error Testing:**
```python
# Pattern for testing hardware failures (not implemented)
def test_serial_failure_handled():
    with patch('serial.Serial', side_effect=serial.SerialException):
        controller = FerrumController(port="COM99")
        # Should print error but not crash
        assert controller.serial is None
```

**Computer Vision Testing:**
```python
# Pattern for testing template matching (not implemented)
def test_find_element_finds_template():
    vision = VisionEngine()
    # Create synthetic frame with known template
    frame = create_test_frame_with_template()
    vision.camera.grab.return_value = frame

    result = vision.find_element("assets/test_template.png")
    assert result is not None
    assert isinstance(result, tuple)
    assert len(result) == 2
```

## Testing Challenges

**Hardware Dependencies:**
- Serial communication requires physical device or mock
- Screen capture requires Windows environment with display
- Win32 API calls require Windows OS

**Timing Sensitivities:**
- Hardcoded `time.sleep()` calls throughout
- Animation and loading screen delays
- Network latency for game client

**Visual Confirmation:**
- Template matching depends on specific screen resolution (2560x1440)
- OCR accuracy varies with font rendering
- Color detection sensitive to display settings

**State Management:**
- Tests would require complex game state setup
- Character selection state, guild menu state, etc.
- Daily progress tracking with date-based reset

## Testing Debt

**Critical Gaps:**
1. No automated test suite
2. No CI/CD pipeline
3. No regression testing
4. Hardware failure modes untested
5. Error recovery paths not validated
6. Concurrent thread safety not verified

**Risk Areas:**
- `modules/auto_login.py` - Complex scroll calculation logic
- `modules/guild_donation.py` - Multi-step workflow with retries
- `core/ferrum_controller.py` - Serial communication reliability
- `core/vision_engine.py` - Image processing accuracy

**Recommended Priority:**
1. Unit tests for coordinate calculation logic
2. Mock-based tests for serial command formatting
3. Fixture-based tests for configuration loading
4. Integration tests with mocked hardware

---

*Testing analysis: 2026-03-07*
