from typing import Optional
from telegram.ext import Application, CommandHandler
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
        self.updater_running = False
        self.application_running = False
        self.shutdown_complete = False
    
    async def initialize(self) -> bool:
        if not self.enabled or not self.token or not self.chat_id:
            print(f"[{get_timestamp()}] ℹ️\u200B Telegram notifications disabled or missing credentials")
            return False
            
        try:
            self.application = (
                Application.builder()
                .token(self.token)
                .read_timeout(30)
                .write_timeout(30)
                .build()
            )
            
            # Add command handlers
            self.application.add_handler(CommandHandler("status", self.status_command))
            
            # Initialize the application
            await self.application.initialize()
            await self.application.start()
            self.application_running = True
            
            await self.application.updater.start_polling()
            self.updater_running = True
            
            self.connected = True
            print(f"[{get_timestamp()}] ✅ Telegram notification handler initialized")
            return True
            
        except Exception as e:
            print(f"[{get_timestamp()}] ❌ Failed to initialize Telegram: {str(e)}")
            self.connected = False
            self.updater_running = False
            self.application_running = False
            return False
    
    async def status_command(self, update, context):
        """Handle the /status command by sending the current status"""
        if not self.connected:
            return
            
        try:
            # In the 50check.py, the function is named generate_status_data()
            # Import it from the global scope to avoid circular imports
            import sys
            main_module = sys.modules['__main__']
            if hasattr(main_module, 'generate_status_data'):
                status_data = main_module.generate_status_data()
                status_message = self.format_status_message(status_data)
                await update.message.reply_text(status_message)
            else:
                await update.message.reply_text("Status information is not available.")
                print(f"[{get_timestamp()}] ⚠️ generate_status_data function not found in main module")
        except Exception as e:
            print(f"[{get_timestamp()}] ❌ Error handling status command: {str(e)}")
            await update.message.reply_text("An error occurred while retrieving status information.")
    
    def format_status_message(self, data):
        """Format the status data into a readable message"""
        status_check = "✅" if data.get('last_check_success', False) else "❌"
        status_text = "Successful" if data.get('last_check_success', False) else "Failed"
        
        last_check_str = "No checks completed"
        if data.get('last_check_time'):
            last_check_str = data['last_check_time'].strftime("%H:%M:%S %d/%m/%Y")
            if data.get('time_since_check'):
                minutes_since = data.get('time_since_check').seconds // 60
                last_check_str += f" ({minutes_since}m ago)"

        message = f"""📊 NVIDIA Stock Checker Status
⏱️ Running for: {self.format_duration(data.get('runtime', 0))}
📈 Requests: {data.get('successful_requests', 0):,} successful, {data.get('failed_requests', 0):,} failed
{status_check} Last check: {last_check_str} ({status_text})
🎯 Monitoring: {'None' if not data.get('monitored_cards', []) else ', '.join(data['monitored_cards'])}"""

        return message
    
    async def shutdown(self) -> None:
        """
        Gracefully shutdown the Telegram notification handler.
        Only print success message after all shutdown steps are completed.
        """
        # Prevent multiple shutdowns
        if self.shutdown_complete:
            return
            
        # If application was never created or initialized, just mark as done
        if not self.application:
            print(f"[{get_timestamp()}] ✅ Telegram notification handler shutdown (no application)")
            self.shutdown_complete = True
            return
            
        # Reset state before shutdown
        was_connected = self.connected
        self.connected = False
        
        # Count successful operations to determine overall success
        successful_steps = 0
        total_steps = 0
        
        # 1. Stop the updater if it's running
        if self.updater_running:
            total_steps += 1
            try:
                await self.application.updater.stop()
                self.updater_running = False
                successful_steps += 1
            except Exception as e:
                print(f"[{get_timestamp()}] ⚠️ Error stopping Telegram updater: {str(e)}")
        
        # 2. Stop the application if it's running
        if self.application_running:
            total_steps += 1
            try:
                await self.application.stop()
                self.application_running = False
                successful_steps += 1
            except Exception as e:
                print(f"[{get_timestamp()}] ⚠️ Error stopping Telegram application: {str(e)}")
        
        # 3. Always try to shutdown the application
        total_steps += 1
        try:
            await self.application.shutdown()
            successful_steps += 1
        except Exception as e:
            print(f"[{get_timestamp()}] ⚠️ Error shutting down Telegram application: {str(e)}")
        
        # Track partial or complete success
        if successful_steps == total_steps:
            print(f"[{get_timestamp()}] ✅ Telegram notification handler shutdown (complete)")
        elif successful_steps > 0:
            print(f"[{get_timestamp()}] ✅ Telegram notification handler shutdown (partial: {successful_steps}/{total_steps} steps)")
        else:
            print(f"[{get_timestamp()}] ⚠️ Telegram notification handler shutdown failed")
            
        # Mark shutdown as complete to prevent duplicate calls
        self.shutdown_complete = True
    
    async def send_stock_alert(self, product_name: str, price: str, url: str, in_stock: bool) -> None:
        if not self.enabled or not self.connected:
            return
                
        status = "✅ IN STOCK" if in_stock else "❌ OUT OF STOCK"
        message = f"""🔔 NVIDIA Stock Alert
    {status}: {product_name}
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
            self.updater_running = False
            self.application_running = False

    def format_duration(self, duration):
        """Format a duration into a readable string, showing only non-zero time units"""
        total_seconds = duration.seconds
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        # Build the output string with only non-zero units
        parts = []
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if seconds > 0 or not parts:  # Include seconds if it's the only non-zero value
            parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
            
        return " ".join(parts)

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
            self.updater_running = False
            self.application_running = False