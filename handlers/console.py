from . import NotificationHandler, get_timestamp

from config import CONSOLE_CONFIG

class ConsoleNotificationHandler(NotificationHandler):
    """Handler for console notifications"""
    
    def __init__(self):
        self.enabled = CONSOLE_CONFIG["enabled"]
        self.log_stock_checks = CONSOLE_CONFIG["log_stock_checks"]
    
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
