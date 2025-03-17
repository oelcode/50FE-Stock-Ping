from . import NotificationHandler, get_timestamp

from config import CONSOLE_CONFIG

class ConsoleNotificationHandler(NotificationHandler):
    """Handler for console notifications"""
    
    def __init__(self):
        self.enabled = CONSOLE_CONFIG["enabled"]
    
    async def initialize(self) -> bool:
        if not self.enabled:
            print(f"[{get_timestamp()}] ℹ️ Console notifications disabled")
            return False
        print(f"[{get_timestamp()}] Console notification handler initialized")
        return True
    
    async def shutdown(self) -> None:
        pass
    
    async def send_stock_alert(self, product_name: str, price: str, url: str, in_stock: bool) -> None:
        if not self.enabled:
            return
            
        status = "✅ IN STOCK" if in_stock else "❌ OUT OF STOCK"
        timestamp = get_timestamp()
        
        print(f"[{timestamp}] {status}: {product_name} - {price}")
        if in_stock:
            print(f"[{timestamp}] 🔗 URL: {url}")
    
    async def send_status_update(self, data: dict) -> None:
        if not self.enabled:
            return
        
        status_text = "Successful" if data['last_check_success'] else "Failed"
        
        last_check_str = "No checks completed"
        if data['last_check_time']:
            last_check_str = data['last_check_time'].strftime("%H:%M:%S %d/%m/%Y")
            minutes_since = data['time_since_check'].seconds // 60
            last_check_str += f" ({minutes_since}m ago)"

        message = (
            f"Runtime: {str(data['runtime'])}\n"
            f"Requests: {data['successful_requests']:,} successful, {data['failed_requests']:,} failed\n"
            f"Last check: {last_check_str} ({status_text})\n"
            f"Monitoring: {'None' if not data['monitored_cards'] else ', '.join(data['monitored_cards'])}"
        )

        print(f"\n[{get_timestamp()}] {message}\n")
    
    async def send_startup_message(self, message: str) -> None:
        if not self.enabled:
            return
        print(f"[{get_timestamp()}] {message}")
