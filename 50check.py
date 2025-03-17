import requests
import time
import webbrowser
import argparse
import asyncio
from datetime import datetime
import signal
import sys
import traceback
import json
import os
from typing import Dict, List

# Load product configuration from products.json
def load_product_config():
    try:
        with open('products.json', 'r') as f:
            config_data = json.load(f)
        return config_data
    except FileNotFoundError:
        print("products.json DOES NOT EXIST. Please run stockconfig.py.")
        sys.exit(1)
    except json.JSONDecodeError:
        print("products.json contains invalid JSON. Please delete the file and re-run stockconfig.py.")
        sys.exit(1)

# Load JSON configuration
product_json_config = load_product_config()

# Get locale configuration from JSON
LOCALE_CONFIG = product_json_config["locale_config"]

# Get product configuration from JSON
PRODUCT_CONFIG_CARDS = product_json_config["product_config_cards"]

# Import remaining configuration from config.py
try:
    from config import (
        NOTIFICATION_CONFIG,
        API_CONFIG,
        SKU_CHECK_API_CONFIG,
        SKU_CHECK_CONFIG,
        STATUS_UPDATES,
        CONSOLE_CONFIG,
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
🌍 Country: {country} ({currency})
⏱️ Check Interval: {params['check_interval']} seconds
⚡ Browser Auto-Open: {'Enabled' if NOTIFICATION_CONFIG['open_browser'] else 'Disabled'}
🔄 API SKU Refresh Interval: {SKU_CHECK_CONFIG['interval']} seconds"""
    
    await notification_manager.send_startup_message(startup_message)

async def shutdown(sig: signal.Signals, loop: asyncio.AbstractEventLoop):
    """Handle shutdown signals gracefully"""
    global running
    print(f"\n[{get_timestamp()}] 🛑 Received {sig.name}, cleaning up...")
    running = False
    
    if notification_manager:
        await notification_manager.shutdown_handlers()

    tasks = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task()]
    if tasks:
        for task in tasks:
            task.cancel()

    print(f"[{get_timestamp()}] ✅ Cancelled all tasks")

async def get_skus_if_needed(selected_cards: List[str], force_check: bool = False) -> List[str]:
    """
    Get SKUs based on selected cards and validate them against the API.
    Enhanced to detect both name changes (same SKU) and SKU changes (same name).
    Returns a list of valid SKUs.
    """
    global last_sku_check_time, cached_skus, sku_to_name_map, running
    
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
            
            # Get configured SKUs and names from products.json
            configured_skus = {}
            configured_names_to_skus = {}
            for card, config in PRODUCT_CONFIG_CARDS.items():
                if config["enabled"] and card in selected_cards and "sku" in config:
                    sku = config["sku"]
                    configured_skus[sku] = card
                    configured_names_to_skus[card] = sku
            
            # Always fetch products from API for validation
            sku_check_params = {
                "locale": API_CONFIG["params"]["locale"],
                "page": 1,
                "limit": 12,
                "manufacturer": "NVIDIA",
            }
            response = requests.get(SKU_CHECK_API_CONFIG["url"], params=sku_check_params, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # Collect all products from API
            api_products = {}  # SKU -> Name mapping
            api_names_to_skus = {}  # Name -> SKU mapping (for detecting SKU changes)
            
            if "searchedProducts" in data and isinstance(data["searchedProducts"]["productDetails"], list):
                for product in data["searchedProducts"]["productDetails"]:
                    if "productSKU" in product and "displayName" in product:
                        sku = product["productSKU"]
                        name = product["displayName"]
                        api_products[sku] = name
                        api_names_to_skus[name] = sku
            
            # Log all products found from API
            all_products_details = ", ".join([f"{name} ({sku})" for sku, name in api_products.items()])
            print(f"[{get_timestamp()}] 📋 Current SKU's listed on API: {all_products_details}")
            
            # Validate configured SKUs against API
            missing_skus = {}
            valid_skus = []
            name_changes = []
            sku_changes = []
            
            # SCENARIO 1: Check for products with the same SKU but different names
            for sku, local_name in configured_skus.items():
                if sku in api_products:
                    # SKU exists in API
                    valid_skus.append(sku)
                    api_name = api_products[sku]
                    
                    # Update SKU to name mapping
                    sku_to_name_map[sku] = api_name
                    
                    # Check if product name has changed
                    if local_name != api_name:
                        name_changes.append((local_name, api_name, sku))
                else:
                    # SKU doesn't exist in API
                    missing_skus[sku] = local_name
            
            # SCENARIO 2: Check for products with the exact same name but different SKUs
            for local_name, original_sku in configured_names_to_skus.items():
                # Only check products that weren't found by SKU
                if original_sku in valid_skus:
                    continue
                    
                # Check if the exact name exists in the API
                if local_name in api_names_to_skus:
                    # Found exact name match with different SKU
                    new_sku = api_names_to_skus[local_name]
                    valid_skus.append(new_sku)
                    sku_to_name_map[new_sku] = local_name
                    sku_changes.append((original_sku, new_sku, local_name))
                    
                    # Remove this SKU from missing SKUs since we found a replacement
                    if original_sku in missing_skus:
                        del missing_skus[original_sku]
            
            # Send notifications for any updates made
            update_notifications = []
            
            # Log any name changes
            if name_changes:
                for old_name, new_name, sku in name_changes:
                    change_message = f"Product name changed: '{old_name}' → '{new_name}' (SKU: {sku})"
                    print(f"[{get_timestamp()}] ℹ️ {change_message}")
                    update_notifications.append(change_message)
            
            # Log any SKU changes
            if sku_changes:
                for old_sku, new_sku, product_name in sku_changes:
                    change_message = f"Product SKU changed: '{old_sku}' → '{new_sku}' (Product: {product_name})"
                    print(f"[{get_timestamp()}] ℹ️ {change_message}")
                    update_notifications.append(change_message)
            
            # Send notification if any updates were made
            if update_notifications and notification_manager:
                config_message = """
🔄 Product Configuration Auto-Updated!

The script detected changes in NVIDIA's product information and has automatically updated its tracking.
Please review your configuration file (products.json) at your earliest convenience to ensure it reflects your desired tracking.

Changes detected:
"""
                for update in update_notifications:
                    config_message += f"- {update}\n"
                
                config_message += "\nThese changes are currently only applied to the script's internal tracking and have NOT been written to your configuration file."
                
                # Send the notification
                await notification_manager.send_startup_message(config_message)            
            # Handle missing SKUs
            # Handle missing SKUs
            if missing_skus:
                # Format message
                missing_products_list = ", ".join([f"{name} ({sku})" for sku, name in missing_skus.items()])
                
                # Create notification message
                mismatch_message = "⚠️ CRITICAL: Product Mismatch Detected!\n\n"
                
                # List products that couldn't be found
                mismatch_message += f"The following configured products could not be found in the NVIDIA API:\n"
                for sku, name in missing_skus.items():
                    mismatch_message += f"- {name} ({sku})\n"
                
                # List products that will continue to be monitored (if any)
                if valid_skus:
                    mismatch_message += f"\nThe following products will continue to be monitored:\n"
                    for sku in valid_skus:
                        product_name = sku_to_name_map.get(sku, f"Unknown Product ({sku})")
                        mismatch_message += f"- {product_name} ({sku})\n"
                
                # Provide next steps
                mismatch_message += "\n📋 NEXT STEPS:\n"
                mismatch_message += "1. Update your products.json file to match current NVIDIA product offerings\n"
                mismatch_message += "2. Run stockconfig.py to reconfigure your products\n"
                mismatch_message += "3. Restart the script\n"
                
                # Indicate if script will exit
                if not valid_skus:
                    mismatch_message += "\n🛑 No valid products remain to monitor. The script will now exit."
                
                # Send notification
                if notification_manager:
                    await notification_manager.send_startup_message(mismatch_message)
                
                # Print to console as well
                timestamp = get_timestamp()
                print(f"\n[{timestamp}] {mismatch_message}")
                
                # Exit if no valid SKUs
                if not valid_skus:
                    print(f"[{get_timestamp()}] 🛑 Exiting as there are no valid products to monitor.")
                    running = False
                    sys.exit(1)
            
            # Update cache with valid SKUs
            cached_skus = valid_skus
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
            # Get the product name from our mapping, or use a fallback if not found
            product_name = sku_to_name_map.get(sku, f"Unknown Product ({sku})")
            
            if CONSOLE_CONFIG["log_stock_checks"]:
                print(f"[{get_timestamp()}] ℹ️ Checking stock for {product_name}")
            
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

                        # Send notification using product name instead of SKU
                        await notification_manager.send_stock_alert(product_name, price, product_url, is_active)

                        # Open browser if configured and item is in stock
                        if is_active and NOTIFICATION_CONFIG["open_browser"]:
                            try:
                                webbrowser.open(product_url)
                            except Exception as e:
                                print(f"[{get_timestamp()}] ⚠️ Failed to open browser: {e}")

                        if is_active:
                            time.sleep(params['cooldown'])
                else:
                    print(f"[{get_timestamp()}] ℹ️ Product {product_name} is not currently in the system")
            
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
            print("NO CARDS HAVE BEEN SETUP FOR MONITORING. CHECK YOUR products.json FILE.")
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
        print(f"[{get_timestamp()}] Product config succesfully loaded from products.json")
        print(f"[{get_timestamp()}] Monitored Country: {country} ({currency})")
        print(f"[{get_timestamp()}] Monitoring Cards: {'None' if not selected_cards else ', '.join(selected_cards)}")
        print(f"[{get_timestamp()}] Check Interval: {params['check_interval']} seconds")
        print(f"[{get_timestamp()}] Cooldown Period: {params['cooldown']} seconds")
        print(f"[{get_timestamp()}] SKU Check Interval: {SKU_CHECK_CONFIG['interval']} seconds")
        print(f"[{get_timestamp()}] Browser Opening: {'Enabled' if NOTIFICATION_CONFIG['open_browser'] else 'Disabled'}")
        print(f"[{get_timestamp()}] Tip: Run with --test to test notifications")
        print(f"[{get_timestamp()}] Tip: Run with --list-cards to see all available cards")
        
        # Main monitoring loop
        try:
            # Add 'await' to properly handle the async function
            skus = await get_skus_if_needed(selected_cards, force_check=True)
        except Exception as e:
            print(f"[{get_timestamp()}] ❌ Initial SKU check failed: {str(e)}")
            print(traceback.format_exc())

        while running:
            try:
                # Record start time of check
                check_start_time = time.time()
                
                # Add 'await' to properly handle the async function
                skus = await get_skus_if_needed(selected_cards)
                await check_nvidia_stock(skus)
                
                if running:
                    # Calculate how long the check took
                    check_duration = time.time() - check_start_time
                    
                    # Calculate remaining time to sleep
                    sleep_time = max(0, params['check_interval'] - check_duration)
                    if sleep_time > 0:
                        await asyncio.sleep(sleep_time)
            except Exception as e:
                print(f"[{get_timestamp()}] ❌ Error during monitoring: {str(e)}")
                print(traceback.format_exc())
                if running:
                    await asyncio.sleep(params['check_interval'])
                        
    except Exception as e:
        print(f"[{get_timestamp()}] ❌ Fatal error: {str(e)}")
        print(traceback.format_exc())
    finally:
        # Ensure clean shutdown
        if notification_manager:
            await notification_manager.shutdown_handlers()

def list_available_cards():
    """Print all available cards and their descriptions"""
    print("\nProduct Configuration (from products.json):")
    for card, config in PRODUCT_CONFIG_CARDS.items():
        status = "✅ Enabled" if config["enabled"] else "❌ Disabled"
        sku = config.get("sku", "No SKU")
        print(f"  {card} - {status} (SKU: {sku})")
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
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Register signal handlers
    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for sig in signals:
        loop.add_signal_handler(sig.value, lambda s=sig: asyncio.create_task(shutdown(s, loop)))

    # Run the main async loop
    try:
        loop.run_until_complete(main())
    except asyncio.CancelledError:
        # Finish running the remaining tasks
        pending = asyncio.all_tasks(loop)
        loop.run_until_complete(asyncio.gather(*pending))
        pass
    finally:
        print(f"[{get_timestamp()}] Successfully shutdown")
        loop.close()