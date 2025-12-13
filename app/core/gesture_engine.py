import cv2
import mediapipe as mp
import time
import threading
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal

class GestureEngine(QObject):
    # --- SIGNALS ---
    # These let the engine talk to the UI thread
    gesture_detected = pyqtSignal(str)  # Sends "GRAB" or "DROP"
    error_occurred = pyqtSignal(str)    # Sends error messages

    def __init__(self):
        super().__init__()
        self.running = False
        self.cap = None
        
        # Initialize MediaPipe (The AI)
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        
        # State Tracking
        self.is_holding = False
        self.last_gesture = "UNKNOWN"

    def diagnose_camera(self):
        """ (Your existing healthy/closed shutter check) """
        try:
            time.sleep(0.2)
            temp_cap = cv2.VideoCapture(0)
            if not temp_cap.isOpened(): return False, "No camera."
            for _ in range(20): temp_cap.read() # Warmup
            ret, frame = temp_cap.read()
            temp_cap.release()
            if not ret: return False, "Camera read error."
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            avg = np.mean(gray)
            if avg < 30: return False, "Camera too dark/closed."
            return True, "Healthy"
        except Exception as e:
            return False, str(e)

    def start(self):
        """Starts the processing loop in a separate thread"""
        if self.running: return
        self.running = True
        
        # Run the loop in a background thread so the GUI doesn't freeze
        self.thread = threading.Thread(target=self._process_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stops the loop safely"""
        self.running = False
        if self.cap:
            self.cap.release()

    def _process_loop(self):
        """The Main AI Loop (Runs in background)"""
        print("[Core] Starting Gesture Loop...")
        
        # Open Camera
        self.cap = cv2.VideoCapture(0)
        
        while self.running and self.cap.isOpened():
            success, image = self.cap.read()
            if not success:
                continue

            # Performance: Mark writable false for MediaPipe processing
            image.flags.writeable = False
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = self.hands.process(image)

            # --- Logic ---
            current_gesture = "UNKNOWN"
            
            if results.multi_hand_landmarks:
                # We found a hand!
                hand_landmarks = results.multi_hand_landmarks[0]
                
                # Check for Fist vs Open
                # (Logic: Are fingertips below knuckles?)
                index_tip_y = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP].y
                index_pip_y = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_PIP].y
                middle_tip_y = hand_landmarks.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y
                middle_pip_y = hand_landmarks.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_PIP].y

                if (index_tip_y > index_pip_y and middle_tip_y > middle_pip_y):
                    current_gesture = "FIST"
                else:
                    current_gesture = "OPEN"

                # --- State Machine (The Magic) ---
                if current_gesture != self.last_gesture:
                    
                    # 1. Detect GRAB (Open -> Fist)
                    if self.last_gesture == "OPEN" and current_gesture == "FIST":
                        if not self.is_holding:
                            self.is_holding = True
                            print("[Core] GRAB Detected!")
                            self.gesture_detected.emit("GRAB")

                    # 2. Detect DROP (Fist -> Open)
                    elif self.last_gesture == "FIST" and current_gesture == "OPEN":
                        if self.is_holding:
                            self.is_holding = False
                            print("[Core] DROP Detected!")
                            self.gesture_detected.emit("DROP")
                    
                    self.last_gesture = current_gesture

            # Small sleep to save CPU
            time.sleep(0.01)

        # Cleanup when loop ends
        self.cap.release()
        print("[Core] Gesture Loop Stopped.")