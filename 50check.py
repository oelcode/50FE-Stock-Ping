import requests
import time
import webbrowser
import argparse
import asyncio
from datetime import datetime
import signal
import sys
import traceback
from typing import Dict, List

# Import configuration
try:
    from config import (
        NOTIFICATION_CONFIG,
        PRODUCT_CONFIG_CARDS,
        API_CONFIG,
        SKU_CHECK_API_CONFIG,
        LOCALE_CONFIG,
        SKU_CHECK_CONFIG,
        STATUS_UPDATES,
    )
except ModuleNotFoundError:
    print("config.py DOES NOT EXIST. Rename example_config.py to config.py to begin.")
    sys.exit(1)


# Import notification system
from handlers import NotificationManager

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
    global last_check_time, last_check_success, notification_manager
    global last_sku_check_time, cached_skus, sku_to_name_map, running
    global last_status_update
    
    last_stock_status = {}
    start_time = datetime.now()
    last_status_update = start_time
    successful_requests = 0
    failed_requests = 0
    last_check_time = None
    last_check_success = True
    notification_manager = None
    last_sku_check_time = None
    cached_skus = []
    sku_to_name_map = {}
    running = True

# Initialize globals
init_globals()

def get_timestamp():
    """Return current timestamp in a readable format"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def generate_status_data():
    """Generate raw status data dictionary"""
    runtime = datetime.now() - start_time
    time_since_check = datetime.now() - last_check_time if last_check_time else None
    
    return {
        'runtime': runtime,
        'successful_requests': successful_requests,
        'failed_requests': failed_requests,
        'last_check_time': last_check_time,
        'last_check_success': last_check_success,
        'monitored_cards': list(AVAILABLE_CARDS.keys()),
        'time_since_check': time_since_check
    }

def format_duration(duration):
    """Format a duration into a readable string"""
    hours = duration.seconds // 3600
    minutes = (duration.seconds % 3600) // 60
    return f"{hours} hours {minutes} minutes"

def handle_product_mismatch(api_products: Dict, configured_products: List[str]) -> bool:
    """
    Handle mismatch between API products and configured products.
    Returns False if there's a critical mismatch, True otherwise.
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
    while remaining_attempts > 0 and running:
        timestamp = get_timestamp()
        print(f"\n[{timestamp}] {mismatch_message}")
        print(f"[{timestamp}] ⚠️ {remaining_attempts} warning{'s' if remaining_attempts > 1 else ''} remaining before exit")
        
        remaining_attempts -= 1
        if remaining_attempts > 0 and running:
            time.sleep(300)  # Wait 5 minutes between notifications
    
    return False  # Exit script after notifications

