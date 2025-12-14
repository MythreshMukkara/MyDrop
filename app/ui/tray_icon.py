"""
=============================================================================
MODULE: tray_icon.py
DESCRIPTION: 
    The central controller for the MyDrop application.
    
    It integrates all subsystems:
    - User Interface: System Tray icon, Notifications, Overlay Window.
    - Input: Global Hotkeys (Start/Stop, Accept).
    - Core Logic: Gesture Engine (Camera), File Grabber (Clipboard/Zip).
    - Networking: Discovery (UDP) and Transfer (TCP).

    State Management:
    - Idle: Waiting for user hotkey.
    - Sender Mode: Camera active, looking for 'Grab' and 'Drop' gestures.
    - Receiver Mode: Waiting for user to accept incoming file via hotkey.
    - Busy: Currently zipping or transferring files.

KEY METHODS:
    - handle_hotkey: The master switch for toggling modes.
    - on_gesture_event: Handles Sender logic (Grab File -> Broadcast Offer).
    - on_offer_received: Handles Receiver logic (Incoming UDP -> Notification).
    - accept_transfer: Initiates TCP download.
=============================================================================
"""

#import statements
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication, QStyle
from PyQt6.QtGui import QAction, QColor
from PyQt6.QtCore import QTimer
import sys
import os
import socket

from app.ui.overlay import OverlayWindow
from app.core.input_listener import GlobalInputListener
from app.core.gesture_engine import GestureEngine
from app.network.discovery import DiscoveryManager
from app.network.transfer import TransferManager
from app.core.file_grabber import FileGrabber

