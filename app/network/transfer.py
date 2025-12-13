import socket
import os
import threading
import time
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
        """Starts a TCP server. Kills any existing server first."""
        
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

        # --- FIX: Handle Timeout ---
        except socket.timeout:
            print("[Transfer] Timeout: No receiver connected.")
            self.transfer_complete.emit("No Receiver Found (Timeout)")

        except OSError:
            print("[Transfer] Server stopped (likely cancelled).")
            
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
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((sender_ip, TRANSFER_PORT))
            print("[Transfer] Connected! Downloading...")

            with open(f"downloaded_{filename}", "wb") as f:
                while True:
                    data = s.recv(BUFFER_SIZE)
                    if not data: break
                    f.write(data)
            
            print(f"[Transfer] Download complete: downloaded_{filename}")
            self.transfer_complete.emit(f"Saved as downloaded_{filename}")
            s.close()

        except Exception as e:
            print(f"[Transfer] Client Error: {e}")
            self.transfer_complete.emit(f"Download Failed: {str(e)}")