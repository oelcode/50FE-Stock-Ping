
---

# Nvidia 50 Series Founders Edition Stock Checker

A Python script to monitor 50 Series Founders Edition graphics card stock, allowing you to immediately open a browser window to the product page and/or send notifications via Telegram when stock changes are detected.

The script supports checking of all currently known 50 series Founders Edition, customizable check intervals (10 secs default), and notifications via sound, browser opening, and Telegram messages.

#### Supported Locales
| Country         | Locale  | Currency | Notes |
|----------------|--------|----------|------------------------------------------------|
| 🇦🇹 Austria        | de-at  | €        |                                                |
| 🇩🇰 Denmark        | da-dk  | kr       |                                                |
| 🇫🇮 Finland        | fi-fi  | €        |                                                |
| 🇫🇷 France         | fr-fr  | €        |                                                |
| 🇩🇪 Germany        | de-de  | €        |                                                |
| 🇮🇹 Italy          | it-it  | €        |                                                |
| 🇳🇱 Netherlands    | nl-nl  | €        |                                                |
| 🇪🇸 Spain          | es-es  | €        |                                                |
| 🇸🇪 Sweden         | sv-se  | kr       |                                                |
| 🇬🇧 United Kingdom | en-gb  | £        |                                                |
| 🇺🇸 United States  | en-us  | $        | ⚠️ API is frequently disabled.  |

---

## Features

- **NEW - Support for all known locales**: The script has been updated to support all known locales.
- **NEW - Quick config tool**: The new 'stockconfig.py' tool allows a quick way to ensure your config is properly setup to monitor the card(s) you want, and from the correct Nvidia store.
- **Real-time Stock Monitoring**: Continuously checks NVIDIA's API for stock updates.
- **Sound Alerts**: Plays a notification sound when stock is detected (Windows and macOS supported).
- **Browser Auto Opening**: Automatically opens the product page in your browser when stock is detected.
- **Status Updates**: Provides periodic status updates via console or Telegram.
- **Telegram Notifications**: Sends alerts when stock status changes (e.g., in stock or out of stock).
- **Telegram Status Checking**: Use the `/status` command in Telegram to get the current status of the stock checker.
- **SKU Validation**: Periodically (configurable) checks the API for updates to product information. Nvidia occasionally change this, so the script will warn you every 5 minutes for 25 minutes if there is a mismatch between the API information and the local configuration. Run 'stockconfig.py' to update your configuration

---

## Prerequisites

- Python 3.8 or higher
- A Telegram bot token and chat ID (for Telegram notifications)
- Required Python packages: `requests` & `python-telegram-bot`

---

## Installation - METHOD 1

1. **Save below files from repo**:
   ```bash
   50check.py
   config.py
   stockconfig.py
   locales.txt
   ```

2. **Install dependencies**:
   ```bash
   pip install requests
   pip install python-telegram-bot - Not required if you don't want to use the Telegram feature. Just ensure all configs are disabled.
   ```

3. **Configure the script**:
   - Edit `config.py` to your preference. If you want to use the Telegram notifications, ensure you add your Telegram bot token and chat ID.

## Installation - METHOD 2

