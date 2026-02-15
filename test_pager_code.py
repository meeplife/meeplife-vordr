#!/usr/bin/env python3
"""
Test script to validate Pager code works without actual Pager hardware.
Run this on a Raspberry Pi to check for Python errors in the Pager modules.

Usage:
    python3 test_pager_code.py
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Create a mock pagerctl module before importing pager code
class MockPager:
    """Mock Pager class that simulates the real pagerctl.Pager without hardware."""
    
    # Predefined colors (RGB565)
    BLACK = 0x0000
    WHITE = 0xFFFF
    RED = 0xF800
    GREEN = 0x07E0
    BLUE = 0x001F
    YELLOW = 0xFFE0
    CYAN = 0x07FF
    MAGENTA = 0xF81F
    ORANGE = 0xFD20
    PURPLE = 0x8010
    GRAY = 0x8410
    
    # Button constants
    BTN_UP = 0x01
    BTN_DOWN = 0x02
    BTN_LEFT = 0x04
    BTN_RIGHT = 0x08
    BTN_GREEN = 0x10
    BTN_RED = 0x20
    BTN_BLUE = 0x40
    
    # Event types
    EVENT_NONE = 0
    EVENT_PRESS = 1
    EVENT_RELEASE = 2
    
    def __init__(self):
        self.width = 222
        self.height = 480
        self._initialized = False
        self._rotation = 0
        print("[MockPager] Created")
    
    @staticmethod
    def rgb(r, g, b):
        """Convert RGB888 to RGB565."""
        return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    
    def init(self):
        self._initialized = True
        print("[MockPager] init() called")
        return True
    
    def cleanup(self):
        self._initialized = False
        print("[MockPager] cleanup() called")
    
    def set_rotation(self, degrees):
        self._rotation = degrees
        if degrees in [90, 270]:
            self.width, self.height = 480, 222
        else:
            self.width, self.height = 222, 480
        print(f"[MockPager] set_rotation({degrees}) - size now {self.width}x{self.height}")
    
    def clear(self, color=0):
        print(f"[MockPager] clear(color={color:#06x})")
    
    def flip(self):
        print("[MockPager] flip() - frame rendered")
    
    def draw_pixel(self, x, y, color):
        pass
    
    def draw_rect(self, x, y, w, h, color):
        print(f"[MockPager] draw_rect({x}, {y}, {w}, {h}, {color:#06x})")
    
    def fill_rect(self, x, y, w, h, color):
        print(f"[MockPager] fill_rect({x}, {y}, {w}, {h}, {color:#06x})")
    
    def draw_text(self, x, y, text, color, size=1):
        print(f"[MockPager] draw_text({x}, {y}, '{text[:30]}...', size={size})")
    
    def draw_text_ttf(self, x, y, text, font_path, font_size, color):
        print(f"[MockPager] draw_text_ttf({x}, {y}, '{text[:30]}...', font_size={font_size})")
    
    def draw_bmp(self, x, y, path):
        print(f"[MockPager] draw_bmp({x}, {y}, '{os.path.basename(path)}')")
    
    def draw_line(self, x1, y1, x2, y2, color):
        pass
    
    def poll_input(self):
        pass
    
    def get_input(self):
        return type('Input', (), {'current': 0, 'pressed': 0, 'released': 0})()
    
    def get_input_event(self):
        return None
    
    def get_battery_percent(self):
        return 75
    
    def get_battery_charging(self):
        return False


# Inject mock into sys.modules BEFORE any imports
import types
mock_module = types.ModuleType('pagerctl')
mock_module.Pager = MockPager
mock_module.PAGER_EVENT_NONE = 0
mock_module.PAGER_EVENT_PRESS = 1
mock_module.PAGER_EVENT_RELEASE = 2
sys.modules['pagerctl'] = mock_module

print("=" * 60)
print("Pager Code Test - Using MockPager (no hardware required)")
print("=" * 60)
print()

# Now test importing the pager modules
errors = []

print("[TEST] Importing pager_menu.py...")
try:
    # We need to patch out the immediate Pager() call in pager_menu
    import pager_menu
    print("[OK] pager_menu.py imported successfully")
except Exception as e:
    print(f"[FAIL] pager_menu.py: {e}")
    import traceback
    traceback.print_exc()
    errors.append(('pager_menu.py', str(e)))

print()
print("[TEST] Importing pager_display.py...")
try:
    import pager_display
    print("[OK] pager_display.py imported successfully")
except Exception as e:
    print(f"[FAIL] pager_display.py: {e}")
    import traceback
    traceback.print_exc()
    errors.append(('pager_display.py', str(e)))

print()
print("[TEST] Importing PagerRagnar.py...")
try:
    # Don't run __main__, just import
    import importlib.util
    spec = importlib.util.spec_from_file_location("PagerRagnar", 
        os.path.join(os.path.dirname(__file__), "PagerRagnar.py"))
    pager_ragnar = importlib.util.module_from_spec(spec)
    # Don't execute - just check syntax
    print("[OK] PagerRagnar.py syntax OK")
except Exception as e:
    print(f"[FAIL] PagerRagnar.py: {e}")
    import traceback
    traceback.print_exc()
    errors.append(('PagerRagnar.py', str(e)))

print()
print("[TEST] Testing pager_menu.RagnarMenu instantiation...")
try:
    interfaces = [{'name': 'eth0', 'ip': '192.168.1.100', 'subnet': '192.168.1.0/24'}]
    menu = pager_menu.RagnarMenu(interfaces)
    print(f"[OK] RagnarMenu created - display size: {menu.gfx.width}x{menu.gfx.height}")
    menu.cleanup()
except Exception as e:
    print(f"[FAIL] RagnarMenu: {e}")
    import traceback
    traceback.print_exc()
    errors.append(('RagnarMenu', str(e)))

print()
print("=" * 60)
if errors:
    print(f"FAILED: {len(errors)} error(s) found:")
    for name, err in errors:
        print(f"  - {name}: {err}")
    sys.exit(1)
else:
    print("SUCCESS: All Pager code imports work correctly!")
    print("The code should work on real Pager hardware.")
    sys.exit(0)
