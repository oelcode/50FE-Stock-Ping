import json
import os
from . import NotificationHandler, get_timestamp

class ConsoleNotificationHandler(NotificationHandler):
    """Handler for console notifications"""
    
    DEFAULT_CONFIG = {
        "enabled": True,
        "log_stock_checks": False
    }
    
    def __init__(self):
        self.config = self.load_config()
        self.enabled = self.config["enabled"]
        self.log_stock_checks = self.config["log_stock_checks"]
    
    def load_config(self) -> dict:
        """Load configuration from local config file"""
        handler_dir = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(handler_dir, "console_config.json")
        
        config = self.DEFAULT_CONFIG.copy()
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    file_config = json.load(f)
                config.update(file_config)
            else:
                with open(config_file, 'w') as f:
                    json.dump(self.DEFAULT_CONFIG, f, indent=4)
                print(f"[{get_timestamp()}] Created default console config at: {config_file}")
        except Exception as e:
            print(f"[{get_timestamp()}] ⚠️ Error loading console config: {str(e)}")
        
        return config
    
    async def initialize(self) -> bool:
        if not self.enabled:
            print(f"[{get_timestamp()}] ℹ️ Console notifications disabled")
            return False
        print(f"[{get_timestamp()}] Console notification handler initialized")
        return True
    
    async def shutdown(self) -> None:
        pass
    
    async def send_stock_alert(self, sku: str, price: str, url: str, in_stock: bool) -> None:
        if not self.enabled:
            return
            
        status = "✅ IN STOCK" if in_stock else "❌ OUT OF STOCK"
        timestamp = get_timestamp()
        
        if self.log_stock_checks or in_stock:
            print(f"[{timestamp}] {status}: {sku} - {price}")
            if in_stock:
                print(f"[{timestamp}] 🔗 URL: {url}")
    
    async def send_status_update(self, message: str) -> None:
        if not self.enabled:
            return
        print(f"\n[{get_timestamp()}] {message}\n")
    
    async def send_startup_message(self, message: str) -> None:
        if not self.enabled:
            return
        print(f"[{get_timestamp()}] {message}")