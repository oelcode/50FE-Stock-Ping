import requests
import time
import webbrowser
import subprocess
import argparse
import platform
import telegram
from telegram.ext import Application, CommandHandler
import asyncio
from datetime import datetime, timedelta
import json
import signal
import sys
import threading
import traceback

# Import winsound only on Windows
if platform.system() == 'Windows':
    import winsound

# Import configuration
from config import (
    PRODUCT_CONFIG_CARDS,
    STATUS_UPDATES,
    TELEGRAM_CONFIG,
    NTFY_CONFIG,
    NOTIFICATION_CONFIG,
    API_CONFIG,
    SKU_CHECK_API_CONFIG,
    LOCALE_CONFIG,
    SKU_CHECK_CONFIG
)

# Get enabled Cards based on configuration
AVAILABLE_CARDS = {card: config["enabled"]
                 for card, config in PRODUCT_CONFIG_CARDS.items()
                 if config["enabled"]}

# API configuration
API_URL = API_CONFIG["url"]
params = API_CONFIG["params"]
headers = API_CONFIG["headers"]
NVIDIA_BASE_URL = API_CONFIG["base_url"]

# Locale configuration
currency = LOCALE_CONFIG["currency"]
country = LOCALE_CONFIG["country"]

# Initialize global variables
def init_globals():
    global last_stock_status, start_time, successful_requests, failed_requests
    global last_check_time, last_check_success, last_console_status_time
    global last_telegram_status_time, telegram_bot, running, loop_manager
    global last_sku_check_time, cached_skus, sku_to_name_map
    
    last_stock_status = {}
    start_time = datetime.now()
    successful_requests = 0
    failed_requests = 0
    last_check_time = None
    last_check_success = True
    last_console_status_time = datetime.now()
    last_telegram_status_time = datetime.now()
    telegram_bot = None
    running = True
    loop_manager = None
    last_sku_check_time = None
    cached_skus = []
    sku_to_name_map = {}

# Initialize globals
init_globals()

def handle_product_mismatch(api_products, configured_products, telegram_bot, loop_manager):
    """
    Handle mismatch between API products and configured products.
    Sends notifications and exits after 5 attempts.
    
    Args:
        api_products (dict): Dictionary of SKU to product name from API
        configured_products (list): List of configured product names
        telegram_bot: Telegram bot instance
        loop_manager: AsyncLoopManager instance
    """
    # Find missing products
    missing_products = []
    for product in configured_products:
        if not any(product.lower() in name.lower() for name in api_products.values()):
            missing_products.append(product)
    
    if not missing_products:
        return True  # No mismatch, continue normal operation
    
    # Format message
    mismatch_message = f"""⚠️ CRITICAL: Product Mismatch Detected!
    
The following configured products are not available in the API:
{', '.join(missing_products)}

Available products in API:
{', '.join(api_products.values())}

This script will exit after 5 warning attempts."""

    remaining_attempts = 5
    while remaining_attempts > 0:
        timestamp = get_timestamp()
        
        # Console notification
        print(f"\n[{timestamp}] {mismatch_message}")
        print(f"[{timestamp}] ⚠️ {remaining_attempts} warning{'s' if remaining_attempts > 1 else ''} remaining before exit")
        
        # Sound notification
        if NOTIFICATION_CONFIG["play_sound"]:
            play_notification_sound()
        
        # Telegram notification
        if TELEGRAM_CONFIG["enabled"] and telegram_bot and telegram_bot.connected:
            try:
                telegram_message = f"{mismatch_message}\n\n⏳ {remaining_attempts} warning{'s' if remaining_attempts > 1 else ''} remaining before exit"
                loop_manager.run_coroutine(telegram_bot.send_message(telegram_message))
            except Exception as e:
                print(f"[{timestamp}] ❌ Failed to send Telegram mismatch notification: {str(e)}")
        
        remaining_attempts -= 1
        if remaining_attempts > 0:
            time.sleep(300)  # Wait 5 minutes between notifications
    
    return False  # Exit script after notifications

