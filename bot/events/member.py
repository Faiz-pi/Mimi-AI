import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

class MemberEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Handle new member joins"""
        try:
            logger.info(f"New member joined: {member} in {member.guild}")
            
            # Send welcome message if configured
            server_cog = self.bot.get_cog('ServerCommands')
            if server_cog:
                await server_cog.send_welcome_message(member)
            
            # Log to mod channel
            mod_channel = discord.utils.get(member.guild.channels, name="mod-log")
            if mod_channel:
                embed = discord.Embed(
                    title="👋 Member Joined",
                    description=f"{member.mention} has joined the server!",
                    color=0x51cf66,
                    timestamp=member.joined_at
                )
                
                if member.avatar:
                    embed.set_thumbnail(url=member.avatar.url)
                
                embed.add_field(
                    name="👤 User",
                    value=f"{member.display_name}\n({member})",
                    inline=True
                )
                
                embed.add_field(
                    name="🆔 User ID",
                    value=member.id,
                    inline=True
                )
                
                embed.add_field(
                    name="📅 Account Created",
                    value=member.created_at.strftime("%B %d, %Y"),
                    inline=True
                )
                
                embed.add_field(
                    name="👥 Member Count",
                    value=member.guild.member_count,
                    inline=True
                )
                
                # Check account age (potential raid detection)
                if member.joined_at:
                    account_age = (member.joined_at - member.created_at).days
                else:
                    account_age = 0
                if account_age < 7:
                    embed.add_field(
                        name="⚠️ New Account",
                        value=f"Account is only {account_age} days old",
                        inline=False
                    )
                
                await mod_channel.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Error handling member join: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Handle member leaves/kicks/bans"""
        try:
            logger.info(f"Member left: {member} from {member.guild}")
            
            # Log to mod channel
            mod_channel = discord.utils.get(member.guild.channels, name="mod-log")
            if mod_channel:
                embed = discord.Embed(
                    title="👋 Member Left",
                    description=f"{member.mention} has left the server.",
                    color=0xff6b6b
                )
                
                if member.avatar:
                    embed.set_thumbnail(url=member.avatar.url)
                
                embed.add_field(
                    name="👤 User",
                    value=f"{member.display_name}\n({member})",
                    inline=True
                )
                
                embed.add_field(
                    name="🆔 User ID",
                    value=member.id,
                    inline=True
                )
                
                # Calculate how long they were in the server
                if member.joined_at:
                    time_in_server = (discord.utils.utcnow() - member.joined_at).days
                    embed.add_field(
                        name="⏱️ Time in Server",
                        value=f"{time_in_server} days",
                        inline=True
                    )
                
                embed.add_field(
                    name="👥 Member Count",
                    value=member.guild.member_count,
                    inline=True
                )
                
                await mod_channel.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Error handling member leave: {e}")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Handle member updates (roles, nickname, etc.)"""
        try:
            # Check for role changes
            if before.roles != after.roles:
                added_roles = set(after.roles) - set(before.roles)
                removed_roles = set(before.roles) - set(after.roles)
                
                if added_roles or removed_roles:
                    mod_channel = discord.utils.get(after.guild.channels, name="mod-log")
                    if mod_channel:
                        embed = discord.Embed(
                            title="🏷️ Member Roles Updated",
                            color=0x3498db
                        )
                        
                        embed.add_field(
                            name="👤 Member",
                            value=after.mention,
                            inline=True
                        )
                        
                        if added_roles:
                            role_names = [role.name for role in added_roles if role.name != "@everyone"]
                            if role_names:
                                embed.add_field(
                                    name="➕ Added Roles",
                                    value=", ".join(role_names),
                                    inline=False
                                )
                        
                        if removed_roles:
                            role_names = [role.name for role in removed_roles if role.name != "@everyone"]
                            if role_names:
                                embed.add_field(
                                    name="➖ Removed Roles",
                                    value=", ".join(role_names),
                                    inline=False
                                )
                        
                        await mod_channel.send(embed=embed)
            
            # Check for nickname changes
            if before.nick != after.nick:
                mod_channel = discord.utils.get(after.guild.channels, name="mod-log")
                if mod_channel:
                    embed = discord.Embed(
                        title="📝 Nickname Changed",
                        color=0x9b59b6
                    )
                    
                    embed.add_field(
                        name="👤 Member",
                        value=after.mention,
                        inline=True
                    )
                    
                    embed.add_field(
                        name="Before",
                        value=before.nick or before.name,
                        inline=True
                    )
                    
                    embed.add_field(
                        name="After",
                        value=after.nick or after.name,
                        inline=True
                    )
                    
                    await mod_channel.send(embed=embed)
                    
        except Exception as e:
            logger.error(f"Error handling member update: {e}")

    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User):
        """Handle user updates (username, avatar, etc.)"""
        try:
            # Only log for users in guilds the bot is in
            mutual_guilds = [guild for guild in self.bot.guilds if guild.get_member(after.id)]
            
            if not mutual_guilds:
                return
            
            changes = []
            
            # Check username change
            if before.name != after.name:
                changes.append(f"Username: `{before.name}` → `{after.name}`")
            
            # Check discriminator change (if applicable)
            if hasattr(before, 'discriminator') and hasattr(after, 'discriminator'):
                if before.discriminator != after.discriminator:
                    changes.append(f"Discriminator: `#{before.discriminator}` → `#{after.discriminator}`")
            
            # Check avatar change
            if before.avatar != after.avatar:
                changes.append("Avatar changed")
            
            if changes:
                # Log to mod channels in mutual guilds
                for guild in mutual_guilds:
                    mod_channel = discord.utils.get(guild.channels, name="mod-log")
                    if mod_channel:
                        embed = discord.Embed(
                            title="👤 User Profile Updated",
                            description=f"{after.mention} updated their profile:",
                            color=0xe67e22
                        )
                        
                        embed.add_field(
                            name="Changes",
                            value="\n".join(changes),
                            inline=False
                        )
                        
                        if after.avatar:
                            embed.set_thumbnail(url=after.avatar.url)
                        
                        await mod_channel.send(embed=embed)
                        
        except Exception as e:
            logger.error(f"Error handling user update: {e}")
