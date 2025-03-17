import json
import os
import sys

# =================================
# Core Notification Configuration
# =================================
NOTIFICATION_CONFIG = {
    "play_sound": True,    # Whether to play a sound when stock is found
    "open_browser": True,  # Whether to auto open the browser when stock is found (DONT USE WITH TELEGRAM NOTIFICATIONS - SEE README)
}

SOUND_CONFIG = {
    "enabled": True, # Enable/disable sound notifications - MUST BE SAME AS "play_sound" IN NOTIFICATION_CONFIG
}

# =================================
# PERIODIC STATUS UPDATES CONFIGURATION
# This sends a notification to the console and/or your configured platforms to show you that the script is still running properly.
# THIS IS NOT THE STOCK NOTIFIER.
# =================================
STATUS_UPDATES = {
    "enabled": False,  # Enable/disable script health updates
    "interval": 60 * 60,  # Console script health update interval in seconds (1 hour default - edit the first number)
}
# =================================
# NOTIFICATION API CONFIGURATION
# These are the notification services that will be used to send notifications when stock is found.
# You can enable multiple services at once.
# =================================
CONSOLE_CONFIG = { # Enables showing updates in the console. RECOMMEND THIS IS KEPT ENABLED
    "enabled": True, 
    "log_stock_checks": False # Show each stock check in the console. (Default = False)
}
NTFY_CONFIG = {
    "enabled": False,
    "server_url": "https://ntfy.sh",  # ntfy server URL
    "topic": "XXXXXX",  # The notification topic to publish to
    "username": "",  # Optional: Basic auth username
    "password": "",  # Optional: Basic auth password
    "access_token": "",  # Optional: Access token for authentication (OVERRIDES USERNAME/PASSWORD AUTH)
    "priority": "high"  # Optional: Default priority for notifications
}

HOMEASSISTANT_CONFIG = {
    "enabled": False,
    "ha_url": "http://homeassistant.local:8123",  # Home Assistant URL
    "ha_token": "XXXXXXXX",  # Long-lived access token
    "notification_service": "mobile_app_XXXXXX",  # The notification service to use
    "critical_alerts_enabled": False,  # Whether to send in-stock alerts as critical
    "critical_alerts_volume": 1.0  # Volume level for critical alerts (0.0 to 1.0) - default is 1.0
}

TELEGRAM_CONFIG = { # You'll need your own bot: https://docs.radist.online/docs/our-products/radist-web/connections/telegram-bot/instructions-for-creating-and-configuring-a-bot-in-botfather
    "enabled": False,             # WARNING DONT USE AUTO BROWSER OPEN AT THE SAME TIME - SEE README
    "bot_token": "XXXXXXXX",  # Your bot token
    "chat_id": "XXXXXXXX",        # Your chat ID
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
        "cooldown": 120,       # Seconds to wait after finding stock before resuming checks (120 seconds default)
        "check_interval": 10   # Seconds between checks (10secs default)
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
    "interval": 3600,  # How often to check for the Nvida API for product info changes (in seconds, default is 3600 = 1 hour)
}
# LEAVE THIS SECTION ALONE IF YOU DON'T KNOW WHAT THIS MEANS.
