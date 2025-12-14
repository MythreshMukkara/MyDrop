"""
=============================================================================
MODULE: input_listener.py
DESCRIPTION: 
    Wraps the 'pynput' library to provide system-wide hotkey detection.
    
    Hotkeys Monitored:
    1. <Ctrl>+<Alt>+S: Toggles the Main Sender Mode (Camera).
    2. <Win>+<Alt>+M: Accepts an incoming file request.
    
    Design:
    - Runs in a non-blocking background thread.
    - Emits Qt Signals to the Main Thread (tray_icon.py) to ensure thread safety.
=============================================================================
"""

from pynput import keyboard
from PyQt6.QtCore import QObject, pyqtSignal

class GlobalInputListener(QObject):
    # Emits "TOGGLE" or "ACCEPT"
    hotkey_triggered = pyqtSignal(str) 

    def __init__(self):
        super().__init__()
        self.listener = None

    def start(self):
        """Starts listening for global hotkeys"""
        # Define the hotkey mapping
        # <cmd> maps to the Windows Key on Windows
        self.hotkeys = {
            '<ctrl>+<alt>+M': self.on_toggle,
            '<cmd>+<alt>+M': self.on_accept
        }
        
        self.listener = keyboard.GlobalHotKeys(self.hotkeys)
        self.listener.start()

    def stop(self):
        if self.listener:
            self.listener.stop()

    def on_toggle(self):
        """Ctrl+Alt+m pressed"""
        self.hotkey_triggered.emit("TOGGLE")

    def on_accept(self):
        """Win+Alt+m pressed"""
        self.hotkey_triggered.emit("ACCEPT")