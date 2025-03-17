import platform
import subprocess
from . import NotificationHandler, get_timestamp

from config import SOUND_CONFIG

class SoundNotificationHandler(NotificationHandler):
    """Handler for sound notifications"""
    
    def __init__(self):
        self.enabled = SOUND_CONFIG["enabled"]
        self.system = platform.system()
    
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
