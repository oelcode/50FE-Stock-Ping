# Nvidia 50 Series Founders Edition Stock Checker

A Python script to monitor 50 Series Founders Edition graphics card stock, allowing you to immediately open a browser window to the product page and/or send notifications through multiple channels when stock changes are detected.

The script supports checking of all currently known 50 series Founders Edition, customizable check intervals (10 secs default), and notifications via sound, auto browser opening, Discord, Home Assistant, NTFY, and Telegram.

## Supported Locales
| Country         | Locale  | Currency | Notes |
|----------------|--------|----------|------------------------------------------------|
| 🇦🇹 Austria        | de-at  | €        |                                                |
| 🇩🇰 Denmark        | da-dk  | kr       |                                                |
| 🇫🇮 Finland        | fi-fi  | €        |                                                |
| 🇫🇷 France         | fr-fr  | €        | Use for 🇧🇪 Belgium                            |
| 🇩🇪 Germany        | de-de  | €        |                                                |
| 🇮🇹 Italy          | it-it  | €        |                                                |
| 🇳🇱 Netherlands    | nl-nl  | €        |                                                |
| 🇳🇴 Norway         | nb-no  | kr       |                                                |
| 🇪🇸 Spain          | es-es  | €        |                                                |
| 🇸🇪 Sweden         | sv-se  | kr       |                                                |
| 🇬🇧 United Kingdom | en-gb  | £        |                                                |
| 🇺🇸 United States  | en-us  | $        | ⚠️ API endpoint frequently disabled. Check before use.  |

---

## Features

- **Multi-Channel Notifications**: Get stock alerts via console, Telegram, NTFY, Home Assistant, and Discord.
- **Quick Configuration Tool**: Use 'stockconfig.py' to easily set up monitoring for specific cards and locales.
- **Automatic SKU Detection**: The script tracks changes on the API, which avoids the script missing stock due to a wrong configuration.
- **Sound Alerts**: Plays a notification sound when stock is detected (Windows and macOS supported).
- **Browser Auto Opening**: Automatically opens the product page in your browser when stock is detected (see ⚠️IMPORTANT BROWSER AUTO OPEN NOTICE⚠️ below).
- **Periodic Status Updates**: Provides periodic status updates via configured notification channels.
- **Ad-hoc Status Updates (TELEGRAM ONLY)**: Use the `/status` command in Telegram to get the current status of the stock checker.
- **Advanced Error Handling**: Robust error recovery and graceful shutdown capabilities.
- **Critical Mobile Alerts (HOME ASSISTANT ONLY)**: Leverage Home Assistant's power notification support on iOS/Android, to ensure that you never miss a stock alert.

---

## Automatic Product Information Updates

The script periodically checks NVIDIA's API to ensure that it's tracking the correct products. It can detect both:
- **Name Changes**: When a product's display name changes but the SKU remains the same.
- **SKU Changes**: When a product's SKU changes but the display name remains the same.

When changes are detected, the script automatically updates its internal tracking and notifies you about these changes.

---

## Notification Support

### Telegram Notifications

When stock changes are detected, the script sends a Telegram message like this:

```
🔔 NVIDIA Stock Alert
✅ IN STOCK: GeForce RTX 5090
💰 Price: £1,939.00
🔗 Link: https://www.nvidia.com/en-gb/geforce/graphics-cards/50-series/rtx-5090/
```

