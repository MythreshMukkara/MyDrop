"""
=============================================================================
MODULE: transfer.py
DESCRIPTION: 
    Manages direct Point-to-Point file transfer using TCP Sockets (Port 50001).
    
    Classes:
    - Server (Sender): Opens a socket, waits for connection, streams file data.
      Includes a 'Kill Switch' to stop previous servers if a new gesture occurs.
    - Client (Receiver): Connects to the Sender's IP, downloads stream, writes to disk.
    
    Safety:
    - Uses SO_REUSEADDR to prevent 'Port In Use' errors.
    - Implements timeouts (20s) to prevent hanging if no receiver connects.
=============================================================================
"""

#import statements
import socket
import os
import threading
import time

from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal

# Configuration
TRANSFER_PORT = 50001
BUFFER_SIZE = 4096

class TransferManager(QObject):
    # Signals
    transfer_progress = pyqtSignal(int)
    transfer_complete = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.server_socket = None # Keep track of the socket so we can close it
        self.is_running = False

    # --- SENDER LOGIC ---
    def start_server(self, filepath):
        """Starts a TCP server. Kills any existing server first.
        Then starts a new thread to host the given file."""
        
        # 1. STOP previous server if it's running
        self.stop_server()
        
        # 2. Start new server thread
        self.is_running = True
        self.thread = threading.Thread(target=self._server_worker, args=(filepath,), daemon=True)
        self.thread.start()

    def stop_server(self):
        """Force closes the socket to free the port."""
        self.is_running = False
        if self.server_socket:
            try:
                print("[Transfer] Stopping previous server...")
                self.server_socket.close() # This will trigger an error in the worker thread, killing it
                self.server_socket = None
                time.sleep(0.1) # Give OS a moment to release port
            except:
                pass

    def _server_worker(self, filepath):
        """Blocking loop that waits for client connection and pipes file data."""

        print(f"[Transfer] Server starting for {filepath}...")
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # --- FIX: Set Timeout (20 Seconds) ---
            self.server_socket.settimeout(20) 
            
            try:
                self.server_socket.bind(('0.0.0.0', TRANSFER_PORT))
            except OSError:
                print("[Transfer] Port busy. Waiting...")
                time.sleep(1)
                self.server_socket.bind(('0.0.0.0', TRANSFER_PORT))

            self.server_socket.listen(1)
            print("[Transfer] Waiting for receiver (20s timeout)...")
            
            # This will now crash if nobody connects in 20s
            client_socket, addr = self.server_socket.accept()
            
            # Reset timeout for the actual file transfer (we don't want it cutting off mid-file)
            client_socket.settimeout(None) 
            
            print(f"[Transfer] Connected to {addr}")
            
            filesize = os.path.getsize(filepath)
            sent_bytes = 0
            
            with open(filepath, "rb") as f:
                while True:
                    data = f.read(BUFFER_SIZE)
                    if not data: break
                    client_socket.sendall(data)
                    sent_bytes += len(data)
                    percent = int((sent_bytes / filesize) * 100)
                    self.transfer_progress.emit(percent)

            print("[Transfer] File sent successfully.")
            self.transfer_complete.emit("File Sent Successfully!")
            client_socket.close()

        # --- Handle Timeout ---

        except socket.timeout:
            print("[Transfer] Timeout: No receiver connected.")
            self.transfer_complete.emit("No Receiver Found")

        except OSError as e:
            if self.is_running:
                print(f"[Transfer] System Error: {e}")
                # This ensures the Red Notification appears!
                self.transfer_complete.emit(f"Error: {e}") 
            else:
                # Only stay silent if we stopped it manually
                print("[Transfer] Server stopped manually.")

        except Exception as e:
            print(f"[Transfer] Server Error: {e}")
            self.transfer_complete.emit(f"Error: {str(e)}")
            
        finally:
            if self.server_socket:
                self.server_socket.close()
                self.server_socket = None

    # --- RECEIVER LOGIC ---
    def start_download(self, sender_ip, filename):
        self.thread = threading.Thread(target=self._client_worker, args=(sender_ip, filename), daemon=True)
        self.thread.start()

    def _client_worker(self, sender_ip, filename):
        print(f"[Transfer] Connecting to {sender_ip}...")
        try:
            # --- NEW SAVE LOGIC START ---
            # 1. Get the dynamic path to Downloads/MyDrop
            download_dir = Path.home() / "Downloads" / "MyDrop"
            
            # 2. Create the folder if it doesn't exist
            download_dir.mkdir(parents=True, exist_ok=True)
            
            # 3. Create the full file path
            save_path = download_dir / filename
            # --- NEW SAVE LOGIC END ---

            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((sender_ip, TRANSFER_PORT))
            print(f"[Transfer] Connected! Saving to {save_path}")

            # Change 'downloaded_{filename}' to 'save_path' here:
            with open(save_path, "wb") as f:
                while True:
                    data = s.recv(BUFFER_SIZE)
                    if not data: break
                    f.write(data)
            
            print(f"[Transfer] Download complete.")
            # Update the notification message
            self.transfer_complete.emit(f"Saved to Downloads/MyDrop")
            s.close()

        except Exception as e:
            print(f"[Transfer] Client Error: {e}")
            self.transfer_complete.emit(f"Download Failed: {str(e)}")

        except Exception as e:
            print(f"[Transfer] Client Error: {e}")
            self.transfer_complete.emit(f"Download Failed: {str(e)}")