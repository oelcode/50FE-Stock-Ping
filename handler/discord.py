import json
import os
from typing import Optional
from discord_webhook import DiscordWebhook, DiscordEmbed
import aiohttp
from . import NotificationHandler, get_timestamp

class DiscordNotificationHandler(NotificationHandler):
    """Handler for Discord notifications"""
    
    # Default configuration
    DEFAULT_CONFIG = {
        "enabled": False,
        "webhook_url": "",  # Discord webhook URL
        "username": "NVIDIA Stock Checker",  # Custom username for webhook messages
        "avatar_url": ""  # Optional avatar URL for the webhook
    }
    
    def __init__(self):
        self.config = self.load_config()
        self.enabled = self.config["enabled"]
        self.webhook_url = self.config["webhook_url"]
        self.username = self.config["username"]
        self.avatar_url = self.config["avatar_url"]
        self.connected = False
        self.session: Optional[aiohttp.ClientSession] = None
        self.webhook: Optional[Webhook] = None
    
    def load_config(self) -> dict:
        """Load configuration from local config file"""
        handler_dir = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(handler_dir, "discord_config.json")
        
        config = self.DEFAULT_CONFIG.copy()
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    file_config = json.load(f)
                config.update(file_config)
            else:
                with open(config_file, 'w') as f:
                    json.dump(self.DEFAULT_CONFIG, f, indent=4)
                print(f"[{get_timestamp()}] Created default Discord config at: {config_file}")
        except Exception as e:
            print(f"[{get_timestamp()}] ⚠️ Error loading Discord config: {str(e)}")
        
        return config
    
    async def initialize(self) -> bool:
        if not self.enabled or not self.webhook_url:
            print(f"[{get_timestamp()}] ℹ️ Discord notifications disabled or missing webhook URL")
            return False
            
        try:
            self.session = aiohttp.ClientSession()
            self.webhook = DiscordWebhook(url=self.webhook_url)
            
            # Test the connection by sending a simple message
            webhook = DiscordWebhook(
                url=self.webhook_url,
                content="🔄 NVIDIA Stock Checker initializing...",
                username=self.username,
                avatar_url=self.avatar_url
            )
            response = webhook.execute()
            
            self.connected = True
            print(f"[{get_timestamp()}] ✅ Discord notification handler initialized")
            return True
            
        except Exception as e:
            print(f"[{get_timestamp()}] ❌ Failed to initialize Discord connection: {str(e)}")
            self.connected = False
            return False
    
    async def shutdown(self) -> None:
        if self.session:
            try:
                await self.session.close()
                print(f"[{get_timestamp()}] ✅ Discord notification handler shutdown")
            except Exception as e:
                print(f"[{get_timestamp()}] ⚠️ Error during Discord shutdown: {str(e)}")
    
    async def send_stock_alert(self, sku: str, price: str, url: str, in_stock: bool) -> None:
        if not self.enabled or not self.connected:
            return
            
        status = "✅ IN STOCK" if in_stock else "❌ OUT OF STOCK"
        color = "00ff00" if in_stock else "ff0000"
        
        embed = DiscordEmbed(
            title="NVIDIA Stock Alert",
            url=url,
            color=color,
            description=f"{status}: {sku}\n💰 Price: {price}"
        )
        
        embed.add_field(
            name="Quick Access",
            value=f"[View Product]({url})",
            inline=False
        )

        await self._send_webhook(embed=embed)
    
    async def send_status_update(self, data: dict) -> None:
        if not self.enabled or not self.connected:
            return

        status_check = "✅" if data['last_check_success'] else "❌"
        status_text = "Successful" if data['last_check_success'] else "Failed"
        
        last_check_str = "No checks completed"
        if data['last_check_time']:
            last_check_str = data['last_check_time'].strftime("%H:%M:%S %d/%m/%Y")
            minutes_since = data['time_since_check'].seconds // 60
            last_check_str += f" ({minutes_since}m ago)"

        embed = discord.Embed(
            title="NVIDIA Stock Checker Status Update",
            color="0099ff",
            description=f"""⏱️ Running for: {self.format_duration(data['runtime'])}
📈 Requests: {data['successful_requests']:,} successful, {data['failed_requests']:,} failed
{status_check} Last check: {last_check_str} ({status_text})
🎯 Monitoring: {'None' if not data['monitored_cards'] else ', '.join(data['monitored_cards'])}"""
        )

        await self._send_webhook(embed=embed)
    
    async def send_startup_message(self, message: str) -> None:
        if not self.enabled or not self.connected:
            return
            
        embed = discord.Embed(
            title="NVIDIA Stock Checker",
            color=discord.Color.blue(),
            description=message
        )
        
        await self._send_webhook(embed=embed)

    def format_duration(self, duration):
        """Format a duration into a readable string"""
        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60
        return f"{hours} hours {minutes} minutes"

    async def _send_webhook(self, *, content: str = None, embed: DiscordEmbed = None) -> None:
        """Helper method to send a message through the webhook"""
        if not self.webhook_url:
            return
            
        try:
            webhook = DiscordWebhook(
                url=self.webhook_url,
                content=content,
                username=self.username,
                avatar_url=self.avatar_url
            )
            
            if embed:
                webhook.add_embed(embed)
        except Exception as e:
            print(f"[{get_timestamp()}] ❌ Failed to send Discord message: {str(e)}")
            self.connected = False