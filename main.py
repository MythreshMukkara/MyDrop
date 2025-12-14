"""
=============================================================================
MODULE: main.py
PROJECT: MyDrop v1.0
DESCRIPTION: 
    The main entry point for the AirGesture application.
    
    Responsibilities:
    1. Environment Setup: Suppresses unnecessary MediaPipe/TensorFlow warnings.
    2. Logger Initialization: Redirects stdout/stderr to a local log file 
       ('MyDrop_Debug.log') to ensure debugging is possible even when 
       running as a compiled --noconsole EXE.
    3. Application Bootstrap: Instantiates the Qt Application and the 
       SystemTrayApp controller.

USAGE:
    Run directly via Python: `python main.py`
    Or build into EXE using PyInstaller.
=============================================================================
"""

#import statements
import sys
import os
import warnings

# 1. Suppress the MediaPipe Protobuf Warning
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
warnings.filterwarnings('ignore', category=UserWarning, module='google.protobuf')

# 2. Redirect Prints to Log File (The "Black Box")
# This ensures that when you run the EXE, you still have a record of what happened.
class Logger(object):
    """
    A custom output stream that writes to both the terminal (if available)
    and a persistent log file. Critical for debugging 'frozen' EXE apps.
    """
    def __init__(self):
        self.terminal = sys.stdout
        # Create log file in the same folder as the app
        self.log = open("MyDrop_Debug.log", "a", encoding="utf-8")

    def write(self, message):
        # Write to terminal (if visible)
        if self.terminal:
            self.terminal.write(message)
        # Write to file
        try:
            self.log.write(message)
            self.log.flush() # Ensure it saves immediately
        except:
            pass

    def flush(self):
        pass

# Activate Logger
sys.stdout = Logger()
sys.stderr = Logger()

# 3. Import UI
from app.ui.tray_icon import SystemTrayApp

if __name__ == "__main__":
    print("\n--- NEW SESSION STARTED ---")
    try:
        tray = SystemTrayApp()
        tray.run()
    except Exception as e:
        # If the app crashes completely, this catches it in the log
        print(f"CRITICAL CRASH: {e}")
        input("Press Enter to exit...") # Keeps window open if console mode