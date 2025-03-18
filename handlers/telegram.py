import threading
import asyncio
from typing import Optional, Dict, Any
from telegram.ext import Application, CommandHandler
from . import NotificationHandler, get_timestamp

from config import TELEGRAM_CONFIG

class TelegramNotificationHandler(NotificationHandler):
    """Handler for Telegram notifications using a dedicated thread"""

    def __init__(self):
        self.enabled = TELEGRAM_CONFIG["enabled"]
        self.token = TELEGRAM_CONFIG["bot_token"]
        self.chat_id = TELEGRAM_CONFIG["chat_id"]
        self.application: Optional[Application] = None
        self.connected = False
        self.updater_running = False
        self.application_running = False
        self.shutdown_complete = False
        self.thread = None
        self.bot_loop = None
        self._queue = asyncio.Queue()
        self._stop_event = threading.Event()
    
    async def initialize(self) -> bool:
        if not self.enabled or not self.token or not self.chat_id:
            print(f"[{get_timestamp()}] ℹ️\u200B Telegram notifications disabled or missing credentials")
            return False
            
        try:
            # Start dedicated thread for Telegram bot
            self.thread = threading.Thread(target=self._run_telegram_bot, daemon=True)
            self.thread.start()
            
            # Wait for bot to connect or fail
            for _ in range(10):  # Wait up to 5 seconds
                if self.connected or self._stop_event.is_set():
                    break
                await asyncio.sleep(0.5)
            
            if self.connected:
                print(f"[{get_timestamp()}] ✅ Telegram notification handler initialized")
                return True
            else:
                print(f"[{get_timestamp()}] ❌ Telegram bot failed to connect")
                return False
            
        except Exception as e:
            print(f"[{get_timestamp()}] ❌ Failed to initialize Telegram: {str(e)}")
            self.connected = False
            return False
    
    async def status_command(self, update, context):
        """Handle the /status command by sending the current status"""
        if not self.connected:
            return
                
        try:
            # Windows-specific approach that doesn't rely on module imports
            status_data = None
            
            # Try to access the variables directly from globals() or through sys modules
            try:
                import sys
                
                # Find the module that contains our globals
                main_module = None
                for name, module in sys.modules.items():
                    if hasattr(module, 'start_time') and hasattr(module, 'successful_requests'):
                        main_module = module
                        break
                
                # If we found a suitable module, use it to create status data
                if main_module:
                    from datetime import datetime
                    
                    # Create status data directly from global variables
                    time_since_check = None
                    if hasattr(main_module, 'last_check_time') and main_module.last_check_time:
                        time_since_check = datetime.now() - main_module.last_check_time
                    
                    # Create status data dictionary
                    status_data = {
                        'runtime': datetime.now() - main_module.start_time if hasattr(main_module, 'start_time') else datetime.timedelta(seconds=0),
                        'successful_requests': main_module.successful_requests if hasattr(main_module, 'successful_requests') else 0,
                        'failed_requests': main_module.failed_requests if hasattr(main_module, 'failed_requests') else 0,
                        'last_check_time': main_module.last_check_time if hasattr(main_module, 'last_check_time') else None,
                        'last_check_success': main_module.last_check_success if hasattr(main_module, 'last_check_success') else False,
                        'monitored_cards': list(main_module.AVAILABLE_CARDS.keys()) if hasattr(main_module, 'AVAILABLE_CARDS') else [],
                        'time_since_check': time_since_check
                    }
                else:
                    # Last resort - hardcoded minimal status info
                    print(f"[{get_timestamp()}] ⚠️ Could not find main module, creating minimal status")
                    status_data = {
                        'runtime': datetime.timedelta(seconds=0),
                        'successful_requests': 0,
                        'failed_requests': 0,
                        'last_check_time': None,
                        'last_check_success': False,
                        'monitored_cards': [],
                        'time_since_check': None
                    }
                    
            except Exception as inner_e:
                print(f"[{get_timestamp()}] ⚠️ Error creating status data: {str(inner_e)}")
                status_data = None
                
            # Format and send the status message
            if status_data:
                status_message = self.format_status_message(status_data)
                await update.message.reply_text(status_message)
            else:
                # Send a basic response if we couldn't get status data
                await update.message.reply_text("The stock checker is running, but detailed status is not available.")
                print(f"[{get_timestamp()}] ⚠️ Could not retrieve status data")
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
    
    def _run_telegram_bot(self):
        """Run Telegram bot in a separate thread with its own event loop"""
        try:
            # Create new event loop for this thread
            self.bot_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.bot_loop)
            
            # Run the bot initialization and message loop
            self.bot_loop.run_until_complete(self._bot_main())
        except Exception as e:
            print(f"[{get_timestamp()}] ❌ Telegram bot thread error: {str(e)}")
            self._stop_event.set()
        finally:
            self.connected = False
            if self.bot_loop and not self.bot_loop.is_closed():
                self.bot_loop.close()
    
    async def _bot_main(self):
        """Main async function for the Telegram bot thread"""
        try:
            # Initialize application
            self.application = (
                Application.builder()
                .token(self.token)
                .read_timeout(30)
                .write_timeout(30)
                .build()
            )
            
            # Add command handlers
            self.application.add_handler(CommandHandler("status", self.status_command))
            
            # Initialize and start application
            await self.application.initialize()
            await self.application.start()
            self.application_running = True
            
            # Start polling
            await self.application.updater.start_polling()
            self.updater_running = True
            self.connected = True
            
            # Process send queue in background
            asyncio.create_task(self._process_queue())
            
            # Wait until stop event is set
            while not self._stop_event.is_set():
                await asyncio.sleep(0.1)
            
            # Clean shutdown
            await self._shutdown_bot()
        except Exception as e:
            print(f"[{get_timestamp()}] ❌ Error in Telegram bot main loop: {str(e)}")
            self.connected = False
    
    async def _process_queue(self):
        """Process messages from queue in background"""
        while not self._stop_event.is_set():
            try:
                # Get message with timeout to allow checking stop_event
                try:
                    # Use a shorter timeout to be more responsive to stop events
                    item = await asyncio.wait_for(self._queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    # Check if we should exit before trying again
                    if self._stop_event.is_set():
                        break
                    continue
                except RuntimeError as e:
                    # Handle event loop closed errors
                    if "Event loop is closed" in str(e):
                        break
                    raise
                    
                msg_type, data = item
                
                # Check again if we should exit before processing
                if self._stop_event.is_set():
                    break
                    
                if msg_type == "stock":
                    product_name, price, url, in_stock = data
                    await self._send_stock_alert_internal(product_name, price, url, in_stock)
                elif msg_type == "status":
                    await self._send_status_update_internal(data)
                elif msg_type == "startup":
                    await self._send_startup_message_internal(data)
                
                self._queue.task_done()
            except Exception as e:
                if "Event loop is closed" in str(e) or self._stop_event.is_set():
                    break
                print(f"[{get_timestamp()}] ❌ Error processing Telegram message queue: {str(e)}")
    
    async def _shutdown_bot(self):
        """Internal method to shutdown the bot"""
        if self.updater_running:
            try:
                await self.application.updater.stop()
                self.updater_running = False
            except Exception as e:
                print(f"[{get_timestamp()}] ⚠️ Error stopping Telegram updater: {str(e)}")
        
        if self.application_running:
            try:
                await self.application.stop()
                self.application_running = False
            except Exception as e:
                print(f"[{get_timestamp()}] ⚠️ Error stopping Telegram application: {str(e)}")
        
        try:
            await self.application.shutdown()
        except Exception as e:
            print(f"[{get_timestamp()}] ⚠️ Error shutting down Telegram application: {str(e)}")
    
    async def shutdown(self) -> None:
        """
        Gracefully shutdown the Telegram notification handler.
        """
        if self.shutdown_complete:
            return
            
        # Signal the thread to stop
        self._stop_event.set()
        
        # Wait for the thread to terminate
        if self.thread and self.thread.is_alive():
            print(f"[{get_timestamp()}] ⏳ Waiting for Telegram thread to shut down...")
            # Don't join in async context - can lead to deadlocks
            # Use a shorter timeout
            self.thread.join(timeout=2.0)
            
            # If thread is still alive, it's stuck
            if self.thread.is_alive():
                print(f"[{get_timestamp()}] ⚠️ Telegram thread did not shut down cleanly, forcing exit")
                # Don't try to force it further - Python will clean up daemon threads
        
        self.shutdown_complete = True
        print(f"[{get_timestamp()}] ✅ Telegram notification handler shutdown")
    
    # Methods for sending messages - queue them to the bot thread
    async def send_stock_alert(self, product_name: str, price: str, url: str, in_stock: bool) -> None:
        if not self.enabled or not self.connected:
            return
        await self._queue.put(("stock", (product_name, price, url, in_stock)))
    
    async def send_status_update(self, data: Dict[str, Any]) -> None:
        if not self.enabled or not self.connected:
            return
        await self._queue.put(("status", data))
    
    async def send_startup_message(self, message: str) -> None:
        if not self.enabled or not self.connected:
            return
        await self._queue.put(("startup", message))
    
    # Internal message sending methods run in the bot thread
    async def _send_stock_alert_internal(self, product_name: str, price: str, url: str, in_stock: bool) -> None:
        status = "✅ IN STOCK" if in_stock else "❌ OUT OF STOCK"
        message = f"""🔔 NVIDIA Stock Alert
{status}: {product_name}
💰 Price: {price}
🔗 Link: {url}"""

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
    
    async def _send_status_update_internal(self, data: Dict[str, Any]) -> None:
        message = self.format_status_message(data)
        
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
    
    async def _send_startup_message_internal(self, message: str) -> None:
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