Telegram Commands:
- **`/status`**: Get the current status of the stock checker, including uptime, # of API requests, and the cards being monitored.
- Follow this guide (https://docs.tracardi.com/qa/how_can_i_get_telegram_bot/) to get your bot setup. Add the token and chat ID's into config.py.

### NTFY Notifications

When stock changes are detected, the script sends a NTFY message to your configured topic with similar information to the Telegram message.

### Home Assistant Notifications

The script can send notifications to your Home Assistant instance, including critical alerts that can override Do Not Disturb settings on your device. 

Critical alerts can be configured in the `HOMEASSISTANT_CONFIG` section of your `config.py` file. Be advised, THIS WILL DISREGARD 'DO NOT DISTURB' SETTINGS ON YOUR DEVICE.
```python
    "critical_alerts_enabled": True,  # Set to True to enable critical alerts
    "critical_alerts_volume": 1.0     # Volume level for critical alerts (0.0 to 1.0)
```
Note - Critical Alerts will only work for "IN STOCK" alerts. Run the script with the `--test` arg to ensure this is setup properly.

### Discord Notifications

Stock alerts and status updates can be sent to a Discord channel via webhooks.

### Sound Notifications

- On **Windows**: Plays a system alert sound.
- On **macOS**: Plays the "Ping" sound.
- On **Linux**: Sound notifications are not supported.

### Browser Automation

If enabled, the script will automatically open the product page in your default browser when stock is detected. 

⚠️ Please refer to the "IMPORTANT BROWSER AUTO OPEN NOTICE" section above before using this feature, especially if you're also using remote notification services.

---

## Prerequisites

- Python 3.8 or higher
- Required Python packages:
  - `requests` and `aiohttp` (core dependencies)
  - `python-telegram-bot` (for Telegram notifications)
  - `discord-webhook` (for Discord notifications)

---

## Installation - METHOD 1

1. **Download ZIP from repo**:
   ```bash
   https://github.com/oelcode/50FE-Stock-Ping/archive/refs/heads/main.zip
   ```

2. **Install dependencies**:
   ```bash
   pip install requests aiohttp
   pip install python-telegram-bot  # For Telegram notifications
   pip install discord-webhook  # For Discord notifications
   ```

3. **Configure the script**:
   - Rename `example_config.py` to `config.py`:
   - Run the configuration tool to set up your product monitoring preferences:
   ```bash
     python stockconfig.py
   ```
   - Edit `config.py` to configure notification methods and other settings (each option has an explanation in the file).

## Installation - METHOD 2

1. **Clone the repository**:
   ```bash
   git clone https://github.com/oelcode/50FE-Stock-Ping.git
   cd 50FE-Stock-Ping
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt  # Installs all required dependencies from requirements.txt
   ```

3. **Configure the script**:
   - Copy the example config file:
     ```bash
     cp example_config.py config.py
     ```
   - Run the configuration tool to set up your product monitoring preferences:
     ```bash
     python stockconfig.py
     ```
   - Edit `config.py` to configure notification methods and other settings (each option has an explanation in the file).

---

<!--## Configuration

### Primary Configuration Files

- **`products.json`**: Contains locale settings and product configurations. Generated by the `stockconfig.py` tool.
- **`config.py`**: Contains notification settings, API configuration, and script behavior settings.

### Main Configuration Sections

- **`NOTIFICATION_CONFIG`**: Enable/disable sound notifications and browser auto-open.
- **`STATUS_UPDATES`**: Configure periodic status updates to show the script is running.
- **`CONSOLE_CONFIG`**: Configure console output behavior and logging level.
- **Notification Service Configs**:
  - `TELEGRAM_CONFIG`: Settings for Telegram notifications
  - `DISCORD_CONFIG`: Settings for Discord notifications
  - `NTFY_CONFIG`: Settings for NTFY notifications
  - `HOMEASSISTANT_CONFIG`: Settings for Home Assistant notifications

### Advanced Configuration

- **`SKU_CHECK_CONFIG`**: Controls how often the script validates product information against the NVIDIA API (default: 1 hour).
- **`API_CONFIG`**: Contains API endpoints, default parameters, and headers (modify only if you know what you're doing).

--- -->

##  ⚠️IMPORTANT BROWSER AUTO OPEN NOTICE⚠️

*Note 1*

This script was built with the understanding that the links provided to you are uniquely generated. Until this can be confirmed otherwise, you should be very careful about using BOTH the auto browser open feature and remote notifications at the same time.

"Why?" I hear you ask - well if the link is unique, if it has automatically opened in your browser, then it's probably not going to work for you if you open it from Telegram or another notification service on another device.

So, if your main use case is that you want to open the link from a notification service (you might not be at the machine running the script when the stock ping arrives), then DISABLE the auto browser open in config.py:

`"open_browser": False,`

*Note 2*

If you have the browser auto-open enabled, it's strongly recommended to run the script with the "--test" arg at least once. This will let you test to see if the browser opens correctly (it uses your default OS browser).

---

## Usage

### Running the Script

<!-- Before you start monitoring for stock, you need to run the configuration tool to set up your locale and product preferences:

```bash
python stockconfig.py
```

Then run the stock checker: -->

```bash
python 50check.py
```

### Command-Line Arguments

| Argument               | Description                                                                 |
|------------------------|-----------------------------------------------------------------------------|
| `--test`               | Run in test mode to check the notification system.                          |
| `--list-cards`          | List all available cards and exit.                                           |
| `--cooldown`           | Cooldown period in seconds after finding stock (default: from config).               |
| `--check-interval`     | Time between checks in seconds (default: from config).                               |
| `--sku-check-interval` | Time between API product validation checks in seconds (default: 3600).                         |
| `--no-browser`         | Disable automatic browser opening (Overrides any config setting).                              |

### Example Commands

1. **Run in test mode**:
   ```bash
   python 50check.py --test
   ```

2. **List available cards**:
   ```bash
   python 50check.py --list-cards
   ```

3. **Custom check interval and cooldown**:
   ```bash
   python 50check.py --check-interval 30 --cooldown 5
   ```

---

## Example Console Output

```
[2025-03-17 14:35:47] Stock checker started. Monitoring for changes...
[2025-03-17 14:35:47] Product config succesfully loaded from products.json
[2025-03-17 14:35:47] Monitored Country: United States ($)
[2025-03-17 14:35:47] Monitoring Cards: NVIDIA RTX 5090, NVIDIA RTX 5080
[2025-03-17 14:35:47] Check Interval: 10 seconds
[2025-03-17 14:35:47] Cooldown Period: 120 seconds
[2025-03-17 14:35:47] SKU Check Interval: 3600 seconds
[2025-03-17 14:35:47] Browser Opening: Enabled
[2025-03-17 14:35:47] Tip: Run with --test to test notifications
[2025-03-17 14:35:47] Tip: Run with --list-cards to see all available cards
[2025-03-17 14:35:47] 🚀 Performing initial SKU check...
[2025-03-17 14:35:47] 📋 Current SKU's listed on API: GeForce RTX 5090 (NVGFT590), GeForce RTX 5080 (NVGFT580)
[2025-03-17 14:35:47] ✅ Initial SKU check complete
[2025-03-17 14:35:47] ℹ️ Checking stock for GeForce RTX 5090
[2025-03-17 14:35:47] ✅ IN STOCK: GeForce RTX 5090 - $1,999.00
```

---

## Contributing

Contributions are welcome! If you'd like to contribute, please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature or bugfix.
3. Submit a pull request.

---

## Disclaimer

This script is for educational and personal use only. The author is not responsible for any misuse or damages caused by this script. Use at your own risk.

---

Good luck! 🚀
