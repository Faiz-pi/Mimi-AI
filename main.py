import discord
from discord.ext import commands
import asyncio
import logging
import os
from dotenv import load_dotenv

load_dotenv()

from bot.commands.chat import ChatCommands
from bot.commands.moderation import ModerationCommands
from bot.commands.server import ServerCommands
from bot.events.message import MessageEvents
from bot.events.member import MemberEvents
from config.settings import BotConfig

# Configure logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AIDiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        
        super().__init__(
            command_prefix=BotConfig.COMMAND_PREFIX,
            intents=intents,
            help_command=None,
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="your messages | /help"
            )
        )
        
    async def setup_hook(self):
        
        await self.add_cog(ChatCommands(self))
        await self.add_cog(ModerationCommands(self))
        await self.add_cog(ServerCommands(self))
        
        #Event Handler
        await self.add_cog(MessageEvents(self))
        await self.add_cog(MemberEvents(self))
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")

    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f"{self.user} has connected to Discord!")
        logger.info(f"Bot is in {len(self.guilds)} guilds")
        
        # Set bot status
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(self.guilds)} servers"
            )
        )

    async def on_error(self, event, *args, **kwargs):
        """Global error handler"""
        logger.error(f"Error in {event}: {args[0] if args else 'Unknown'}")

async def main():
    """Main function to run the bot"""
    # Validate environment variables
    if not BotConfig.DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN not found in environment variables")
        return
    
    if not BotConfig.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not found in environment variables")
        return
    
    # Create and run bot
    bot = AIDiscordBot()
    
    try:
        await bot.start(BotConfig.DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
    finally:
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main())
