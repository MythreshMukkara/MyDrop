import socket
import json
import threading
import uuid
from PyQt6.QtCore import QObject, pyqtSignal

class DiscoveryManager(QObject):
    offer_received = pyqtSignal(dict, str) 

    def __init__(self, device_name="AirGesture_User"):
        super().__init__()
        self.device_name = device_name
        self.instance_id = str(uuid.uuid4())
        self.broadcast_port = 50000
        self.running = False
        self.sock = None

    def get_local_broadcast_ip(self):
        """
        Tricks the OS into revealing the real Wi-Fi IP, then calculates 
        the broadcast address (e.g., 192.168.1.x -> 192.168.1.255)
        """
        try:
            # We don't actually send data, just connecting to Google DNS helps us 
            # find which network interface is the "Real" one (Wi-Fi).
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            
            # Assuming a standard home network (/24 subnet), broadcast ends in .255
            # This splits "192.168.1.5", takes ["192", "168", "1"], and adds "255"
            base_ip = local_ip.rsplit('.', 1)[0]
            return f"{base_ip}.255"
        except:
            return '<broadcast>' # Fallback

    def start_listening(self):
        self.running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        print("[Net] Discovery Listener Started.")

    def stop(self):
        self.running = False
        if self.sock:
            self.sock.close()

    def broadcast_offer(self, filename, filesize):
        message = {
            "type": "ANNOUNCE",
            "sender": self.device_name,
            "instance_id": self.instance_id,
            "filename": filename,
            "filesize": filesize
        }
        
        target_ip = self.get_local_broadcast_ip()
        print(f"[Net] Broadcasting to target: {target_ip}")
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            json_msg = json.dumps(message).encode('utf-8')
            sock.sendto(json_msg, (target_ip, self.broadcast_port))
            sock.close()
            return True
        except Exception as e:
            print(f"[Net] Broadcast Error: {e}")
            return False

    def _listen_loop(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # CRITICAL: Allow multiple apps to listen on the same port
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            # Bind to 0.0.0.0 to hear from ALL interfaces
            self.sock.bind(('0.0.0.0', self.broadcast_port))
        except:
            print("[Net] Error: Could not bind port.")
            return

        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                message = json.loads(data.decode('utf-8'))

                sender_id = message.get('instance_id')
                if sender_id == self.instance_id:
                    continue # Ignore my own echo

                if message.get('type') == "ANNOUNCE":
                    print(f"[Net] OH! Heard offer from {addr[0]}")
                    self.offer_received.emit(message, addr[0])

            except Exception as e:
                pass