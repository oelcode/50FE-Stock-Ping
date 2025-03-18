import json
import os
import sys

# =================================
# Core Timing Configuration
# Key settings that control the stock checking behavior
# =================================
API_CHECK_INTERVAL = 10  # Seconds between stock checks (10 secs default)
COOLDOWN_PERIOD = 120  # Seconds to wait after finding stock before resuming checks (120 seconds default)
SKU_CHECK_INTERVAL = 1  # How often to check the Nvidia API for product info changes (in hours, default is 1 hour)

# =================================
# Core Notification Configuration
# =================================
NOTIFICATION_CONFIG = {
    "play_sound": True,    # Whether to play a sound when stock is found
    "open_browser": True,  # Whether to auto open the browser when stock is found (DONT USE WITH TELEGRAM NOTIFICATIONS - SEE README)
}

SOUND_CONFIG = {
    "enabled": True,
}

# =================================
# Script Health Updates Configuration
# THIS IS NOT THE STOCK NOTIFIER.
# =================================
STATUS_UPDATES = { # This sends a notification to the console and any configured notification platforms to remind you that the script is still running properly.
    "enabled": True,  # Enable/disable
    "hours": 12,       # How often to send status updates (in hours)
}

CONSOLE_CONFIG = {
    "enabled": True, # DON'T DISABLE THIS
    "log_stock_checks": False # Enable/disable logging each stock check to the console
}
# =================================
# NOTIFICATION SERVICE API CONFIGURATION
# These are the notification services that will be used to send notifications when stock is found.
# You can enable multiple services at once.
# =================================
NTFY_CONFIG = {
    "enabled": False,
    "server_url": "https://ntfy.sh",  # ntfy server URL
    "topic": "YOUR_TOPIC_HERE",  # The notification topic to publish to
    "username": "",  # Optional: Basic auth username
    "password": "",  # Optional: Basic auth password
    "access_token": "",  # Optional: Access token for authentication (OVERRIDES USERNAME/PASSWORD AUTH)
    "priority": "high"  # Optional: Default priority for notifications
}

HOMEASSISTANT_CONFIG = {
    "enabled": False,
    "ha_url": "http://YOUR_HA_SERVER:8123",  # Home Assistant URL
    "ha_token": "YOUR_HA_TOKEN_HERE",  # Long-lived access token
    "notification_service": "YOUR_NOTIFICATION_SERVICE",  # The notification service to use
    "critical_alerts_enabled": True,  # Whether to send in-stock alerts as critical
    "critical_alerts_volume": 1.0  # Volume level for critical alerts (0.0 to 1.0) - default is 1.0
}

TELEGRAM_CONFIG = {
    "enabled": False,             # WARNING DONT USE AUTO BROWSER OPEN AT THE SAME TIME - SEE README
    "bot_token": "YOUR_BOT_TOKEN_HERE",  # Your bot token
    "chat_id": "YOUR_CHAT_ID_HERE",        # Your chat ID
}

DISCORD_CONFIG = {
    "enabled": False,
    "webhook_url": "",  # Discord webhook URL
    "username": "NVIDIA Stock Checker",  # Custom username for webhook messages
    "mention": "",  # Optional: Mention a user or a role. Format: <@user_id> or <@&role_id>
    "avatar_url": ""  # Optional: avatar URL for the webhook
}
# =================================
# PRODUCT AND LOCALE CONFIG LOADING
# LEAVE THIS SECTION ALONE IF YOU DON'T KNOW WHAT THIS MEANS.
# =================================
def load_json_config():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, 'products.json')
    
    try:
        with open(json_path, 'r') as f:
            config_data = json.load(f)
        return config_data
    except FileNotFoundError:
        print(f"Error: products.json file not found at {json_path}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: products.json contains invalid JSON")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading products.json: {e}")
        sys.exit(1)

json_config = load_json_config() # Load configuration from JSON - this will exit if file can't be loaded
PRODUCT_CONFIG_CARDS = json_config['product_config_cards'] # Get product config from JSON
LOCALE_CONFIG = json_config['locale_config'] # Get locale info from JSON

# =================================
# NVIDIA API CONFIGURATION
# LEAVE THIS SECTION ALONE IF YOU DON'T KNOW WHAT THIS MEANS.
# =================================
API_CONFIG = {
    "url": "https://api.store.nvidia.com/partner/v1/feinventory",
    "params": {
        "locale": LOCALE_CONFIG["locale"],
        "cooldown": COOLDOWN_PERIOD,  # References the variable defined at the top
        "check_interval": API_CHECK_INTERVAL  # References the variable defined at the top
    },
    "headers": {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://marketplace.nvidia.com",
        "Origin": "https://marketplace.nvidia.com",
        "Connection": "keep-alive",
    },
    "base_url": f"https://marketplace.nvidia.com/{LOCALE_CONFIG['locale']}/consumer/graphics-cards/?locale={LOCALE_CONFIG['locale']}&page=1&limit=12&category=GPU&manufacturer=NVIDIA&manufacturer_filter=NVIDIA~2,ASUS~31,GAINWARD~5,GIGABYTE~18,INNO3D~3,KFA2~1,MSI~22,PALIT~10,PNY~7,ZOTAC~14"}
SKU_CHECK_API_CONFIG = {
    "url": "https://api.nvidia.partners/edge/product/search"
}
SKU_CHECK_CONFIG = {
    "interval": SKU_CHECK_INTERVAL * 3600,  # Converted from hours to seconds using the variable defined at the top
}
STATUS_UPDATES["interval"] = STATUS_UPDATES["hours"] * 3600 # DO NOT CHANGE.
# LEAVE THIS SECTION ALONE IF YOU DON'T KNOW WHAT THIS MEANS.
