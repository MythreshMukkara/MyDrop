# 🖐️ MyDrop - An Offline File Transfer Tool for Windows using Computer Vision

---

## 💡 The Inspiration

### "Why do we need the Internet to move a file 2 feet away?"

My friends and I exclusively use Windows laptops. We noticed a recurring frustration: whenever we needed to share files between our PCs, the process was clumsy. We either had to:

1. Transfer the file to a mobile phone first, then send it to the other PC.
2. Use WhatsApp or Email, which requires an active Internet connection (not always available) and compresses our images.

When we saw the **Huawei Air Gesture** file transfer technology, we realized this was the missing link. We decided to build a native Windows application that allows us to grab files physically from the air and "drop" them onto another computer—**no Internet required, no cables, no USB drives.**

---

## 🚀 How It Works (The Flow)

MyDrop uses your laptop's webcam to track hand movements and creates a local peer-to-peer network for file transfer.

### 1. The Sender

1. **Select:** Highlight any file(s) or folder in File Explorer.
2. **Activate:** Press `Ctrl+Alt+M` to open the camera (Green Border appears).
3. **Grab:** Make a **Fist** gesture at the camera. The app intelligently "copies" the selected files (zipping them automatically if it's a folder).
4. **Drop:** Open your hand (✋) at the camera. The app broadcasts the file to the local network and locks the transfer.

### 2. The Receiver

1. **Notification:** The receiver sees a system notification: *"User X sends [Filename]. Press Win+Alt+M to Download."*
2. **Accept:** The receiver presses `Win+Alt+M`.
3. **Download:** The file is instantly transferred via TCP and saved to the `Downloads/MyDrop/` folder.

---

## 📂 Project Architecture & Modules

The project is modularized to separate UI, Network Logic, and AI processing.

### 🔹 Entry Point

* **`main.py`**
* **Purpose:** The launchpad of the application.
* **Function:** It redirects all console output to a log file (`MyDrop_Debug.log`) so errors can be tracked even in the compiled EXE. It initializes the system tray application.

### 🔹 User Interface (`app/ui`)

* **`tray_icon.py`**
* **Purpose:** The central controller ("The Brain").
* **Function:** Manages the application state (Idle, Sender, Receiver). It handles notifications, connects the network signals to the UI, and decides what happens when a gesture is detected.

* **`overlay.py`**
* **Purpose:** Visual feedback.
* **Function:** Draws a transparent colored border around the screen to tell the user the current status (Green = Ready, Cyan = Grabbed, Red = Error, Blue = Downloading).

### 🔹 Core Logic (`app/core`)

* **`gesture_engine.py`**
* **Purpose:** The eye of the system.
* **Function:** Uses **MediaPipe** and **OpenCV** to track hand landmarks. It calculates geometry to distinguish between an "Open Palm" and a "Closed Fist" and emits signals only when the state changes.

* **`file_grabber.py`**
* **Purpose:** Smart file handling.
* **Function:** Interacts with the Windows Clipboard. If a user grabs a folder or multiple files, this module automatically compresses them into a temporary ZIP file so they can be sent as a single object.

* **`input_listener.py`**
* **Purpose:** Global keyboard control.
* **Function:** Uses `pynput` to listen for hotkeys (`Ctrl+Alt+M`, `Win+Alt+M`) even when the application is minimized or running in the background.

### 🔹 Networking (`app/network`)

* **`discovery.py`** (UDP)
* **Purpose:** Finding devices.
* **Function:** Broadcasts "Announce" packets over the local Wi-Fi. It allows the Receiver to know *who* is sending a file and *what* the file is called before accepting it.

* **`transfer.py`** (TCP)
* **Purpose:** Moving the data.
* **Function:** Establishes a direct, high-speed socket connection between the two laptops. It handles the raw byte transfer and ensures the file is saved correctly in the `Downloads` folder.

---

## 🛠️ Tech Stack

* **Language:** Python 3.12
* **GUI:** PyQt6 (System Tray & Overlay)
* **Computer Vision:** OpenCV, Google MediaPipe
* **Networking:** Python `socket` (TCP/UDP)
* **System Automation:** `pyautogui`, `pywin32`, `pynput`
* **Packaging:** PyInstaller

---

## 📦 Installation & Usage

### Option A: Run the Standalone EXE

1. Download `MyDrop.exe` from the **Releases** tab.
2. Run the application on both laptops.
3. Make sure both laptops are connected to the **same Wi-Fi network**.

### Option B: Run from Source

1. Clone the repository:

   ```bash
   git clone https://github.com/MythreshMukkara/MyDrop.git
   cd MyDrop
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the app:

   ```bash
   python main.py
   ```

---

## 🔮 Future Improvements

* Add encryption for secure file transfer.
* Add a "History" tab to see previously sent files.
* Cross-platform support (Mac/Linux).

---
