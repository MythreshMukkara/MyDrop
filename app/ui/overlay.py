"""
=============================================================================
MODULE: overlay.py
DESCRIPTION: 
    A transparent, click-through window that draws a colored border around the screen.
    
    Purpose: Provides visual feedback of the application state without obstructing work.
    - Green: Ready / Listening.
    - Cyan: File Grabbed.
    - Purple: Broadcasting / Waiting.
    - Blue: Downloading.
    - Red: Error / Timeout.
    - Yellow: Incoming Offer.

    Tech: Uses PyQt6 WA_TransparentForMouseEvents to ensure it doesn't block clicks.
=============================================================================
"""

#import statements
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen

class OverlayWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        # 1. Remove Title Bar and Window Frame
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |       # No border/title bar
            Qt.WindowType.WindowStaysOnTopHint |      # Always on top of other apps
            Qt.WindowType.Tool |                      # Don't show in taskbar
            Qt.WindowType.WindowTransparentForInput   # CLICK THROUGH (Crucial!)
        )
        
        # 2. Make the background transparent
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 3. Set to Full Screen
        screen_geometry = QApplication.primaryScreen().geometry()
        self.setGeometry(screen_geometry)
        
        # State
        self.border_color = QColor(0, 255, 0) # Green for "Active"
        self.border_width = 10

    def paintEvent(self, event):
        """Draws the colored border around the screen"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Setup the Pen (The Border)
        pen = QPen(self.border_color)
        pen.setWidth(self.border_width)
        painter.setPen(pen)
        
        # Draw the rectangle exactly around the window edges
        # We adjust by half width to ensure it stays on screen
        rect = self.rect().adjusted(
            self.border_width // 2, 
            self.border_width // 2, 
            -self.border_width // 2, 
            -self.border_width // 2
        )
        painter.drawRect(rect)

    def flash_success(self):
        """Changes color to Blue briefly (e.g., when file sent)"""
        self.border_color = QColor(0, 100, 255) # Blue
        self.update() # Redraw
        QTimer.singleShot(1000, self.reset_color) # Reset after 1 sec

    def reset_color(self):
        self.border_color = QColor(0, 255, 0) # Back to Green
        self.update()