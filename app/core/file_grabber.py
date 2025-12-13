import time
import pyautogui
import win32clipboard
import win32con

class FileGrabber:
    @staticmethod
    def get_selected_file():
        """
        Simulates Ctrl+C and reads file paths directly from Windows API.
        Includes protection against grabbing the Terminal window.
        """
        # 1. Simulate Ctrl+C
        try:
            # We wrap this in a try-block to catch the "Kill Signal"
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.5) # Give Windows time to process
            
        except KeyboardInterrupt:
            # THIS IS THE FIX: We catch the suicide attempt!
            print("[FileGrabber] WARNING: You tried to grab the Terminal! Click a file first.")
            return None, "Don't grab the Terminal! Click a file first."
            
        except Exception as e:
            return None, f"Keyboard Error: {e}"

        # 2. Open Native Clipboard
        try:
            win32clipboard.OpenClipboard()
        except Exception:
            # If locked, wait and retry once
            time.sleep(0.2)
            try:
                win32clipboard.OpenClipboard()
            except:
                return None, "Clipboard is locked by System."

        # 3. Read Data (CF_HDROP = File List)
        file_path = None
        error_msg = None

        try:
            if win32clipboard.IsClipboardFormatAvailable(win32con.CF_HDROP):
                # Get list of files
                data = win32clipboard.GetClipboardData(win32con.CF_HDROP)
                if data:
                    # 'data' is a tuple of strings, we take the first one
                    file_path = data[0]
            else:
                error_msg = "No files found (Did you copy text?)"
        
        except Exception as e:
            error_msg = f"Read Error: {e}"
        
        finally:
            # CRITICAL: Always close the clipboard!
            win32clipboard.CloseClipboard()

        # 4. Return Result
        if file_path:
            print(f"[FileGrabber] Native Success: {file_path}")
            return file_path, None
        else:
            return None, error_msg or "Clipboard Empty"