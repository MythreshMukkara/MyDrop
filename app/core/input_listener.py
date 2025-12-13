from pynput import keyboard
from PyQt6.QtCore import QObject, pyqtSignal

class GlobalInputListener(QObject):
    # This 'signal' allows the background thread to talk to the GUI
    hotkey_triggered = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.listener = None

    def start(self):
        # Define the hotkey combination
        # <ctrl>+<alt>+m = Send Mode
        hotkeys = {
            '<ctrl>+<alt>+m': self.on_activate_send_mode
        }

        # Start the listener in a non-blocking way
        self.listener = keyboard.GlobalHotKeys(hotkeys)
        self.listener.start()
        print("[Core] Global Listener started. Press Ctrl+Alt+m to test.")

    def on_activate_send_mode(self):
        print("[Input] Hotkey detected!")
        # Emit the signal to the Main Thread
        self.hotkey_triggered.emit("SEND_MODE")

    def stop(self):
        if self.listener:
            self.listener.stop()