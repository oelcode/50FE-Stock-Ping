import json
from typing import Optional
import aiohttp
from . import NotificationHandler, get_timestamp

from config import NTFY_CONFIG

class NtfyNotificationHandler(NotificationHandler):
    """Handler for ntfy notifications"""
    
    def __init__(self):
        self.enabled = NTFY_CONFIG["enabled"]
        self.server_url = NTFY_CONFIG["server_url"].rstrip('/')
        self.topic = NTFY_CONFIG["topic"]
        self.username = NTFY_CONFIG["username"]
        self.password = NTFY_CONFIG["password"]
        self.priority = NTFY_CONFIG["priority"]
        self.access_token = NTFY_CONFIG["access_token"]
        self.connected = False
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> bool:
        if not self.enabled or not self.topic:
            print(f"[{get_timestamp()}] ℹ️ ntfy notifications disabled or missing topic")
            return False
            
        try:
            # Setup basic auth if credentials are provided
            auth = None
            if self.username and self.password:
                auth = aiohttp.BasicAuth(self.username, self.password)
            
            # Create aiohttp session
            self.session = aiohttp.ClientSession(auth=auth)
            
            # Test the connection with a simple ping
            test_data = {
                "topic": self.topic,
                "message": "Initializing connection",
                "priority": "min",
                "tags": ["test"]
            }
            
            async with self.session.post(f"{self.server_url}/{self.topic}", json=test_data) as response:
                if response.status == 200:
                    self.connected = True
                    print(f"[{get_timestamp()}] ✅ ntfy notification handler initialized")
                    return True
                else:
                    print(f"[{get_timestamp()}] ❌ Failed to connect to ntfy: Status {response.status}")
                    return False
                    
        except Exception as e:
            print(f"[{get_timestamp()}] ❌ Failed to initialize ntfy connection: {str(e)}")
            self.connected = False
            return False
    
    async def shutdown(self) -> None:
        if self.session:
            try:
                await self.session.close()
                print(f"[{get_timestamp()}] ✅ ntfy notification handler shutdown")
            except Exception as e:
                print(f"[{get_timestamp()}] ⚠️ Error during ntfy shutdown: {str(e)}")
    
    async def send_stock_alert(self, sku: str, price: str, url: str, in_stock: bool) -> None:
        if not self.enabled or not self.connected:
            return
            
        status = "IN STOCK" if in_stock else "OUT OF STOCK"
        
        notification_data = {
            "topic": self.topic,
            "title": "NVIDIA Stock Alert",
            "message": f"{status}: {sku}\nPrice: {price}",
            "priority": "high" if in_stock else "default",
            "tags": ["nvidia", "stock", "alert"] + (["instock"] if in_stock else ["outofstock"]),
            "click": url,  # URL to open when notification is clicked
            "actions": [  # Custom actions (supported by some clients)
                {
                    "action": "view",
                    "label": "View Product",
                    "url": url
                }
            ]
        }

        await self._send_notification(notification_data)
    
    async def send_status_update(self, data: dict) -> None:
        if not self.enabled or not self.connected:
            return

        status_text = "Successful" if data['last_check_success'] else "Failed"
        
        last_check_str = "No checks completed"
        if data['last_check_time']:
            last_check_str = data['last_check_time'].strftime("%H:%M:%S %d/%m/%Y")
            minutes_since = data['time_since_check'].seconds // 60
            last_check_str += f" ({minutes_since}m ago)"

        message = (
            f"Running for: {self.format_duration(data['runtime'])}\n"
            f"Requests: {data['successful_requests']:,} successful, {data['failed_requests']:,} failed\n"
            f"Last check: {last_check_str} ({status_text})\n"
            f"Monitoring: {'None' if not data['monitored_cards'] else ', '.join(data['monitored_cards'])}"
        )

        notification_data = {
            "topic": self.topic,
            "title": "NVIDIA Stock Checker Status",
            "message": message,
            "priority": "low",
            "tags": ["nvidia", "status", "update"],
        }

        await self._send_notification(notification_data)
    
    async def send_startup_message(self, message: str) -> None:
        if not self.enabled or not self.connected:
            return
            
        notification_data = {
            "topic": self.topic,
            "title": "NVIDIA Stock Checker",
            "message": message,
            "priority": "default",
            "tags": ["nvidia", "startup"]
        }

        await self._send_notification(notification_data)

    def format_duration(self, duration):
        """Format a duration into a readable string"""
        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60
        return f"{hours} hours {minutes} minutes"

    async def _send_notification(self, notification_data: dict) -> None:
        """Helper method to send a notification through ntfy"""
        if not self.session:
            return
            
        try:
            url = f"{self.server_url}/{self.topic}"
            async with self.session.post(url, json=notification_data) as response:
                if response.status != 200:
                    print(f"[{get_timestamp()}] ❌ Failed to send ntfy notification: Status {response.status}")
                    self.connected = False
                    
        except Exception as e:
            print(f"[{get_timestamp()}] ❌ Failed to send ntfy notification: {str(e)}")
            self.connected = False