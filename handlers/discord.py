from typing import Optional
from discord_webhook import DiscordWebhook, DiscordEmbed
import aiohttp
from requests import Response
from . import NotificationHandler, get_timestamp

from config import DISCORD_CONFIG

class DiscordNotificationHandler(NotificationHandler):
    """Handler for Discord notifications"""

    def __init__(self):
        self.enabled = DISCORD_CONFIG["enabled"]
        self.webhook_url = DISCORD_CONFIG["webhook_url"]
        self.username = DISCORD_CONFIG["username"]
        self.avatar_url = DISCORD_CONFIG["avatar_url"]
        self.connected = False
        self.session: Optional[aiohttp.ClientSession] = None
        self.webhook: Optional[DiscordWebhook] = None
    
    async def initialize(self) -> bool:
        if not self.enabled or not self.webhook_url:
            print(f"[{get_timestamp()}] ℹ️ Discord notifications disabled or missing webhook URL")
            return False
            
        try:
            self.session = aiohttp.ClientSession()
            self.webhook = DiscordWebhook(url=self.webhook_url)
            
            # Test the connection by sending a simple message
            response = self._send_webhook(content="🔄 NVIDIA Stock Checker initializing...")
            response.raise_for_status()
            
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
        
        embed.add_embed_field(
            name="Links",
            value=f"[View Product]({url})",
            inline=False
        )

        content = DISCORD_CONFIG["mention"] if DISCORD_CONFIG["mention"] and in_stock else None

        self._send_webhook(content=content, embed=embed)
    
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

        embed = DiscordEmbed(
            title="NVIDIA Stock Checker Status Update",
            color="0099ff",
            description=f"""⏱️ Running for: {self.format_duration(data['runtime'])}
📈 Requests: {data['successful_requests']:,} successful, {data['failed_requests']:,} failed
{status_check} Last check: {last_check_str} ({status_text})
🎯 Monitoring: {'None' if not data['monitored_cards'] else ', '.join(data['monitored_cards'])}"""
        )

        self._send_webhook(embed=embed)
    
    async def send_startup_message(self, message: str) -> None:
        if not self.enabled or not self.connected:
            return
            
        embed = DiscordEmbed(
            title="NVIDIA Stock Checker",
            description=message
        )
        
        self._send_webhook(embed=embed)

    def format_duration(self, duration):
        """Format a duration into a readable string"""
        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60
        return f"{hours} hours {minutes} minutes"

    def _send_webhook(self, *, content: str = None, embed: DiscordEmbed = None) -> Response:
        """Helper method to send a message through the webhook"""
        try:
            webhook = DiscordWebhook(
                url=self.webhook_url,
                content=content,
                username=self.username,
                avatar_url=self.avatar_url
            )
            
            if embed:
                webhook.add_embed(embed)

            return webhook.execute()
        except Exception as e:
            print(f"[{get_timestamp()}] ❌ Failed to send Discord message: {str(e)}")
            self.connected = False
