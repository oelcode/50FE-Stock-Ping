from typing import Optional
import aiohttp
from . import NotificationHandler, get_timestamp

from config import HOMEASSISTANT_CONFIG

class HomeAssistantNotificationHandler(NotificationHandler):
    """Handler for Home Assistant notifications"""
    
    def __init__(self):
        self.enabled = HOMEASSISTANT_CONFIG["enabled"]
        self.ha_url = HOMEASSISTANT_CONFIG["ha_url"].rstrip('/')
        self.ha_token = HOMEASSISTANT_CONFIG["ha_token"]
        self.notification_service = HOMEASSISTANT_CONFIG["notification_service"]
        self.connected = False
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> bool:
        if not self.enabled or not self.ha_token or not self.ha_url:
            print(f"[{get_timestamp()}] ℹ️ Home Assistant notifications disabled or missing credentials")
            return False
            
        try:
            # Create aiohttp session with proper headers
            self.session = aiohttp.ClientSession(headers={
                "Authorization": f"Bearer {self.ha_token}",
                "Content-Type": "application/json",
            })
            
            # Test the connection
            async with self.session.get(f"{self.ha_url}/api/") as response:
                if response.status == 200:
                    self.connected = True
                    print(f"[{get_timestamp()}] ✅ Home Assistant notification handler initialized")
                    return True
                else:
                    print(f"[{get_timestamp()}] ❌ Failed to connect to Home Assistant: Status {response.status}")
                    return False
                    
        except Exception as e:
            print(f"[{get_timestamp()}] ❌ Failed to initialize Home Assistant connection: {str(e)}")
            self.connected = False
            return False
    
    async def shutdown(self) -> None:
        if self.session:
            try:
                await self.session.close()
                print(f"[{get_timestamp()}] ✅ Home Assistant notification handler shutdown")
            except Exception as e:
                print(f"[{get_timestamp()}] ⚠️ Error during Home Assistant shutdown: {str(e)}")
    
    async def send_stock_alert(self, sku: str, price: str, url: str, in_stock: bool) -> None:
        if not self.enabled or not self.connected:
            return
            
        status = "IN STOCK" if in_stock else "OUT OF STOCK"
        
        notification_data = {
            "title": "NVIDIA Stock Alert",
            "message": f"{status}: {sku}\nPrice: {price}",
            "target": self.notification_service,
            "data": {
                "url": url,
                "tag": f"nvidia_stock_{sku}",
                "color": "#00ff00" if in_stock else "#ff0000",
                "priority": "high",
                "sticky": True,
                "actions": [
                    {
                        "action": "URI",
                        "title": "View Product",
                        "uri": url
                    }
                ]
            }
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
            "message": message,
            "title": "NVIDIA Stock Checker Status",
            "data": {
                "push": {
                    "sound": "default",
                    "priority": "normal"
                },
                "tag": "nvidia_stock_status",
                "color": "#0099ff"
            }
        }

        await self._send_notification(notification_data)
    
    async def send_startup_message(self, message: str) -> None:
        if not self.enabled or not self.connected:
            return
            
        notification_data = {
            "message": message,
            "title": "NVIDIA Stock Checker",
            "data": {
                "push": {
                    "sound": "default",
                    "priority": "normal"
                },
                "tag": "nvidia_stock_startup",
                "color": "#0099ff"
            }
        }

        await self._send_notification(notification_data)

    def format_duration(self, duration):
        """Format a duration into a readable string"""
        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60
        return f"{hours} hours {minutes} minutes"

    async def _send_notification(self, notification_data: dict) -> None:
        """Helper method to send a notification through Home Assistant"""
        if not self.session:
            return
            
        try:
            url = f"{self.ha_url}/api/services/notify/{self.notification_service}"
            async with self.session.post(url, json=notification_data) as response:
                if response.status != 200:
                    print(f"[{get_timestamp()}] ❌ Failed to send Home Assistant notification: Status {response.status}")
                    self.connected = False
                    
        except Exception as e:
            print(f"[{get_timestamp()}] ❌ Failed to send Home Assistant notification: {str(e)}")
            self.connected = False
