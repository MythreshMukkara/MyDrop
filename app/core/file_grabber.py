import time
import pyautogui
import win32clipboard
import win32con
import os
import zipfile
import tempfile

class FileGrabber:
    @staticmethod
    def get_grabbed_content():
        """
        Simulates Ctrl+C.
        - If 1 file selected: Returns path to that file.
        - If Multiple files or Folder selected: Zips them and returns path to Zip.
        """
        # 1. Simulate Ctrl+C
        try:
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.5) 
        except KeyboardInterrupt:
            print("[FileGrabber] WARNING: You tried to grab the Terminal!")
            return None, "Don't grab the Terminal! Click a file first."
        except Exception as e:
            return None, f"Keyboard Error: {e}"

        # 2. Open Native Clipboard
        try:
            win32clipboard.OpenClipboard()
        except Exception:
            time.sleep(0.2)
            try:
                win32clipboard.OpenClipboard()
            except:
                return None, "Clipboard is locked by System."

        # 3. Read File List
        file_paths = []
        error_msg = None

        try:
            if win32clipboard.IsClipboardFormatAvailable(win32con.CF_HDROP):
                # data is a TUPLE of all selected file paths
                file_paths = win32clipboard.GetClipboardData(win32con.CF_HDROP)
            else:
                error_msg = "No files found (Did you copy text?)"
        except Exception as e:
            error_msg = f"Read Error: {e}"
        finally:
            win32clipboard.CloseClipboard()

        if not file_paths:
            return None, error_msg or "Clipboard Empty"

        # 4. DECISION LOGIC: Single File vs. Batch
        # If it's a single file (not a folder), return it directly
        if len(file_paths) == 1 and os.path.isfile(file_paths[0]):
            print(f"[FileGrabber] Single file detected: {file_paths[0]}")
            return file_paths[0], None
        
        # Otherwise (Multiple files OR a Folder), create a ZIP
        else:
            print(f"[FileGrabber] Batch/Folder detected. Zipping...")
            return FileGrabber._create_temp_zip(file_paths), None

    @staticmethod
    def _create_temp_zip(file_paths):
        """Compresses list of paths into a temporary zip file"""
        try:
            # Create a temp file like 'AirGesture_Batch.zip'
            temp_dir = tempfile.gettempdir()
            zip_path = os.path.join(temp_dir, "AirGesture_Bundle.zip")
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for path in file_paths:
                    if os.path.isfile(path):
                        # Add file (arcname ensures we don't save the full C:/Users/... path)
                        zipf.write(path, arcname=os.path.basename(path))
                    elif os.path.isdir(path):
                        # Recursively add folder
                        root_len = len(os.path.dirname(path))
                        for root, dirs, files in os.walk(path):
                            for file in files:
                                full_path = os.path.join(root, file)
                                # Relative path inside zip
                                rel_path = full_path[root_len:]
                                zipf.write(full_path, arcname=rel_path)
            
            return zip_path
        except Exception as e:
            print(f"[Zip Error] {e}")
            return None