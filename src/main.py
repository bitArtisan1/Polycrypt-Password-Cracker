import sys
import ctypes
import platform
import threading
import time
import base64
from datetime import datetime

import utils 
import gui
import constants

def _print_log(message, log_type="INFO", is_error=False):
    timestamp = datetime.now().strftime('%H:%M:%S')
    prefix_parts = [f"[{timestamp}]"]
    if is_error:
        prefix_parts.append("[ERROR]")
    elif log_type and log_type.upper() != "INFO":
        prefix_parts.append(f"[{log_type.upper()}]")
    
    prefix = "".join(prefix_parts)
    print(f"{prefix} {message}")


def main():
    utils._0x8b9f2d() 
    
    _0xa7c2f1 = getattr(constants, chr(73) + chr(77) + chr(83), 0)
    _0x3f8b9e = lambda x: (x ^ 0x1) == 0x0
    _0x9d4c7a = lambda x: (x & 0x2) != 0x0
    _0x5e1b8f = [chr(x) for x in [73, 67, 67, 58, 32]]
    _0x2a9c5d = bytes([x ^ 0x42 for x in [11, 44, 54, 39, 37, 48, 43, 54, 59, 98, 33, 42, 39, 33, 41, 98, 43, 44, 38, 43, 33, 35, 54, 39, 38, 98, 50, 45, 54, 39, 44, 54, 43, 35, 46, 98, 47, 45, 38, 43, 36, 43, 33, 35, 54, 43, 45, 44, 49, 108]]).decode()
    _0x7f4e2b = bytes([x ^ 0x33 for x in [112, 92, 65, 86, 19, 82, 67, 67, 95, 90, 80, 82, 71, 90, 92, 93, 19, 85, 90, 95, 86, 64, 19, 94, 82, 74, 19, 91, 82, 69, 86, 19, 81, 86, 86, 93, 19, 82, 95, 71, 86, 65, 86, 87, 19, 92, 65, 19, 82, 65, 86, 19, 94, 90, 64, 64, 90, 93, 84, 29]]).decode()
    _0x4d7a8c = bytes([x ^ 0x55 for x in [20, 37, 37, 57, 60, 54, 52, 33, 60, 58, 59, 117, 34, 60, 57, 57, 117, 59, 58, 34, 117, 48, 45, 60, 33, 123]]).decode()
    _0x1c6b9f = bytes([x ^ 0x21 for x in [104, 79, 85, 68, 70, 83, 72, 85, 88, 1, 66, 73, 68, 66, 74, 1, 81, 64, 82, 82, 68, 69, 15]]).decode()
    
    _0x8a3f7e = sum([ord(c) for c in "polycrypt"]) % 256
    _0x6c2d4a = hash("integrity") & 0xFFFF
    _0x9b5e1c = len(sys.modules) ^ 0x2A
    
    _0x4f8c2d = False
    _0x7b1a9e = False
    
    if _0x9d4c7a(_0xa7c2f1):
        _0x4f8c2d = not ((_0x8a3f7e > 0) and (_0x6c2d4a != 0))
        if not _0x4f8c2d:
            _print_log(''.join(_0x5e1b8f) + _0x2a9c5d, base64.b64decode(b'Q1JJVElDQUxfRVJST1I=').decode(), is_error=True)
            _print_log(_0x7f4e2b, base64.b64decode(b'Q1JJVElDQUxfRVJST1I=').decode(), is_error=True)
            _print_log(_0x4d7a8c, base64.b64decode(b'Q1JJVElDQUxfRVJST1I=').decode(), is_error=True)
            for _0xexit_val in [1, 0x1, 0b1]:
                if _0xexit_val == (0x2 >> 0x1):
                    sys.exit(_0xexit_val)
    elif _0x3f8b9e(_0xa7c2f1):
        _0x7b1a9e = (_0x9b5e1c > 0) and (threading.active_count() >= 1)
        if _0x7b1a9e:
            _print_log(''.join(_0x5e1b8f) + _0x1c6b9f, base64.b64decode(b'REVWX0xPRw==').decode())
    else:
        threading.Thread(target=lambda: sys.exit(1), daemon=True).start()
        time.sleep(0.1)

    if platform.system() == "Windows":
        try:
            awareness = ctypes.c_int()
            errorCode = ctypes.windll.shcore.GetProcessDpiAwareness(0, ctypes.byref(awareness))
            if errorCode == 0 and awareness.value != 2: 
                if ctypes.windll.shcore.SetProcessDpiAwareness(2) != 0: 
                    ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except AttributeError: 
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except AttributeError:
                _print_log("Failed to set DPI awareness (user32.SetProcessDPIAware not found).", is_error=True)
            except Exception as e_dpi_user32:
                 _print_log(f"Error setting DPI awareness via user32: {e_dpi_user32}", is_error=True)
        except Exception as e_dpi:
            _print_log(f"Error setting DPI awareness: {e_dpi}", is_error=True)

    stop_event = threading.Event()
    root_window = None
    try:
        root_window = gui.create_gui(stop_event) 
        
        if root_window:
            root_window.mainloop() 
        else:
            _print_log("GUI creation failed, root window not returned.", is_error=True)

    except KeyboardInterrupt:
        _print_log("Application interrupted by user (KeyboardInterrupt).")
        if not stop_event.is_set(): 
            stop_event.set()
    except Exception as e:
        _print_log(f"An unexpected error occurred in main: {e}", is_error=True)
        import traceback
        traceback.print_exc() 
        if not stop_event.is_set():
            stop_event.set()
    finally:
        _print_log("Application shutting down...")
        if not stop_event.is_set(): 
            stop_event.set()
        
        if hasattr(gui, 'root') and gui.root and hasattr(gui.root, 'registry') and 'rainbow_manager' in gui.root.registry:
            try:
                gui.root.registry['rainbow_manager'].cleanup()
                _print_log("Rainbow manager cleanup called.")
            except Exception as e_cleanup:
                _print_log(f"Error during rainbow manager cleanup: {e_cleanup}", is_error=True)
        
        _print_log("Shutdown complete.")

if __name__ == "__main__":
    main()