1. **Clone the repository**:
   ```bash
   git clone https://github.com/oelcode/50FE-Stock-Ping.git
   cd nvidia-stock-checker
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the script**:
   - Copy the `config.example.py` file to `config.py`:
     ```bash
     cp config.example.py config.py
     ```
   - Edit `config.py` to your preference. If you want to use the Telegram notifications, ensure you add your Telegram bot token and chat ID.

---

## Configuration

The `config.py` file contains all the configuration options. Here are the key settings:

- **`PRODUCT_CONFIG_CARDS`**: Set the enabled flag for the cards you want to monitor.
- **`NOTIFICATION_CONFIG`**: Enable or disable sound notifications, browser auto open, and logging of stock checks.
- **`TELEGRAM_CONFIG`**: All Telegram features are turned off by default. Configure your Telegram bot token and chat ID ([Setup guide](https://gist.github.com/nafiesl/4ad622f344cd1dc3bb1ecbe468ff9f8a)).
- **`API_CONFIG`**: Configure the NVIDIA API URL and parameters. (DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING).
- **`SKU_CHECK_CONFIG`**: Configure the interval for refreshing SKUs (default: 3600 seconds).

---

##  ⚠️IMPORTANT BROWSER AUTO OPEN NOTICE⚠️

*Note 1*

This script was built with the understanding that the links provided to you are uniquely generated. Until I can confirm otherwise, you should be very careful about using BOTH the auto browser open feature and the Telegram notification at the same time.

"Why?" I hear you ask - well if the link is unique, if it has automatically opened in your browser, then it's probably not going to work for you if you open it from Telegram on another device.

So, if your main use case is that you want to open the link from Telegram (you might not be at the machine running the script when the stock ping arrives), then DISABLE the auto browser open in config.py

`"open_browser": False,`

This will stop the browser from auto-opening the new links, but will still send them to you via Telegram.

*Note 2*

If you have the browser auto-open enabled, I'd strongly recommend running the script with the "--test" arg at least once. This will let you test to see if the browser opens correctly (it uses your default OS browser). After the configured cooldown period, the script will run in normal mode, so feel free to start using the "--test" arg every time for safety. There are a lot more args listed below, mostly used for me to test things work with the script, but I left them in the code in case you find them useful.

---

## Usage

### Running the Script

Before you start monitoring for stock, you need to run the quick config tool to setup your configuration options. This contains a list of known working locale options for you to choose from, but you can also enter a custom locale to check if it works.

```bash
python stockconfig.py
```

Once this has been done, you may edit 'config.py' for any further configuration before you may need (interval timings, Telegram bot credentials etc).

When you're ready to run the script, run the below command:

```bash
python 50check.py
```

### Command-Line Arguments

The script supports several command-line arguments for customization. Most users should set their configuration via "config.py". The Command-line args are simply for customising checks on the fly, without having to keep editing "config.py".

| Argument               | Description                                                                 |
|------------------------|-----------------------------------------------------------------------------|
| `--test`               | Run in test mode to check the notification system.                          |
| `--list-cards`          | List all available cards and exit.                                           |
| `--cooldown`           | Cooldown period in seconds after finding stock (default: 10).               |
| `--check-interval`     | Time between checks in seconds (default: 60).                               |
| `--console-status`     | Enable console status updates.                                              |
| `--no-console-status`  | Disable console status updates.                                             |
| `--console-interval`   | Time between console status updates in seconds.                             |
| `--telegram-status`    | Enable Telegram status updates.                                             |
| `--no-telegram-status` | Disable Telegram status updates.                                            |
| `--telegram-interval`  | Time between Telegram status updates in seconds.                            |
| `--telegram-token`     | Telegram bot token (overrides configuration).                               |
| `--telegram-chat-id`   | Telegram chat ID (overrides configuration).                                 |
| `--no-sound`           | Disable notification sounds.                                                |
| `--no-browser`         | Disable automatic browser opening.                                          |
| `--sku-check-interval` | Time between API product validation checks in seconds (default: 3600).                         |
| `--log-stock-checks`   | Toggle the logging of stock checks to the console.                              |

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

4. **Enable logging of stock checks**:
   ```bash
   python 50check.py --log-stock-checks
   ```

---

## Telegram Commands

- **`/status`**: Get the current status of the stock checker, including uptime, # of API requests, and the cards being monitored.

---

## Notifications

### Telegram Notifications

When stock changes are detected, the script sends a Telegram message like this:

```
🔔 NVIDIA Stock Alert
✅ IN STOCK: GeForce RTX 5090
💰 Price: £1,939.00
🔗 Link: https://www.nvidia.com/en-gb/geforce/graphics-cards/50-series/rtx-5090/
```

### Sound Notifications

- On **Windows**: Plays a system alert sound.
- On **macOS**: Plays the "Ping" sound.
- On **Linux**: Sound notifications are not supported.

### Browser Automation

If enabled, the script will automatically open the product page in your default browser when stock is detected.

---

## Example Output

### Console Output

```
[2023-10-25 14:35:47] ℹ️ Checking stock for GeForce RTX 5090...
[2023-10-25 14:35:47] ✅ IN STOCK: GeForce RTX 5090 - £1,939.00
[2023-10-25 14:35:47] 🔗 NVIDIA Link: https://www.nvidia.com/en-gb/geforce/graphics-cards/50-series/rtx-5090/
```

### Telegram Startup Message

```
🚀 NVIDIA Stock Checker Started Successfully!
🎯 Monitoring: GeForce RTX 5090, GeForce RTX 5080
⏱️ Check Interval: 10 seconds
🔔 Notifications: Enabled
🌐 Browser Opening: Enabled
📢 Type /status to get the latest script statistics.
```

---

## Contributing

Contributions are welcome! If you'd like to contribute, please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature or bugfix.
3. Submit a pull request.

---

## To do

- Add proxy functionality to help spread API requests across multiple IP's (in case Nvidia start blocking IP's for hammering their API - sorry Nvidia!).
- Add support for more regions and currencies - the list is being updated as they are discovered.
- Improve error handling for API rate limiting - Currently, failed checks are handled quietly, and the script keeps retrying until it works again. This hasn't been a big issue as the API seems to be quite robust, but I want to be prepared in case Nvidia get stricter.

---

## Disclaimer

This script is for educational and personal use only. The author is not responsible for any misuse or damages caused by this script. Use at your own risk.

---

Good luck! 🚀

---
