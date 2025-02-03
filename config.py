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
    "interval": 3600,  # How often to check for the Nvidia API for product info changes (in seconds, default is 3600 = 1 hour)
}

# Browser auto-open configuration
BROWSER_CONFIG = {
    "auto_open": True  # Whether to auto open the browser when stock is found (default is True)
}

# =================================
# API Configuration
# LEAVE THIS SECTION ALONE IF YOU DON'T KNOW WHAT THIS MEANS.
# =================================
API_CONFIG = {
    "url": "https://api.store.nvidia.com/partner/v1/feinventory",
    "params": {
        "locale": LOCALE_CONFIG["locale"],
        "cooldown": 120,       # Seconds to wait after finding stock before resuming checks (60 seconds default)
        "check_interval": 10   # Seconds between checks (10secs default)
    },
    "headers": {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://marketplace.nvidia.com",
        "Origin": "https://marketplace.nvidia.com",
        "Connection": "keep-alive",
    },
    "base_url": f"https://marketplace.nvidia.com/{LOCALE_CONFIG['locale']}/consumer/graphics-cards/?locale={LOCALE_CONFIG['locale']}&page=1&limit=12&category=GPU&manufacturer=NVIDIA&manufacturer_filter=NVIDIA~2,ASUS~31,GAINWARD~5,GIGABYTE~18,INNO3D~3,KFA2~1,MSI~22,PALIT~10,PNY~7,ZOTAC~14"
}

SKU_CHECK_API_CONFIG = {
    "url": "https://api.nvidia.partners/edge/product/search"
}