class AsyncLoopManager:
    def __init__(self):
        self.loop = None
        
    def start_loop(self):
        """Start a new event loop in the current thread"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
    def stop_loop(self):
        """Stop the event loop"""
        if self.loop:
            self.loop.stop()
            self.loop.close()
            
    def run_coroutine(self, coro):
        """Run a coroutine in the current loop"""
        if self.loop and self.loop.is_running():
            return asyncio.run_coroutine_threadsafe(coro, self.loop)
        elif self.loop:
            return self.loop.run_until_complete(coro)
        return None

class TelegramBot:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.connected = False
        self.backoff_time = TELEGRAM_CONFIG["initial_backoff"]
        self.retry_count = 0
        self.last_connection_attempt = None
        self.application = None
        
    async def start(self):
        """Start the Telegram bot with error handling and backoff"""
        try:
            # Build the application
            self.application = (
                Application.builder()
                .token(self.token)
                .read_timeout(30)
                .write_timeout(30)
                .build()
            )
            
            # Add command handlers
            # Add command handlers
            async def status_handler(update, context):
                print(f"[{get_timestamp()}] /status command received")
                status_message = generate_status_message()
                await update.message.reply_text(status_message, parse_mode='HTML')

            self.application.add_handler(CommandHandler("status", status_handler))
            print(f"[{get_timestamp()}] /status command handler registered")  # Corrected line
            
            # Start the application and polling
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(
                poll_interval=1.0,
                timeout=30,
                bootstrap_retries=-1,
                read_timeout=30,
                write_timeout=30
            )
            
            self.connected = True
            self.backoff_time = TELEGRAM_CONFIG["initial_backoff"]
            self.retry_count = 0
            print(f"[{get_timestamp()}] ✅ Telegram bot connected successfully")

        except Exception as e:
            self.connected = False
            print(f"[{get_timestamp()}] ❌ Telegram connection failed: {str(e)}")

    async def stop(self):
        """Stop the Telegram bot gracefully"""
        if self.application:
            try:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
            except Exception as e:
                print(f"[{get_timestamp()}] ⚠️ Error during Telegram shutdown: {str(e)}")
        self.connected = False
        print(f"[{get_timestamp()}] ✅ Telegram bot stopped successfully")

    async def send_message(self, message):
        """Send a message with error handling"""
        if not self.connected or not running:
            return
            
        try:
            if self.application:
                await self.application.bot.send_message(
                    chat_id=self.chat_id,
                    text=message,
                    parse_mode='HTML'
                )
        except Exception as e:
            print(f"[{get_timestamp()}] ❌ Failed to send Telegram message: {str(e)}")
            self.connected = False

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global running
    print(f"\n[{get_timestamp()}] 🛑 Received shutdown signal, cleaning up...")
    running = False
    
    if telegram_bot:
        loop_manager.run_coroutine(telegram_bot.stop())
    if loop_manager:
        loop_manager.stop_loop()
    
    print(f"[{get_timestamp()}] Goodbye!")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def get_timestamp():
    """Return current timestamp in a readable format"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def format_duration(duration):
    """Format a duration into a readable string"""
    hours = duration.seconds // 3600
    minutes = (duration.seconds % 3600) // 60
    return f"{hours} hours {minutes} minutes"

def generate_status_message():
    """Generate a status message for both console and Telegram"""
    runtime = datetime.now() - start_time
    
    status_check = "✅" if last_check_success else "❌"
    status_text = "Successful" if last_check_success else "Failed"
    
    if last_check_time:
        last_check_str = last_check_time.strftime("%H:%M:%S %d/%m/%Y")
    else:
        last_check_str = "No checks yet"

    return f"""📊 NVIDIA Stock Checker Status
⏱️ Running for: {format_duration(runtime)}
📈 Requests: {successful_requests:,} successful, {failed_requests:,} failed
{status_check} Last check: {last_check_str} ({status_text})
🎯 Monitoring: {'None' if not AVAILABLE_CARDS.keys() else ', '.join(AVAILABLE_CARDS.keys())}"""

async def send_startup_message():
    """Send a startup message via Telegram with monitoring details"""
    if not TELEGRAM_CONFIG["enabled"] or not telegram_bot or not telegram_bot.connected:
        return

    startup_message = f"""🚀 *NVIDIA Stock Checker Started Successfully!*
🎯 Monitoring: {'None' if not AVAILABLE_CARDS else ', '.join(AVAILABLE_CARDS.keys())}
⏱️ Check Interval: {params['check_interval']} seconds
🔔 Notifications: {'Enabled' if NOTIFICATION_CONFIG['play_sound'] else 'Disabled'}
🌐 Browser Opening: {'Enabled' if NOTIFICATION_CONFIG['open_browser'] else 'Disabled'}

📢 Type */status* to get the latest script statistics."""

    try:
        await telegram_bot.send_message(startup_message)
        print(f"[{get_timestamp()}] ✅ Startup message sent to Telegram")
    except Exception as e:
        print(f"[{get_timestamp()}] ❌ Failed to send startup message: {str(e)}")