async def setup_notifications():
    """Initialize the notification system"""
    global notification_manager
    notification_manager = NotificationManager.load_handlers()
    await notification_manager.initialize_handlers()
    
    # Send startup message
    startup_message = f"""🚀 NVIDIA Stock Checker Started Successfully!
🎯 Monitoring: {'None' if not AVAILABLE_CARDS else ', '.join(AVAILABLE_CARDS.keys())}
🌍 Country: {country}
⏱️ Check Interval: {params['check_interval']} seconds
⚡ Browser Auto-Open: {'Enabled' if NOTIFICATION_CONFIG['open_browser'] else 'Disabled'}
🔄 API SKU Refresh Interval: {SKU_CHECK_CONFIG['interval']} seconds"""
    
    await notification_manager.send_startup_message(startup_message)

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global running
    print(f"\n[{get_timestamp()}] 🛑 Received shutdown signal, cleaning up...")
    running = False
    
    if notification_manager:
        asyncio.run(notification_manager.shutdown_handlers())
    
    print(f"[{get_timestamp()}] Goodbye!")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def get_skus_if_needed(selected_cards: List[str], force_check: bool = False) -> List[str]:
    """
    Get SKUs based on selected cards, but only if the cache has expired or force_check is True.
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
            if "searchedProducts" in data and isinstance(data["searchedProducts"]["productDetails"], list):
                for product in data["searchedProducts"]["productDetails"]:
                    if "productSKU" in product and "displayName" in product:
                        sku = product["productSKU"]
                        name = product["displayName"]
                        all_products[sku] = name
                        sku_to_name_map[sku] = name

            # Log all products found from API
            all_products_details = ", ".join([f"{name} ({sku})" for sku, name in all_products.items()])
            print(f"[{get_timestamp()}] 📋 Current SKU's listed on API: {all_products_details}")

            # Check for mismatches between API products and configured products
            if not handle_product_mismatch(all_products, selected_cards):
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

async def check_nvidia_stock(skus: List[str]):
    """Check stock for each SKU individually"""
    global last_stock_status, successful_requests, failed_requests, last_check_time, last_check_success, last_status_update
    
    if not running:
        return
        
    current_time = datetime.now()
    
    # Only send status update if we've done at least one check and 15 minutes have passed
    if last_check_time and (current_time - last_status_update).seconds >= STATUS_UPDATES["interval"]:
        last_status_update = current_time
        await notification_manager.send_status_update(generate_status_data())
    
    for sku in skus:
        if not running:
            return
            
        try:
            product_name = sku_to_name_map.get(sku, "Unknown Product")
            print(f"[{get_timestamp()}] ℹ️ Checking stock for {product_name} ({sku})...")
            
            # Record start time of request
            request_start_time = time.time()
            
            # Query one SKU at a time
            current_params = {**params, "skus": sku}
            
            response = requests.get(API_URL, params=current_params, headers=headers)
            response.raise_for_status()
            data = response.json()
            successful_requests += 1
            last_check_success = True
            last_check_time = datetime.now()

            if "listMap" in data and isinstance(data["listMap"], list):
                if data["listMap"]:  # If we got data back
                    item = data["listMap"][0]  # Should only be one item
                    api_sku = item.get("fe_sku", "Unknown SKU")
                    is_active = item.get("is_active", "false") == "true"
                    price = item.get("price", "Unknown Price")
                    product_url = item.get("product_url") or NVIDIA_BASE_URL

                    # Check if stock status has changed
                    if api_sku not in last_stock_status or last_stock_status[api_sku] != is_active:
                        last_stock_status[api_sku] = is_active

                        # Send notification
                        await notification_manager.send_stock_alert(sku, price, product_url, is_active)

                        # Open browser if configured and item is in stock
                        if is_active and NOTIFICATION_CONFIG["open_browser"]:
                            try:
                                webbrowser.open(product_url)
                            except Exception as e:
                                print(f"[{get_timestamp()}] ⚠️ Failed to open browser: {e}")

                        if is_active:
                            time.sleep(params['cooldown'])
                else:
                    print(f"[{get_timestamp()}] ℹ️ ({sku}) is not currently in the system")
            
            # Small delay between requests, accounting for request time
            if running:
                request_duration = time.time() - request_start_time
                sleep_time = max(0, 1.0 - request_duration)  # Maintain 1 second between requests
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except requests.exceptions.RequestException as e:
            failed_requests += 1
            last_check_success = False
            last_check_time = datetime.now()
            print(f"[{get_timestamp()}] ❌ API request failed for {sku}: {e}")

async def main():
    try:
        # Check if no cards are being monitored
        if not AVAILABLE_CARDS:
            print("NO CARDS HAVE BEEN SETUP FOR MONITORING. RUN 'stockconfig.py' TO SET THE CARDS YOU WANT TO MONITOR")
            sys.exit(1)

        # Initialize notification system
        await setup_notifications()

        if args.test:
            print(f"[{get_timestamp()}] 🧪 Running test mode...")
            test_url = NVIDIA_BASE_URL
            await notification_manager.send_stock_alert("TEST-SKU", "9.99", test_url, True)
            if NOTIFICATION_CONFIG["open_browser"]:
                webbrowser.open(test_url)
            print(f"[{get_timestamp()}] ✅ Test completed.")
            return

        # Print startup information
        print(f"[{get_timestamp()}] Stock checker started. Monitoring for changes...")
        print(f"[{get_timestamp()}] Monitored Country: {country}")
        print(f"[{get_timestamp()}] Monitoring Cards: {'None' if not selected_cards else ', '.join(selected_cards)}")
        print(f"[{get_timestamp()}] Check Interval: {params['check_interval']} seconds")
        print(f"[{get_timestamp()}] Cooldown Period: {params['cooldown']} seconds")
        print(f"[{get_timestamp()}] SKU Check Interval: {SKU_CHECK_CONFIG['interval']} seconds")
        print(f"[{get_timestamp()}] Browser Opening: {'Enabled' if NOTIFICATION_CONFIG['open_browser'] else 'Disabled'}")
        print(f"[{get_timestamp()}] Tip: Run with --test to test notifications")
        print(f"[{get_timestamp()}] Tip: Run with --list-cards to see all available cards")
        
        # Main monitoring loop
        try:
            skus = get_skus_if_needed(selected_cards, force_check=True)
            while running:
                try:
                    # Record start time of check
                    check_start_time = time.time()
                    
                    # Do the check
                    skus = get_skus_if_needed(selected_cards)
                    await check_nvidia_stock(skus)
                    
                    if running:
                        # Calculate how long the check took
                        check_duration = time.time() - check_start_time
                        
                        # Calculate remaining time to sleep
                        sleep_time = max(0, params['check_interval'] - check_duration)
                        if sleep_time > 0:
                            time.sleep(sleep_time)
                except Exception as e:
                    print(f"[{get_timestamp()}] ❌ Error during monitoring: {str(e)}")
                    print(traceback.format_exc())
                    if running:
                        time.sleep(params['check_interval'])
        except Exception as e:
            print(f"[{get_timestamp()}] ❌ Initial SKU check failed: {str(e)}")
            print(traceback.format_exc())
                        
    except Exception as e:
        print(f"[{get_timestamp()}] ❌ Fatal error: {str(e)}")
        print(traceback.format_exc())
    finally:
        # Ensure clean shutdown
        if notification_manager:
            await notification_manager.shutdown_handlers()

def list_available_cards():
    """Print all available cards and their descriptions"""
    print("\nProduct Configuration:")
    for card, config in PRODUCT_CONFIG_CARDS.items():
        status = "✅ Enabled" if config["enabled"] else "❌ Disabled"
        print(f"  {card} - {status}")
    print("\nCurrently monitoring:")
    for card in AVAILABLE_CARDS.keys():
        print(f"  {card}")

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
    parser.add_argument('--sku-check-interval', type=int,
                      help='Time between SKU checks in seconds')
    parser.add_argument('--no-browser', action='store_true',
                      help='Disable automatic browser opening')
    
    args = parser.parse_args()
    
    if args.list_cards:
        list_available_cards()
        exit(0)

    selected_cards = list(AVAILABLE_CARDS.keys())
    
    # Override params with command line arguments if provided
    params['cooldown'] = args.cooldown
    params['check_interval'] = args.check_interval
    
    # Process SKU check interval if provided
    if args.sku_check_interval:
        SKU_CHECK_CONFIG["interval"] = args.sku_check_interval
    
    # Process browser configuration
    if args.no_browser:
        NOTIFICATION_CONFIG["open_browser"] = False
    
    # Run the main async loop
    asyncio.run(main())
