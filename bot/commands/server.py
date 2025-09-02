import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ServerCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Store welcome message settings per guild
        self.welcome_settings = {}
        
    @app_commands.command(name="server_info", description="Get information about this server")
    async def server_info(self, interaction: discord.Interaction):
        """Display server information"""
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    "❌ This command can only be used in a server.",
                    ephemeral=True
                )
                return
            
            # Calculate server stats
            total_members = guild.member_count
            online_members = len([m for m in guild.members if m.status != discord.Status.offline])
            text_channels = len(guild.text_channels)
            voice_channels = len(guild.voice_channels)
            roles = len(guild.roles)
            
            # Create embed
            embed = discord.Embed(
                title=f"📊 {guild.name} Server Info",
                color=0x7289da,
                timestamp=datetime.utcnow()
            )
            
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
            
            # Basic info
            embed.add_field(
                name="👑 Owner",
                value=guild.owner.mention if guild.owner else "Unknown",
                inline=True
            )
            embed.add_field(
                name="🗓️ Created",
                value=guild.created_at.strftime("%B %d, %Y"),
                inline=True
            )
            embed.add_field(
                name="🆔 Server ID",
                value=guild.id,
                inline=True
            )
            
            # Member stats
            embed.add_field(
                name="👥 Members",
                value=f"Total: {total_members}\nOnline: {online_members}",
                inline=True
            )
            
            # Channel stats
            embed.add_field(
                name="📝 Channels",
                value=f"Text: {text_channels}\nVoice: {voice_channels}",
                inline=True
            )
            
            # Role count
            embed.add_field(
                name="🏷️ Roles",
                value=roles,
                inline=True
            )
            
            # Features
            features = guild.features
            if features:
                feature_list = [feature.replace('_', ' ').title() for feature in features[:5]]
                if len(features) > 5:
                    feature_list.append(f"and {len(features) - 5} more...")
                embed.add_field(
                    name="✨ Server Features",
                    value="\n".join(feature_list) if feature_list else "None",
                    inline=False
                )
            
            embed.set_footer(
                text=f"Requested by {interaction.user.display_name}",
                icon_url=interaction.user.avatar.url if interaction.user.avatar else None
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in server_info command: {e}")
            await interaction.response.send_message(
                "❌ Failed to retrieve server information.",
                ephemeral=True
            )

    @app_commands.command(name="welcome_setup", description="Configure welcome messages for new members (Admin only)")
    @app_commands.describe(
        channel="Channel to send welcome messages",
        message="Custom welcome message (use {user} for mention, {server} for server name)"
    )
    @app_commands.default_permissions(administrator=True)
    async def welcome_setup(
        self, 
        interaction: discord.Interaction, 
        channel: discord.TextChannel,
        message: str = "Welcome {user} to {server}! 🎉"
    ):
        """Setup welcome messages for new members"""
        try:
            guild_id = interaction.guild_id
            
            # Store welcome settings
            self.welcome_settings[guild_id] = {
                'channel_id': channel.id,
                'message': message,
                'enabled': True
            }
            
            embed = discord.Embed(
                title="✅ Welcome Messages Configured",
                description=f"Welcome messages will now be sent to {channel.mention}",
                color=0x51cf66
            )
            
            # Show preview
            preview_message = message.replace('{user}', interaction.user.mention)
            preview_message = preview_message.replace('{server}', interaction.guild.name if interaction.guild else 'Server')
            
            embed.add_field(
                name="📝 Message Preview",
                value=preview_message,
                inline=False
            )
            
            embed.add_field(
                name="💡 Variables",
                value=(
                    "`{user}` - Mentions the new member\n"
                    "`{server}` - Shows the server name\n"
                    "`{count}` - Shows member count"
                ),
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            logger.info(f"Welcome setup configured for guild {guild_id}")
            
        except Exception as e:
            logger.error(f"Error in welcome_setup command: {e}")
            await interaction.response.send_message(
                "❌ Failed to configure welcome messages.",
                ephemeral=True
            )

    @app_commands.command(name="welcome_toggle", description="Enable/disable welcome messages (Admin only)")
    @app_commands.default_permissions(administrator=True)
    async def welcome_toggle(self, interaction: discord.Interaction):
        """Toggle welcome messages on/off"""
        try:
            guild_id = interaction.guild_id
            
            if guild_id not in self.welcome_settings:
                await interaction.response.send_message(
                    "❌ Welcome messages are not configured. Use `/welcome_setup` first.",
                    ephemeral=True
                )
                return
            
            current_status = self.welcome_settings[guild_id].get('enabled', False)
            new_status = not current_status
            self.welcome_settings[guild_id]['enabled'] = new_status
            
            status_text = "enabled" if new_status else "disabled"
            color = 0x51cf66 if new_status else 0xff6b6b
            icon = "✅" if new_status else "❌"
            
            embed = discord.Embed(
                title=f"{icon} Welcome Messages {status_text.title()}",
                description=f"Welcome messages have been **{status_text}**.",
                color=color
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error toggling welcome messages: {e}")
            await interaction.response.send_message(
                "❌ Failed to toggle welcome messages.",
                ephemeral=True
            )

    async def send_welcome_message(self, member: discord.Member):
        """Send welcome message when a new member joins"""
        try:
            guild_id = member.guild.id
            settings = self.welcome_settings.get(guild_id)
            
            if not settings or not settings.get('enabled', False):
                return
            
            channel = self.bot.get_channel(settings['channel_id'])
            if not channel:
                return
            
            # Format welcome message
            message = settings['message']
            message = message.replace('{user}', member.mention)
            message = message.replace('{server}', member.guild.name)
            message = message.replace('{count}', str(member.guild.member_count))
            
            # Create welcome embed
            embed = discord.Embed(
                title="🎉 Welcome!",
                description=message,
                color=0x00ff88
            )
            
            if member.avatar:
                embed.set_thumbnail(url=member.avatar.url)
            
            embed.add_field(
                name="📅 Account Created",
                value=member.created_at.strftime("%B %d, %Y"),
                inline=True
            )
            
            embed.add_field(
                name="👥 Member #",
                value=member.guild.member_count,
                inline=True
            )
            
            embed.set_footer(
                text=f"Welcome to {member.guild.name}!",
                icon_url=member.guild.icon.url if member.guild.icon else None
            )
            
            await channel.send(embed=embed)
            logger.info(f"Sent welcome message for {member} in {member.guild}")
            
        except Exception as e:
            logger.error(f"Error sending welcome message: {e}")