def send_console_status():
    """Print a status update to the console"""
    global last_console_status_time
    if not running:
        return
    status_message = generate_status_message()
    print(f"\n[{get_timestamp()}] {status_message}\n")
    last_console_status_time = datetime.now()

def send_telegram_status():
    """Send a status update via Telegram"""
    global last_telegram_status_time
    if not running:
        return
    if not TELEGRAM_CONFIG["enabled"] or not telegram_bot or not telegram_bot.connected:
        return
    if not loop_manager:
        print(f"[{get_timestamp()}] ⚠️ Cannot send Telegram status: Loop manager not initialized")
        return

    try:
        status_message = generate_status_message()
        loop_manager.run_coroutine(telegram_bot.send_message(status_message))
    except Exception as e:
        print(f"[{get_timestamp()}] ❌ Failed to send Telegram status: {str(e)}")
    finally:
        last_telegram_status_time = datetime.now()

def play_notification_sound():
    """Play notification sound using the appropriate method for the OS"""
    system = platform.system()
    
    if system == 'Windows':
        try:
            winsound.MessageBeep()  # Built-in Windows alert sound
        except Exception as e:
            print(f"[{get_timestamp()}] ⚠️ Failed to play Windows sound: {e}")
    
    elif system == 'Darwin':  # macOS
        try:
            subprocess.run(['afplay', '/System/Library/Sounds/Ping.aiff'], check=True)
        except subprocess.SubprocessError as e:
            print(f"[{get_timestamp()}] ⚠️ Failed to play macOS sound: {e}")
    
    else:  # Linux or other systems
        print(f"[{get_timestamp()}] ℹ️ Sound not supported on this operating system")

def dispatch_stock_notifications(sku, price, product_url, in_stock):
    """Send out stock notifications according to the config"""
    if not running:
        return
    
    if in_stock:
        if NOTIFICATION_CONFIG["open_browser"]:
            open_browser()
        if NOTIFICATION_CONFIG["play_sound"]:
            play_notification_sound()

    if TELEGRAM_CONFIG["enabled"]:
        send_telegram_notification(sku, price, product_url, in_stock)
    if NTFY_CONFIG["enabled"]:
        send_ntfy_notification(sku, price, product_url, in_stock)

def send_telegram_notification(sku, price, product_url, in_stock):
    """Send stock notification via Telegram"""
    if not telegram_bot or not telegram_bot.connected:
        return
    if not loop_manager:
        print(f"[{get_timestamp()}] ⚠️ Cannot send Telegram notification: Loop manager not initialized")
        return

    status = "✅ IN STOCK" if in_stock else "❌ OUT OF STOCK"
    message = f"""🔔 NVIDIA Stock Alert
{status}: {sku}
💰 Price: {currency}{price}
🔗 Link: {product_url}"""

    try:
        loop_manager.run_coroutine(telegram_bot.send_message(message))
    except Exception as e:
        print(f"[{get_timestamp()}] ❌ Failed to send Telegram notification: {str(e)}")

def send_ntfy_notification(sku, price, product_url, in_stock):
    status = "✅ IN STOCK" if in_stock else "❌ OUT OF STOCK"
    actions = [{"action": "view", "label": "Add to cart", "url": product_url}] if in_stock else []
    headers = {"Authorization": f"Bearer {NTFY_CONFIG["access_token"]}"} if NTFY_CONFIG["access_token"] else None
    try:
        response = requests.post(f"{NTFY_CONFIG['url']}",
            headers=headers,
            data=json.dumps({
                "topic": NTFY_CONFIG["topic"],
                "message": f"💰 Price: {currency}{price}",
                "Priority": 5 if in_stock else 3,
                "title": f"{status}: {sku}",
                "actions": actions
            })
        )
        response.raise_for_status()

    except Exception as e:
        print(f"[{get_timestamp()}] ❌ Failed to send NTFY notification: {str(e)}")

def open_browser(product_url):
    """Open web browser to the product url """
    if not running:
        return
    try:
        webbrowser.open(product_url)
    except Exception as e:
        print(f"[{get_timestamp()}] ⚠️ Failed to open browser: {e}")

