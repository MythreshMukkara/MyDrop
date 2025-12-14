"""
=============================================================================
MODULE: file_grabber.py
DESCRIPTION: 
    Utility class for accessing selected files via the Windows Clipboard.
    
    Capabilities:
    1. Clipboard Automation: Simulates 'Ctrl+C' to copy selected files.
    2. Windows API Access: Uses pywin32 to read file paths directly from clipboard memory.
    3. Smart Batching: 
       - If 1 file: Returns path.
       - If multiple files or folder: Automatically zips them into a temp file.
    4. Error Handling: Skips locked/admin-only files during zipping to prevent crashes.

USAGE:
    filepath, error = FileGrabber.get_grabbed_content()
=============================================================================
"""

#import statements
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
        Orchestrates the grab process: Trigger Copy -> Read Clipboard -> Decide Zip vs Single.
        Returns: (path_to_file_or_zip, error_message)
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
        """Compresses list of paths into a temporary zip file, skipping errors."""
        """
        Iterates through file paths and compresses them into a temp ZIP.
        Includes logic to handle recursion for folders and 'try-catch' for permission errors.
        """
        try:
            temp_dir = tempfile.gettempdir()
            zip_path = os.path.join(temp_dir, "MyDrop_Bundle.zip")
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for path in file_paths:
                    # Case 1: It's a single File
                    if os.path.isfile(path):
                        try:
                            zipf.write(path, arcname=os.path.basename(path))
                        except Exception as e:
                            print(f"[Zip Error] Skipped file {path}: {e}")

                    # Case 2: It's a Folder
                    elif os.path.isdir(path):
                        root_len = len(os.path.dirname(path))
                        for root, dirs, files in os.walk(path):
                            for file in files:
                                full_path = os.path.join(root, file)
                                try:
                                    # Logic to keep folder structure inside zip
                                    rel_path = full_path[root_len:]
                                    zipf.write(full_path, arcname=rel_path)
                                except Exception as e:
                                    # If a specific file is locked/denied, SKIP IT and continue
                                    print(f"[Zip Error] Skipped {file}: {e}")
            
            return zip_path
        except Exception as e:
            print(f"[Zip Critical Fail] {e}")
            return None
            
            return zip_path
        except Exception as e:
            print(f"[Zip Error] {e}")
            return None