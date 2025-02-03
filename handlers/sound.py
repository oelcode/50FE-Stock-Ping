import json
import os
import platform
import subprocess
from . import NotificationHandler, get_timestamp

class SoundNotificationHandler(NotificationHandler):
    """Handler for sound notifications"""
    
    DEFAULT_CONFIG = {
        "enabled": True
    }
    
    def __init__(self):
        self.config = self.load_config()
        self.enabled = self.config["enabled"]
        self.system = platform.system()
    
    def load_config(self) -> dict:
        """Load configuration from local config file"""
        handler_dir = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(handler_dir, "sound_config.json")
        
        config = self.DEFAULT_CONFIG.copy()
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    file_config = json.load(f)
                config.update(file_config)
            else:
                with open(config_file, 'w') as f:
                    json.dump(self.DEFAULT_CONFIG, f, indent=4)
                print(f"[{get_timestamp()}] Created default sound config at: {config_file}")
        except Exception as e:
            print(f"[{get_timestamp()}] ⚠️ Error loading sound config: {str(e)}")
        
        return config
    
    async def initialize(self) -> bool:
        if not self.enabled:
            print(f"[{get_timestamp()}] ℹ️ Sound notifications disabled")
            return False
            
        print(f"[{get_timestamp()}] Sound notification handler initialized")
        return True
    
    async def shutdown(self) -> None:
        pass
    
    async def send_stock_alert(self, sku: str, price: str, url: str, in_stock: bool) -> None:
        if not self.enabled or not in_stock:
            return
            
        if self.system == 'Windows':
            try:
                import winsound
                winsound.MessageBeep()
            except Exception as e:
                print(f"[{get_timestamp()}] ⚠️ Failed to play Windows sound: {e}")
        
        elif self.system == 'Darwin':  # macOS
            try:
                subprocess.run(['afplay', '/System/Library/Sounds/Ping.aiff'], check=True)
            except subprocess.SubprocessError as e:
                print(f"[{get_timestamp()}] ⚠️ Failed to play macOS sound: {e}")
        
        else:  # Linux or other systems
            print(f"[{get_timestamp()}] ℹ️ Sound not supported on this operating system")
    
    async def send_status_update(self, message: str) -> None:
        # Sound handler doesn't need to handle status updates
        pass
    
    async def send_startup_message(self, message: str) -> None:
        # Sound handler doesn't need to handle startup messages
        pass