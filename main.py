from app.ui.tray_icon import SystemTrayApp

if __name__ == "__main__":
    print("Starting MyDrop V2...")
    
    # Initialize the System Tray Interface
    tray = SystemTrayApp()
    
    # Start the application loop
    tray.run()