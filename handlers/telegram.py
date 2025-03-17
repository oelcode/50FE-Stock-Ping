from typing import Optional
from telegram.ext import Application
from . import NotificationHandler, get_timestamp

from config import TELEGRAM_CONFIG

class TelegramNotificationHandler(NotificationHandler):
    """Handler for Telegram notifications"""

    def __init__(self):
        self.enabled = TELEGRAM_CONFIG["enabled"]
        self.token = TELEGRAM_CONFIG["bot_token"]
        self.chat_id = TELEGRAM_CONFIG["chat_id"]
        self.application: Optional[Application] = None
        self.connected = False
    
    async def initialize(self) -> bool:
        if not self.enabled or not self.token or not self.chat_id:
            print(f"[{get_timestamp()}] ℹ️ Telegram notifications disabled or missing credentials")
            return False
            
        try:
            self.application = (
                Application.builder()
                .token(self.token)
                .read_timeout(30)
                .write_timeout(30)
                .build()
            )
            
            # Initialize the application
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            self.connected = True
            print(f"[{get_timestamp()}] ✅ Telegram notification handler initialized")
            return True
            
        except Exception as e:
            print(f"[{get_timestamp()}] ❌ Failed to initialize Telegram: {str(e)}")
            self.connected = False
            return False
    
    async def shutdown(self) -> None:
        if self.application:
            try:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                print(f"[{get_timestamp()}] ✅ Telegram notification handler shutdown")
            except Exception as e:
                print(f"[{get_timestamp()}] ⚠️ Error during Telegram shutdown: {str(e)}")
    
    async def send_stock_alert(self, sku: str, price: str, url: str, in_stock: bool) -> None:
        if not self.enabled or not self.connected:
            return
                
        status = "✅ IN STOCK" if in_stock else "❌ OUT OF STOCK"
        message = f"""🔔 NVIDIA Stock Alert
{status}: {sku}
💰 Price: {price}
🔗 Link: {url}"""

        await self._send_message(message)
    
    async def send_status_update(self, data: dict) -> None:
        if not self.enabled or not self.connected:
            return

        status_check = "✅" if data['last_check_success'] else "❌"
        status_text = "Successful" if data['last_check_success'] else "Failed"
        
        last_check_str = "No checks completed"
        if data['last_check_time']:
            last_check_str = data['last_check_time'].strftime("%H:%M:%S %d/%m/%Y")
            minutes_since = data['time_since_check'].seconds // 60
            last_check_str += f" ({minutes_since}m ago)"

        message = f"""📊 NVIDIA Stock Checker Status Update
⏱️ Running for: {self.format_duration(data['runtime'])}
📈 Requests: {data['successful_requests']:,} successful, {data['failed_requests']:,} failed
{status_check} Last check: {last_check_str} ({status_text})
🎯 Monitoring: {'None' if not data['monitored_cards'] else ', '.join(data['monitored_cards'])}"""

        await self._send_message(message)
    
    async def send_startup_message(self, message: str) -> None:
        if not self.enabled or not self.connected:
            return
            
        try:
            await self.application.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
        except Exception as e:
            print(f"[{get_timestamp()}] ❌ Failed to send Telegram startup message: {str(e)}")
            self.connected = False

    def format_duration(self, duration):
        """Format a duration into a readable string"""
        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60
        return f"{hours} hours {minutes} minutes"

    async def _send_message(self, message: str) -> None:
        """Helper method to handle the actual sending"""
        try:
            await self.application.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
        except Exception as e:
            print(f"[{get_timestamp()}] ❌ Failed to send Telegram message: {str(e)}")
            self.connected = False