class SystemTrayApp:
    def __init__(self):
        """Initializes UI components, starts background threads (Listener, Discovery), and sets up signals."""
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        # UI Setup
        self.tray_icon = QSystemTrayIcon()
        icon = self.app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self.tray_icon.setIcon(icon)
        self.tray_icon.setVisible(True)

        self.overlay = OverlayWindow()
        self.engine = GestureEngine()

        # Menu
        self.menu = QMenu()
        self.status_action = QAction("Status: Idle")
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)
        self.menu.addSeparator()
        self.quit_action = QAction("Quit MyDrop")
        self.quit_action.triggered.connect(self.quit_app)
        self.menu.addAction(self.quit_action)
        self.tray_icon.setContextMenu(self.menu)
        
        self.tray_icon.showMessage("MyDrop", "Ready. Ctrl+Alt+M to Send.", QSystemTrayIcon.MessageIcon.Information, 2000)

        # Input Listener
        self.listener = GlobalInputListener()
        self.listener.hotkey_triggered.connect(self.handle_hotkey) # Connects to new logic
        self.listener.start()

        # Network
        hostname = socket.gethostname()
        self.net_manager = DiscoveryManager(device_name=hostname)
        self.net_manager.offer_received.connect(self.on_offer_received)
        self.net_manager.start_listening()

        self.engine.gesture_detected.connect(self.on_gesture_event)
        self.transfer_manager = TransferManager()
        self.transfer_manager.transfer_complete.connect(self.on_transfer_done)
        
        # State
        self.current_sender_ip = None
        self.current_filename = None
        self.current_grabbed_file = None
        self.has_pending_offer = False

        self.deny_timer = QTimer()
        self.deny_timer.setSingleShot(True)
        self.deny_timer.timeout.connect(self.deny_request)

    def handle_hotkey(self, key_type):
        """
        Triggered by GlobalInputListener.
        - 'TOGGLE': Starts/Stops the Sender Mode (Camera).
        - 'ACCEPT': Accepts a pending file transfer if one exists.
        """
        print(f"[UI] Hotkey Triggered: {key_type}")

        # 1. HANDLE ACCEPT (Win+Alt+M)
        if key_type == "ACCEPT":
            if self.has_pending_offer:
                self.accept_transfer()
            else:
                # Optional: Tell user there is nothing to accept
                self.tray_icon.showMessage("MyDrop", "No pending files to download.", QSystemTrayIcon.MessageIcon.Warning, 1000)
            return

        # 2. HANDLE TOGGLE (Ctrl+Alt+M)
        if key_type == "TOGGLE":
            # If overlay is ON, turn it OFF
            if self.overlay.isVisible():
                self.full_shutdown()
            else:
                # If idle, turn ON Sender Mode
                self.start_sender_mode()

    def start_sender_mode(self):
        is_healthy, message = self.engine.diagnose_camera()
        if not is_healthy:
            self.tray_icon.showMessage("Camera Error", message, QSystemTrayIcon.MessageIcon.Warning, 3000)
            return 

        self.overlay.border_color = QColor(0, 255, 0) # Green
        self.overlay.update()
        self.overlay.show()
        self.status_action.setText("Status: LISTENING...")
        self.engine.start()

    def on_offer_received(self, metadata, sender_ip):
        """
        Triggered when a valid UDP broadcast is detected.
        - Ignores if app is busy.
        - Otherwise, shows 'Incoming File' notification and starts 20s timeout.
        """
        # 1. CHECK IF BUSY
        if self.has_pending_offer or self.overlay.border_color == QColor(0, 0, 255):
            print(f"[UI] BUSY. Ignored offer from {sender_ip}")
            return # Ignore the new guy
        print(f"[UI] Offer from {sender_ip}")
        
        self.current_sender_ip = sender_ip
        self.current_filename = metadata.get('filename')
        sender_name = metadata.get('sender', 'Unknown User')
        
        self.has_pending_offer = True
        
        # --- CHANGES START HERE ---
        # 1. No visual overlay (Gold removed)
        # 2. Just a notification
        
        self.tray_icon.showMessage(
            "Incoming File",
            f"{sender_name} sends: {self.current_filename}\nPress Win+Alt+M to Download",
            QSystemTrayIcon.MessageIcon.Information,
            5000
        )
        
        # 3. Start Timer (Silent Countdown)
        self.deny_timer.start(20000) 

    def accept_transfer(self):
        print("[UI] Accepting Transfer...")
        self.deny_timer.stop()
        self.has_pending_offer = False
        
        # Only show Blue overlay when download ACTUALLY starts
        self.overlay.border_color = QColor(0, 0, 255) # Blue
        self.overlay.show()
        self.overlay.update()
        self.tray_icon.showMessage("MyDrop", "Downloading...", QSystemTrayIcon.MessageIcon.NoIcon, 1000)
        
        if self.current_sender_ip and self.current_filename:
            self.transfer_manager.start_download(self.current_sender_ip, self.current_filename)

    def deny_request(self):
        print("[UI] Request Timed Out")
        self.has_pending_offer = False
        # Silent failure - just reset variables, no big red flash unless you want it
        self.current_sender_ip = None

    def on_gesture_event(self, event_type):
        """
        The Core Logic for SENDER Mode.
        - 'GRAB': Calls FileGrabber to zip/get files. Updates UI to Cyan.
        - 'DROP': Starts TCP Server, Broadcasts UDP Offer, locks Camera.
        """
        # SENDER LOGIC ONLY
        if event_type == "GRAB":
            # SENDER: GRAB FILE
            print("[UI] Sender: Attempting Smart Grab...")
            
            # 1. Notify User (Processing...)
            # We force an update so the user sees this BEFORE the zip lag happens
            self.tray_icon.showMessage("MyDrop", "Processing selection...", QSystemTrayIcon.MessageIcon.NoIcon, 1000)
            QApplication.processEvents() # Force UI to draw the notification NOW
            
            # 2. Perform the Grab (Zipping happens here)
            filepath, error = FileGrabber.get_grabbed_content()
            
            if filepath:
                self.current_grabbed_file = filepath
                filename = os.path.basename(filepath)
                
                # Update Visuals to Success (Cyan)
                self.overlay.border_color = QColor(0, 255, 255) 
                self.overlay.update()
                self.tray_icon.showMessage("MyDrop", f"Ready to Send: {filename}", QSystemTrayIcon.MessageIcon.NoIcon, 2000)
            
            else:
                # Failure
                print(f"[UI] Grab Failed: {error}")
                self.overlay.border_color = QColor(255, 0, 0)
                self.overlay.update()
                self.tray_icon.showMessage("Grab Failed", error, QSystemTrayIcon.MessageIcon.Warning, 3000)
                QTimer.singleShot(1000, self.reset_to_ready)

        elif event_type == "DROP":
            if self.current_grabbed_file:
                self.overlay.border_color = QColor(200, 0, 255) # Purple
                self.overlay.update()
                self.transfer_manager.start_server(self.current_grabbed_file)
                
                filesize = os.path.getsize(self.current_grabbed_file)
                filename = os.path.basename(self.current_grabbed_file)
                self.net_manager.broadcast_offer(filename, filesize)
                
                self.tray_icon.showMessage("MyDrop", "Transferring...", QSystemTrayIcon.MessageIcon.NoIcon, 2000)
                self.engine.stop() 

    def on_transfer_done(self, message):
        title = "Transfer Update"
        color = QColor(0, 255, 0)
        icon = QSystemTrayIcon.MessageIcon.Information
        
        if "No Receiver" in message or "Error" in message:
            title = "Failed"
            color = QColor(255, 0, 0)
            icon = QSystemTrayIcon.MessageIcon.Warning

        self.overlay.border_color = color
        self.overlay.update()
        self.tray_icon.showMessage(title, message, icon, 3000)
        QTimer.singleShot(2000, self.full_shutdown)

    def full_shutdown(self):
        self.overlay.hide()
        self.engine.stop()
        self.has_pending_offer = False
        self.status_action.setText("Status: Idle")

    def reset_to_ready(self):
        if self.overlay.isVisible():
            self.overlay.border_color = QColor(0, 255, 0)
            self.overlay.update()

    def quit_app(self):
        self.engine.stop()
        self.listener.stop()
        self.net_manager.stop()
        self.app.quit()

    def run(self):
        """Starts the application event loop."""
        sys.exit(self.app.exec())