def get_skus_if_needed(selected_cards, force_check=False, telegram_bot=None, loop_manager=None):
    """
    Get SKUs based on selected cards, but only if the cache has expired or force_check is True.
    Handles mismatches between API products and configured products.
    """
    global last_sku_check_time, cached_skus, sku_to_name_map
    
    current_time = datetime.now()
    
    # Check if we need to update SKUs
    needs_update = (
        force_check or
        last_sku_check_time is None or
        (current_time - last_sku_check_time).seconds >= SKU_CHECK_CONFIG["interval"]
    )
    
    if needs_update:
        try:
            if force_check:
                print(f"[{get_timestamp()}] 🚀 Performing initial SKU check...")
            else:
                print(f"[{get_timestamp()}] ℹ️ Updating SKU cache...")
                
            # Get SKUs and their associated product names
            sku_check_params = {
                "locale": API_CONFIG["params"]["locale"],
                "page": 1,
                "limit": 12,
                "manufacturer": "NVIDIA",
            }
            response = requests.get(SKU_CHECK_API_CONFIG["url"], params=sku_check_params, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # First, collect all products from API
            all_products = {}
            sku_to_name_map = {}  # New mapping
            if "searchedProducts" in data and isinstance(data["searchedProducts"]["productDetails"], list):
                for product in data["searchedProducts"]["productDetails"]:
                    if "productSKU" in product and "displayName" in product:
                        sku = product["productSKU"]
                        name = product["displayName"]
                        all_products[sku] = name
                        sku_to_name_map[sku] = name  # Store the mapping

            # Log all products found from API
            all_products_details = ", ".join([f"{name} ({sku})" for sku, name in all_products.items()])
            print(f"[{get_timestamp()}] 📋 Current SKU's listed on API: {all_products_details}")

            # Check for mismatches between API products and configured products
            if not handle_product_mismatch(all_products, selected_cards, telegram_bot, loop_manager):
                print(f"[{get_timestamp()}] 🛑 Exiting due to product mismatch")
                global running
                running = False
                sys.exit(1)

            # Then filter for enabled products
            enabled_skus = []
            for sku, name in all_products.items():
                matching_card = next((card for card in PRODUCT_CONFIG_CARDS.keys() 
                                   if card.lower() in name.lower() 
                                   and PRODUCT_CONFIG_CARDS[card]["enabled"]), None)
                if matching_card and matching_card in selected_cards:
                    enabled_skus.append(sku)

            cached_skus = enabled_skus
            last_sku_check_time = current_time
            
            if force_check:
                print(f"[{get_timestamp()}] ✅ Initial SKU check complete")
            else:
                print(f"[{get_timestamp()}] ✅ SKU cache updated successfully")
        except Exception as e:
            print(f"[{get_timestamp()}] ❌ Failed to update SKU cache: {str(e)}")
            # If we've never successfully gotten SKUs, raise the error
            if not cached_skus:
                raise
    
    return cached_skus

def check_nvidia_stock(skus):
    """Check stock for each SKU individually"""
    global last_stock_status, successful_requests, failed_requests, last_check_time, last_check_success
    
    if not running:
        return
        
    current_time = datetime.now()
    
    # Check if it's time for console status update
    if STATUS_UPDATES["console"]["enabled"] and \
       (current_time - last_console_status_time).seconds >= STATUS_UPDATES["console"]["interval"]:
        send_console_status()
    
    # Check if it's time for Telegram status update
    if STATUS_UPDATES["telegram"]["enabled"] and \
       (current_time - last_telegram_status_time).seconds >= STATUS_UPDATES["telegram"]["interval"]:
        send_telegram_status()
    
    for sku in skus:
        if not running:
            return
            
        try:
            product_name = sku_to_name_map.get(sku, "Unknown Product")
            if NOTIFICATION_CONFIG["log_stock_checks"]:
                print(f"[{get_timestamp()}] ℹ️ Checking stock for {product_name} ({sku})...")
            
            # Query one SKU at a time
            current_params = {**params, "skus": sku}
            
            response = requests.get(API_URL, params=current_params, headers=headers)
            response.raise_for_status()
            data = response.json()
            successful_requests += 1
            last_check_success = True
            last_check_time = datetime.now()

            if "listMap" in data and isinstance(data["listMap"], list):
                # Process response for this SKU
                if data["listMap"]:  # If we got data back
                    item = data["listMap"][0]  # Should only be one item
                    api_sku = item.get("fe_sku", "Unknown SKU")
                    is_active = item.get("is_active", "false") == "true"
                    price = item.get("price", "Unknown Price")
                    product_url = item.get("product_url") or NVIDIA_BASE_URL

                    if NOTIFICATION_CONFIG["log_stock_checks"]:
                        print(f"[{get_timestamp()}] {'✅' if is_active else '❌'} ({sku}) is currently {'in stock' if is_active else 'out of stock'}")
                    
                    # Check if stock status has changed
                    if api_sku not in last_stock_status or last_stock_status[api_sku] != is_active or product_url != NVIDIA_BASE_URL:
                        last_stock_status[api_sku] = is_active
                        timestamp = get_timestamp()
                        dispatch_stock_notifications(sku, price, product_url, is_active)
                        if NOTIFICATION_CONFIG["log_stock_checks"]:
                            if is_active:
                                print(f"[{timestamp}] ✅ IN STOCK: {sku} - {currency}{price}")
                                print(f"[{timestamp}] 🔗 NVIDIA Link: {product_url}")
                            else:
                                print(f"[{timestamp}] ❌ OUT OF STOCK: {sku} - {currency}{price}")
                        if is_active:
                            time.sleep(params['cooldown'])
                else:
                    # Empty listMap means product not in system
                    if NOTIFICATION_CONFIG["log_stock_checks"]:
                        print(f"[{get_timestamp()}] ℹ️ ({sku}) is not currently in the system")
            
            # Small delay between requests to be nice to the API
            if running:
                time.sleep(1)

        except requests.exceptions.RequestException as e:
            failed_requests += 1
            last_check_success = False
            last_check_time = datetime.now()
            print(f"[{get_timestamp()}] ❌ API request failed for {sku}: {e}")

def run_test(selected_cards):
    """Run a test of the notification system then transition to normal monitoring"""
    system = platform.system()
    print(f"[{get_timestamp()}] 🧪 Running test mode...")
    print(f"[{get_timestamp()}] Operating System: {system}")
    print(f"[{get_timestamp()}] Monitoring Cards: {'None' if not selected_cards else ', '.join(selected_cards)}")
    
    test_url = NVIDIA_BASE_URL
    print(f"[{get_timestamp()}] Testing stock notification...")
    open_browser(test_url)
    play_notification_sound()
    print(f"[{get_timestamp()}] ✅ Test completed. Browser should have opened and sound should have played.")
    
    if TELEGRAM_CONFIG["enabled"] and telegram_bot and telegram_bot.connected:
        print(f"[{get_timestamp()}] Testing Telegram notification...")
        send_telegram_notification("TEST", "9.99", test_url, True)
        print(f"[{get_timestamp()}] Telegram test message sent.")

    if NTFY_CONFIG["enabled"]:
        print(f"[{get_timestamp()}] Testing NTFY notification...")
        send_ntfy_notification("TEST", "9.99", test_url, True)
        print(f"[{get_timestamp()}] NTFY test message sent.")
    
    print(f"[{get_timestamp()}] ⏳ Testing cooldown: waiting {params['cooldown']} seconds...")
    time.sleep(params['cooldown'])
    print(f"[{get_timestamp()}] Cooldown period complete.")
    
    print(f"[{get_timestamp()}] Transitioning to normal monitoring mode...")
    
    # Do initial SKU check
    try:
        skus = get_skus_if_needed(selected_cards, force_check=True, telegram_bot=telegram_bot, loop_manager=loop_manager)
        while running:
            try:
                skus = get_skus_if_needed(selected_cards, telegram_bot=telegram_bot, loop_manager=loop_manager)
                check_nvidia_stock(skus)
                if running:
                    time.sleep(params['check_interval'])
            except Exception as e:
                print(f"[{get_timestamp()}] ❌ Error during monitoring: {str(e)}")
                print(traceback.format_exc())
                if running:
                    time.sleep(params['check_interval'])
    except Exception as e:
        print(f"[{get_timestamp()}] ❌ Initial SKU check failed: {str(e)}")
        print(traceback.format_exc())

def list_available_cards():
    """Print all available cards and their descriptions"""
    print("\nProduct Configuration:")
    for card, config in PRODUCT_CONFIG_CARDS.items():
        status = "✅ Enabled" if config["enabled"] else "❌ Disabled"
        print(f"  {card} - {status}")
    print("\nCurrently monitoring:")
    for card in AVAILABLE_CARDS.keys():
        print(f"  {card}")

def main():
    global running, telegram_bot, loop_manager
    running = True
    try:
        # Check if no cards are being monitored
        if not AVAILABLE_CARDS:
            print("NO CARDS HAVE BEEN SETUP FOR MONITORING. RUN 'stockconfig.py' TO SET THE CARDS YOU WANT TO MONITOR")
            sys.exit(1)

        # Initialize loop manager if Telegram is enabled
        if TELEGRAM_CONFIG["enabled"]:
            if TELEGRAM_CONFIG["bot_token"] and TELEGRAM_CONFIG["chat_id"]:
                try:
                    global loop_manager, telegram_bot
                    # Create and start the async loop manager
                    loop_manager = AsyncLoopManager()
                    loop_manager.start_loop()
                    
                    # Initialize and start the bot
                    telegram_bot = TelegramBot(TELEGRAM_CONFIG["bot_token"], TELEGRAM_CONFIG["chat_id"])
                    
                    # Start the bot and wait for it to connect
                    loop_manager.run_coroutine(telegram_bot.start())
                    
                    # Give the bot a moment to initialize
                    time.sleep(2)
                    
                    if not telegram_bot.connected:
                        print(f"[{get_timestamp()}] ⚠️ Telegram bot failed to connect")
                        TELEGRAM_CONFIG["enabled"] = False
                        telegram_bot = None
                        loop_manager.stop_loop()
                        loop_manager = None
                    else:
                        # Send the startup message after successful connection
                        loop_manager.run_coroutine(send_startup_message())
                        
                        # Start a background task to keep the event loop running
                        def run_event_loop():
                            loop_manager.loop.run_forever()
                        
                        loop_thread = threading.Thread(target=run_event_loop, daemon=True)
                        loop_thread.start()
                        
                except Exception as e:
                    print(f"[{get_timestamp()}] ❌ Failed to initialize Telegram bot: {str(e)}")
                    TELEGRAM_CONFIG["enabled"] = False
                    telegram_bot = None
                    if loop_manager:
                        loop_manager.stop_loop()
                    loop_manager = None
            else:
                print(f"[{get_timestamp()}] ℹ️ Telegram disabled: missing credentials")
                TELEGRAM_CONFIG["enabled"] = False

        if args.test:
            run_test(selected_cards)
        else:
            system = platform.system()
            print(f"[{get_timestamp()}] Stock checker started. Monitoring for changes...")
            print(f"[{get_timestamp()}] Monitored Country: {country}")
            print(f"[{get_timestamp()}] Monitoring Cards: {'None' if not selected_cards else ', '.join(selected_cards)}")
            print(f"[{get_timestamp()}] Check Interval: {params['check_interval']} seconds")
            print(f"[{get_timestamp()}] Cooldown Period: {params['cooldown']} seconds")
            print(f"[{get_timestamp()}] SKU Check Interval: {SKU_CHECK_CONFIG['interval']} seconds")
            
            if STATUS_UPDATES["console"]["enabled"]:
                print(f"[{get_timestamp()}] Script Health Update (to Console): Every {STATUS_UPDATES['console']['interval']} seconds")
            else:
                print(f"[{get_timestamp()}] Script Health Update (to Console): Disabled")
                
            if STATUS_UPDATES["telegram"]["enabled"] and TELEGRAM_CONFIG["enabled"]:
                print(f"[{get_timestamp()}] Script Check Health Update (to Telegram): Every {STATUS_UPDATES['telegram']['interval']} seconds")
            else:
                print(f"[{get_timestamp()}] Script Check Health Update (to Telegram): Disabled")
                
            print(f"[{get_timestamp()}] Sound Notifications: {'Enabled' if NOTIFICATION_CONFIG['play_sound'] else 'Disabled'}")
            print(f"[{get_timestamp()}] Browser Opening: {'Enabled' if NOTIFICATION_CONFIG['open_browser'] else 'Disabled'}")
            print(f"[{get_timestamp()}] Tip: Run with --test to test notifications")
            print(f"[{get_timestamp()}] Tip: Run with --list-cards to see all available cards")
            
            # Do initial SKU check
            try:
                skus = get_skus_if_needed(selected_cards, force_check=True, telegram_bot=telegram_bot, loop_manager=loop_manager)
            except Exception as e:
                print(f"[{get_timestamp()}] ❌ Initial SKU check failed: {str(e)}")
                return
                
            while running:
                try:
                    skus = get_skus_if_needed(selected_cards, telegram_bot=telegram_bot, loop_manager=loop_manager)
                    check_nvidia_stock(skus)
                    if running:
                        time.sleep(params['check_interval'])
                except Exception as e:
                    print(f"[{get_timestamp()}] ❌ Error during monitoring: {str(e)}")
                    print(traceback.format_exc())
                    if running:
                        time.sleep(params['check_interval'])
                        
    except Exception as e:
        print(f"[{get_timestamp()}] ❌ Fatal error: {str(e)}")
    finally:
        # Ensure clean shutdown
        running = False
        if telegram_bot and loop_manager:
            loop_manager.run_coroutine(telegram_bot.stop())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='NVIDIA Stock Checker')
    parser.add_argument('--test', action='store_true', 
                      help='Run in test mode to check notification system')
    parser.add_argument('--list-cards', action='store_true',
                      help='List all available cards and exit')
    parser.add_argument('--cooldown', type=int, default=params['cooldown'],
                      help=f'Cooldown period in seconds after finding stock (default: {params["cooldown"]})')
    parser.add_argument('--check-interval', type=int, default=params['check_interval'],
                      help=f'Time between checks in seconds (default: {params["check_interval"]})')
    parser.add_argument('--console-status', action='store_true',
                      help='Enable console script health updates')
    parser.add_argument('--no-console-status', action='store_true',
                      help='Disable console script health updates')
    parser.add_argument('--console-interval', type=int,
                      help='Time between console script health updates in seconds')
    parser.add_argument('--telegram-status', action='store_true',
                      help='Enable Telegram script health updates')
    parser.add_argument('--no-telegram-status', action='store_true',
                      help='Disable Telegram script health updates')
    parser.add_argument('--telegram-interval', type=int,
                      help='Time between Telegram script health updates in seconds')
    parser.add_argument('--telegram-token', type=str,
                      help='Telegram bot token')
    parser.add_argument('--telegram-chat-id', type=str,
                      help='Telegram chat ID')
    parser.add_argument('--telegram-polling-timeout', type=int,
                      help='Telegram polling timeout in seconds')
    parser.add_argument('--no-sound', action='store_true',
                      help='Disable notification sounds')
    parser.add_argument('--no-browser', action='store_true',
                      help='Disable automatic browser opening')
    parser.add_argument('--sku-check-interval', type=int,
                      help='Time between SKU checks in seconds')
    parser.add_argument('--log-stock-checks', action='store_true',
                  help='Enable logging of stock checks to the console')
    
    args = parser.parse_args()
    
    if args.list_cards:
        list_available_cards()
        exit(0)

    selected_cards = list(AVAILABLE_CARDS.keys())
    
    # Override params with command line arguments if provided
    params['cooldown'] = args.cooldown
    params['check_interval'] = args.check_interval
    
    # Process status update settings
    if args.console_status:
        STATUS_UPDATES["console"]["enabled"] = True
    if args.no_console_status:
        STATUS_UPDATES["console"]["enabled"] = False
    if args.console_interval:
        STATUS_UPDATES["console"]["interval"] = args.console_interval

    if args.telegram_status:
        STATUS_UPDATES["telegram"]["enabled"] = True
    if args.no_telegram_status:
        STATUS_UPDATES["telegram"]["enabled"] = False
    if args.telegram_interval:
        STATUS_UPDATES["telegram"]["interval"] = args.telegram_interval
        
    # Process SKU check interval if provided
    if args.sku_check_interval:
        SKU_CHECK_CONFIG["interval"] = args.sku_check_interval
    
    # Process notification configuration
    if args.no_sound:
        NOTIFICATION_CONFIG["play_sound"] = False
    if args.no_browser:
        NOTIFICATION_CONFIG["open_browser"] = False
    
    # Process Telegram arguments
    if args.telegram_token:
        TELEGRAM_CONFIG["bot_token"] = args.telegram_token
        TELEGRAM_CONFIG["enabled"] = True
    if args.telegram_chat_id:
        TELEGRAM_CONFIG["chat_id"] = args.telegram_chat_id
    if args.telegram_polling_timeout:
        TELEGRAM_CONFIG["polling_timeout"] = args.telegram_polling_timeout

    # Process check logging argument
    if args.log_stock_checks:
        NOTIFICATION_CONFIG["log_stock_checks"] = True
        
    main()
