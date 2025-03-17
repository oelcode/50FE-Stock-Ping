# =================================
# Product Configuration
# =================================
# Set to True/False to enable/disable checking for specific products
PRODUCT_CONFIG_CARDS = {
    "NVIDIA RTX 5090": {
        "enabled": False
    },
    "NVIDIA RTX 5080": {
        "enabled": False
    }
}

LOCALE_CONFIG = {
    "locale": "en-gb",  # Locale to use for the NVIDIA store (en-gb, de-de, etc)
    "country": "United Kingdom",  # Name of the country corresponding to the locale
    "currency": "£"    # Currency symbol to use in notifications (£, €, etc)
}

SKU_CHECK_CONFIG = {
    "interval": 3600,  # How often to check for the Nvida API for product info changes (in seconds, default is 3600 = 1 hour)
}

# =================================
# Core Notification Configuration
# =================================
NOTIFICATION_CONFIG = {
    "play_sound": True,    # Whether to play a sound when stock is found
    "open_browser": True,  # Whether to auto open the browser when stock is found (DONT USE WITH TELEGRAM NOTIFICATIONS - SEE README)
}
# =================================
# Script Health Updates Configuration
# This sends a notification to the console and/or Telegram to show you that the script is still running properly.
# THIS IS NOT THE STOCK NOTIFIER.
# =================================
STATUS_UPDATES = {
    "enabled": True,  # Enable/disable script health updates
    "interval": 60 * 60,  # Console script health update interval in seconds (1 hour default - edit the first number)
}

CONSOLE_CONFIG = {
    "enabled": True,
    "log_stock_checks": False
}

SOUND_CONFIG = {
    "enabled": True,
}

TELEGRAM_CONFIG = {
    "enabled": False,             # Master switch for Telegram functionality (WARNING DONT USE AUTO BROWSER OPEN AT THE SAME TIME - SEE README)
    "bot_token": "XXXXXXX",  # Your bot token
    "chat_id": "XXXXXXX",        # Your chat ID
}

DISCORD_CONFIG = {
    "enabled": False,
    "webhook_url": "",  # Discord webhook URL
    "username": "NVIDIA Stock Checker",  # Custom username for webhook messages
    "mention": "",  # Optional: Mention a user or a role. Format: <@user_id> or <@&role_id>
    "avatar_url": ""  # Optional: avatar URL for the webhook
}

# =================================
# NTFY Configuration
# =================================
NTFY_CONFIG = {
    "enabled": True,
    "server_url": "https://ntfy.sh",  # ntfy server URL
    "topic": "",  # The notification topic to publish to
    "username": "",  # Optional: Basic auth username
    "password": "",  # Optional: Basic auth password
    "access_token": "",  # Optional: Access token for authentication (OVERRIDES USERNAME/PASSWORD AUTH)
    "priority": "default"  # Optional: Default priority for notifications
}

HOMEASSISTANT_CONFIG = {
    "enabled": False,
    "ha_url": "http://homeassistant.local:8123",  # Home Assistant URL
    "ha_token": "",  # Long-lived access token
    "notification_service": "mobile_app_phone"  # The notification service to use
}

# =================================
# API Configuration
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
# LEAVE THIS SECTION ALONE IF YOU DON'T KNOW WHAT THIS MEANS.
