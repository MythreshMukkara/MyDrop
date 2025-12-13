from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication, QStyle
from PyQt6.QtGui import QAction
import sys
from app.ui.overlay import OverlayWindow
from app.core.input_listener import GlobalInputListener
from app.core.gesture_engine import GestureEngine
from PyQt6.QtGui import QColor
from app.network.discovery import DiscoveryManager
import socket # To get hostname
from app.network.transfer import TransferManager
from app.core.file_grabber import FileGrabber
import os

class SystemTrayApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        # --- UI Setup ---
        self.tray_icon = QSystemTrayIcon()
        icon = self.app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self.tray_icon.setIcon(icon)
        self.tray_icon.setVisible(True)

        self.overlay = OverlayWindow()
        self.engine = GestureEngine()

        self.menu = QMenu()
        
        # This action text will change when we press the hotkey
        self.status_action = QAction("Status: Idle")
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)
        
        self.menu.addSeparator()

        self.quit_action = QAction("Quit MyDrop")
        self.quit_action.triggered.connect(self.quit_app) # changed to custom quit method
        self.menu.addAction(self.quit_action)

        self.tray_icon.setContextMenu(self.menu)
        
        self.tray_icon.showMessage(
            "MyDrop V2",
            "Running. Press Ctrl+Alt+m to test.",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )

        # --- Listener Setup ---
        self.listener = GlobalInputListener()
        # Connect the signal from the thread to our function
        self.listener.hotkey_triggered.connect(self.handle_hotkey)
        # Start listening
        self.listener.start()

        self.engine = GestureEngine()
        # --- NETWORK SETUP ---
        # Get computer name automatically
        hostname = socket.gethostname()
        self.net_manager = DiscoveryManager(device_name=hostname)
        
        # Connect: When we hear a broadcast -> Run self.on_offer_received
        self.net_manager.offer_received.connect(self.on_offer_received)
        
        # Start listening immediately (Background Mode)
        self.net_manager.start_listening()
        # --- CONNECT SIGNALS ---
        # When engine says "GRAB", call self.on_gesture_event
        self.engine.gesture_detected.connect(self.on_gesture_event)
        # --- TRANSFER MANAGER ---
        self.transfer_manager = TransferManager()
        self.transfer_manager.transfer_complete.connect(self.on_transfer_done)
        
        # State to remember who sent us the file
        self.current_sender_ip = None
        self.current_filename = None
        self.is_receiver_mode = False # Track if we are the sender or receiver
        self.current_grabbed_file = None

    def handle_hotkey(self, mode_name):
        print(f"[UI] Requesting Mode: {mode_name}")
        
        # Toggle OFF
        if self.overlay.isVisible():
            print("[UI] Deactivating...")
            self.overlay.hide()
            self.engine.stop() # STOP THE ENGINE
            self.status_action.setText("Status: Idle")
            return

        # Toggle ON
        self.is_receiver_mode = False
        
        # --- DIAGNOSTIC CHECK ---
        is_healthy, message = self.engine.diagnose_camera()
        
        if not is_healthy:
            print(f"[UI] Start Failed: {message}")
            
            # 1. Show User Notification
            self.tray_icon.showMessage(
                "Camera Error",
                message,
                QSystemTrayIcon.MessageIcon.Warning,
                3000
            )
            
            # 2. Flash Red Border (Visual Error Feedback)
            self.overlay.border_color = QColor(255, 0, 0) # Red
            self.overlay.show()
            # Hide the red border automatically after 1 second
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(1000, self.overlay.hide)
            
            return # Stop here, do not activate mode

        # Success - Start Engine
        self.overlay.border_color = QColor(0, 255, 0) # Green
        self.overlay.update()
        self.overlay.show()
        self.status_action.setText("Status: LISTENING...")
        
        # START THE ENGINE LOOP
        self.engine.start()

    def on_gesture_event(self, event_type):
        if event_type == "GRAB":
            # --- NEW SMART GRAB LOGIC ---
            print("[UI] Attempting Smart Grab...")
            
            filepath, error = FileGrabber.get_selected_file()
            
            if filepath:
                self.current_grabbed_file = filepath
                filename = os.path.basename(filepath)
                
                # Success Visuals
                self.overlay.border_color = QColor(0, 255, 255) # Cyan
                self.overlay.update()
                self.tray_icon.showMessage("MyDrop", f"Grabbed: {filename}", QSystemTrayIcon.MessageIcon.NoIcon, 1000)
            else:
                # Error Visuals (Flash Red briefly)
                print(f"[UI] Grab Failed: {error}")
                self.overlay.border_color = QColor(255, 0, 0) # Red
                self.overlay.update()
                self.tray_icon.showMessage("Grab Failed", error, QSystemTrayIcon.MessageIcon.Warning, 1000)
                
                # Reset to Green after 1 second if failed
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(1000, self.reset_to_ready)

        elif event_type == "DROP":
            if not self.is_receiver_mode:
                # CASE A: SENDER
                if self.current_grabbed_file:
                    self.overlay.border_color = QColor(200, 0, 255) # Purple
                    self.overlay.update()
                    
                    # 1. Start Server with REAL file
                    self.transfer_manager.start_server(self.current_grabbed_file)
                    
                    # 2. Broadcast Offer
                    filesize = os.path.getsize(self.current_grabbed_file)
                    filename = os.path.basename(self.current_grabbed_file)
                    
                    self.net_manager.broadcast_offer(filename, filesize)
                    self.tray_icon.showMessage("MyDrop", f"Sending {filename}...", QSystemTrayIcon.MessageIcon.NoIcon, 1000)
                else:
                    self.tray_icon.showMessage("Error", "Nothing to send! Grab a file first.", QSystemTrayIcon.MessageIcon.Warning, 1000)
            
            else:
                # CASE B: RECEIVER (Logic remains the same)
                self.overlay.border_color = QColor(0, 0, 255)
                self.overlay.update()
                self.tray_icon.showMessage("MyDrop", "Accepting File...", QSystemTrayIcon.MessageIcon.NoIcon, 1000)
                if self.current_sender_ip and self.current_filename:
                    self.transfer_manager.start_download(self.current_sender_ip, self.current_filename)
            
            
    def on_offer_received(self, metadata, sender_ip):
        print(f"[UI] Offer from {sender_ip}")
        
        # Save info for later
        self.current_sender_ip = sender_ip
        self.current_filename = metadata.get('filename')
        self.is_receiver_mode = True # <--- CRITICAL SWITCH
        
        # Visuals
        self.tray_icon.showMessage("MyDrop", f"File Offer: {self.current_filename}", QSystemTrayIcon.MessageIcon.Information, 4000)
        self.overlay.border_color = QColor(255, 165, 0) # Orange
        self.overlay.show()
        
        # Wake up Camera
        if not self.engine.running:
             self.engine.start()
             self.status_action.setText("Status: WAITING FOR ACCEPT GESTURE...")
             
    def on_transfer_done(self, message):
        print(f"[UI] Transfer Finished: {message}")
        self.tray_icon.showMessage("MyDrop", message, QSystemTrayIcon.MessageIcon.Information, 3000)
        
        # Flash Green then hide
        self.overlay.border_color = QColor(0, 255, 0)
        self.overlay.update()
        
        # Close everything after 2 seconds
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(2000, self.reset_app)
        
    def reset_app(self):
        self.overlay.hide()
        self.engine.stop()
        self.is_receiver_mode = False

    def reset_to_ready(self):
        if self.overlay.isVisible():
            self.overlay.border_color = QColor(0, 255, 0) # Back to Green
            self.overlay.update()

    def quit_app(self):
        self.engine.stop()
        self.listener.stop()
        self.app.quit()

    def run(self):
        sys.exit(self.app.exec())