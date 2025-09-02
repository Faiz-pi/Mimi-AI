import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional

from bot.utils.gemini_client import GeminiClient
from bot.utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

class ModerationCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.gemini_client = GeminiClient()
        self.rate_limiter = RateLimiter()
        # Store auto-moderation settings per guild
        self.auto_moderation = {}
        
    @app_commands.command(name="moderate", description="Check if text violates community guidelines")
    @app_commands.describe(text="Text to check for policy violations")
    async def moderate(self, interaction: discord.Interaction, text: str):
        """Manual content moderation check"""
        await interaction.response.defer(thinking=True)
        
        try:
            # Check rate limits
            if not self.rate_limiter.check_rate_limit(interaction.user.id, "moderate"):
                await interaction.followup.send(
                    "⏰ You're using moderation too frequently! Please wait.",
                    ephemeral=True
                )
                return
            
            # Check content with Gemini moderation
            moderation_result = await self.gemini_client.moderate_content(text)
            
            if moderation_result["flagged"]:
                # Create warning embed
                embed = discord.Embed(
                    title="⚠️ Content Warning",
                    description="The provided text was flagged for potential policy violations:",
                    color=0xff6b6b
                )
                
                flagged_categories = [
                    category for category, flagged in moderation_result["categories"].items()
                    if flagged
                ]
                
                embed.add_field(
                    name="Flagged Categories",
                    value=", ".join(flagged_categories) if flagged_categories else "General violation",
                    inline=False
                )
                
                embed.add_field(
                    name="Recommendation",
                    value="Please review and modify the content before sharing.",
                    inline=False
                )
                
            else:
                # Content is clean
                embed = discord.Embed(
                    title="✅ Content Approved",
                    description="The text appears to comply with community guidelines.",
                    color=0x51cf66
                )
                
            embed.set_footer(
                text=f"Checked by {interaction.user.display_name}",
                icon_url=interaction.user.avatar.url if interaction.user.avatar else None
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in moderate command: {e}")
            await interaction.followup.send(
                "❌ Failed to check content. Please try again later.",
                ephemeral=True
            )

    @app_commands.command(name="filter_toggle", description="Toggle automatic content filtering (Admin only)")
    @app_commands.default_permissions(administrator=True)
    async def filter_toggle(self, interaction: discord.Interaction):
        """Toggle auto-moderation for the server"""
        try:
            guild_id = interaction.guild_id or 0
            current_setting = self.auto_moderation.get(guild_id, False)
            new_setting = not current_setting
            self.auto_moderation[guild_id] = new_setting
            
            status = "enabled" if new_setting else "disabled"
            color = 0x51cf66 if new_setting else 0xff6b6b
            icon = "✅" if new_setting else "❌"
            
            embed = discord.Embed(
                title=f"{icon} Auto-Moderation {status.title()}",
                description=f"Automatic content filtering has been **{status}** for this server.",
                color=color
            )
            
            if new_setting:
                embed.add_field(
                    name="What happens now?",
                    value=(
                        "• Messages will be automatically scanned\n"
                        "• Flagged content will be deleted\n"
                        "• Users will receive warnings\n"
                        "• Moderators will be notified"
                    ),
                    inline=False
                )
            else:
                embed.add_field(
                    name="What happens now?",
                    value="Messages will no longer be automatically moderated.",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
            logger.info(f"Auto-moderation {status} for guild {guild_id} by {interaction.user}")
            
        except Exception as e:
            logger.error(f"Error toggling filter: {e}")
            await interaction.response.send_message(
                "❌ Failed to toggle auto-moderation. Please try again.",
                ephemeral=True
            )

    async def auto_moderate_message(self, message: discord.Message) -> bool:
        """
        Auto-moderate a message if enabled for the guild
        Returns True if message was moderated, False otherwise
        """
        if not message.guild or not self.auto_moderation.get(message.guild.id, False):
            return False
            
        if message.author.bot:
            return False
            
        try:
            # Check message content
            moderation_result = await self.gemini_client.moderate_content(message.content)
            
            if moderation_result["flagged"]:
                # Delete the message
                await message.delete()
                
                # Get flagged categories
                flagged_categories = [
                    category for category, flagged in moderation_result["categories"].items()
                    if flagged
                ]
                
                # Send warning to user
                embed = discord.Embed(
                    title="⚠️ Message Removed",
                    description="Your message was automatically removed for violating community guidelines.",
                    color=0xff6b6b
                )
                
                if flagged_categories:
                    embed.add_field(
                        name="Reason",
                        value=f"Flagged for: {', '.join(flagged_categories)}",
                        inline=False
                    )
                
                embed.add_field(
                    name="What to do?",
                    value="Please review the server rules and modify your message before reposting.",
                    inline=False
                )
                
                try:
                    await message.author.send(embed=embed)
                except discord.Forbidden:
                    # If DM fails, send in channel with mention
                    if hasattr(message.channel, 'send'):
                        embed.set_footer(text=f"@{message.author.display_name}, please check your DMs")
                        temp_msg = await message.channel.send(embed=embed)
                        # Delete after 10 seconds
                        await temp_msg.delete(delay=10)
                
                # Log to moderation channel if exists
                mod_channel = discord.utils.get(message.guild.channels, name="mod-log") if message.guild else None
                if mod_channel and hasattr(mod_channel, 'send'):
                    log_embed = discord.Embed(
                        title="🤖 Auto-Moderation Action",
                        description=f"Message from {message.author.mention} was automatically removed.",
                        color=0xff9800
                    )
                    channel_mention = getattr(message.channel, 'mention', '#unknown')
                    log_embed.add_field(
                        name="Channel",
                        value=channel_mention,
                        inline=True
                    )
                    log_embed.add_field(
                        name="Flagged Categories",
                        value=", ".join(flagged_categories) if flagged_categories else "General violation",
                        inline=True
                    )
                    log_embed.add_field(
                        name="Original Message",
                        value=message.content[:500] + ("..." if len(message.content) > 500 else ""),
                        inline=False
                    )
                    await mod_channel.send(embed=log_embed)
                
                logger.info(f"Auto-moderated message from {message.author} in {message.guild}")
                return True
                
        except Exception as e:
            logger.error(f"Error in auto-moderation: {e}")
            
        return False
