---

# Nvidia 50 Series Founders Edition Stock Checker (UK) 🇬🇧

A Python script to monitor 50 Series Founders Edition graphics card stock, allowing you to immediately open a browser window to the product page and/or send notifications via Telegram when stock changes are detected.

The script supports checking of all currently known 50 series Founders Edition, customisable check intervals (2 secs default), and notifications via sound, browser opening, and Telegram messages.

---

## Features

- **Real-time Stock Monitoring**: Continuously checks NVIDIA's API for stock updates.
- **Sound Alerts**: Plays a notification sound when stock is detected (Windows and macOS supported).
- **Browser Auto Open**: Automatically opens the product page in your browser when stock is detected.
- **Status Updates**: Provides periodic status updates via console or Telegram.
- **Telegram Notifications**: Sends alerts when stock status changes (e.g., in stock or out of stock).
- **Telegram Status checking**: Use the `/status` command in Telegram to get the current status of the stock checker.

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
   git clone https://github.com/oelcode/50FE-UK-Ping.git
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
- **`NOTIFICATION_CONFIG`**: Enable or disable sound notifications and browser auto open (READ THE NOTICE BELOW.
- **`TELEGRAM_CONFIG`**: All Telegram features are turned off by default. Configure your Telegram bot token and chat ID ([Setup guide](https://gist.github.com/nafiesl/4ad622f344cd1dc3bb1ecbe468ff9f8a))
- **`API_CONFIG`**: Configure the NVIDIA API URL and parameters. (DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING)

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

To start monitoring NVIDIA stock, run the script with the following command:

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

## Telegram Commands

- **`/status`**: Get the current status of the stock checker, including runtime, requests, and monitored cards.

---

## Notifications

### Telegram Notifications

When stock changes are detected, the script sends a Telegram message like this:

```
🔔 NVIDIA Stock Alert
✅ IN STOCK: GeForce RTX 4090 (5090)
💰 Price: £1,499.00
🔗 Link: https://www.nvidia.com/en-us/geforce/graphics-cards/40-series/rtx-4090/
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
[2023-10-25 14:35:47] ✅ IN STOCK: GeForce RTX 4090 (5090) - £1,499.00
[2023-10-25 14:35:47] 🔗 NVIDIA Link: https://www.nvidia.com/en-us/geforce/graphics-cards/40-series/rtx-4090/
```

### Telegram Startup Message

```
🚀 NVIDIA Stock Checker Started Successfully!
🎯 Monitoring: GeForce RTX 4090, GeForce RTX 4080
⏱️ Check Interval: 60 seconds
🔔 Notifications: Enabled
🌐 Browser Opening: Enabled
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

---

## Disclaimer

This script is for educational and personal use only. The author is not responsible for any misuse or damages caused by this script. Use at your own risk.

---

Good luck! 🚀

---
