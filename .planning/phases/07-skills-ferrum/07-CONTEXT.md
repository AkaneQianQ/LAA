# Phase 7: Ferrum Hardware Integration - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning
**Source:** User requirements + Ferrum hardware documentation

<domain>
## Phase Boundary

This phase delivers a complete Ferrum hardware controller implementation that integrates
with the existing HardwareInputGateway. The controller will translate high-level actions
(click, press, scroll, move) into Ferrum's serial command protocol.

**What this phase delivers:**
1. FerrumController class implementing the hardware controller interface
2. Serial communication layer for Ferrum KM API commands
3. HID key code mapping for keyboard actions
4. Mouse movement and button control via Ferrum protocol
5. Integration with existing HardwareInputGateway and workflow system

**What this phase does NOT include:**
- Changes to workflow YAML definitions
- Vision engine modifications
- Account management changes
- Error recovery logic changes

</domain>

<decisions>
## Implementation Decisions

### Ferrum API Selection
- **Decision:** Use Software API (KM API) over serial port
- **Rationale:** Windows-compatible, modern, high-performance, direct command interface
- **Locked:** Yes

### Serial Communication
- **Decision:** Use pyserial for serial communication (consistent with existing codebase)
- **Port:** Configurable (default COM2 for CP210x devices)
- **Baudrate:** 115200
- **Line terminator:** \r\n (per Ferrum spec)
- **Locked:** Yes

### Command Mapping
- **Decision:** Map existing controller methods to Ferrum KM API commands
  - click(x, y) → km.move() + km.click(0) + hardware-managed delay
  - press(key) → km.down(hid) + delay + km.up(hid)
  - scroll(dir, ticks) → km.wheel(±1) per tick
  - wait(ms) → Python time.sleep()
- **Locked:** Yes

### HID Key Codes
- **Decision:** Use standard HID Usage Table (HUT 1.5) codes
- **Common keys mapped:**
  - ESC = 41
  - U = 24
  - Up Arrow = 38
  - Down Arrow = 40
  - Left Alt = 226
  - Enter = 40 (same as Down in some contexts)
- **Locked:** Yes

### Mouse Movement
- **Decision:** Use relative movement via km.move(dx, dy)
- **Units:** Generic units (typically pixels, OS-dependent)
- **Bounds:** No clamping at controller level (gateway handles constraints)
- **Locked:** Yes

### Hardware Override Safety
- **Decision:** Rely on Ferrum's built-in hardware override for stuck-input prevention
- **Note:** km.down() presses are indefinite until km.up() or hardware override
- **Implementation:** Always pair down/up for key presses
- **Locked:** Yes

### Integration Pattern
- **Decision:** FerrumController implements same interface expected by ActionDispatcher
- **Methods required:** click(x, y), press(key), scroll(direction, ticks), wait(seconds)
- **Locked:** Yes

</decisions>

<specifics>
## Specific Ideas

### FerrumController Interface
```python
class FerrumController:
    """Ferrum hardware controller implementing the controller interface."""

    def __init__(self, port: str = "COM2", baudrate: int = 115200):
        self.serial = serial.Serial(port, baudrate, timeout=1)
        self._send_command("km.init()")  # Clear device locks

    def click(self, x: int, y: int) -> None:
        """Move to position and click left button."""
        self._send_command(f"km.move({x}, {y})")
        self._send_command("km.click(0)")

    def press(self, key_name: str) -> None:
        """Press a key by name (maps to HID code)."""
        hid_code = self._key_to_hid(key_name)
        self._send_command(f"km.down({hid_code})")
        time.sleep(0.05)  # Brief press duration
        self._send_command(f"km.up({hid_code})")

    def scroll(self, direction: str, ticks: int) -> None:
        """Scroll up or down."""
        amount = 1 if direction == "up" else -1
        for _ in range(ticks):
            self._send_command(f"km.wheel({amount})")

    def _send_command(self, cmd: str) -> str:
        """Send command and parse response."""
        self.serial.write(f"{cmd}\r\n".encode())
        # Read echoed command + result + prompt
        response = self.serial.read_until(b">>> ")
        return response.decode()
```

### Key Name to HID Mapping
```python
KEY_MAP = {
    "esc": 41,
    "u": 24,
    "up": 38,
    "down": 40,
    "left": 37,
    "right": 39,
    "enter": 40,
    "alt": 226,  # Left Alt
    "space": 44,
    "tab": 43,
}
```

### Workflow Integration
```python
# In main entry point (gui_launcher.py or test)
from core.hardware_input_gateway import HardwareInputGateway
from core.ferrum_controller import FerrumController

# Create Ferrum hardware controller
ferrum = FerrumController(port="COM2")

# Wrap in gateway for compliance/policy
gateway = HardwareInputGateway(hardware_controller=ferrum)

# Pass to workflow bootstrap
executor = create_workflow_executor(
    "config/workflows/guild_donation.yaml",
    controller=gateway,  # ActionDispatcher calls gateway.click/press/scroll
    vision_engine=vision
)
```

</specifics>

<deferred>
## Deferred Ideas

- KMBox Net style API (UDP socket) - not needed, serial is sufficient
- DHZBox style API - not needed
- Button/axis locks for input masking - not required for current workflows
- Key state callbacks - not needed for automation
- Multiple key simultaneous press (multidown) - can add later if needed

</deferred>

---

*Phase: 07-skills-ferrum*
*Context gathered: 2026-03-08 via requirements analysis*
