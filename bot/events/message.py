import discord
from discord.ext import commands
import logging
import re

logger = logging.getLogger(__name__)

class MessageEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle incoming messages"""
        # Ignore bot messages
        if message.author.bot:
            return
            
        # Ignore DMs
        if not message.guild:
            return
            
        try:
            # Auto-moderation check
            moderation_cog = self.bot.get_cog('ModerationCommands')
            if moderation_cog:
                was_moderated = await moderation_cog.auto_moderate_message(message)
                if was_moderated:
                    return
            
            # Check if bot is mentioned
            if self.bot.user in message.mentions:
                await self._handle_mention(message)
                
            # Process commands normally
            await self.bot.process_commands(message)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def _handle_mention(self, message: discord.Message):
        """Handle when the bot is mentioned"""
        try:
            # Remove the mention from the message
            content = message.content
            mention_pattern = f'<@!?{self.bot.user.id}>'
            content = re.sub(mention_pattern, '', content).strip()
            
            if not content:
                # Just mentioned without text
                embed = discord.Embed(
                    title="👋 Hello!",
                    description=(
                        f"Hi {message.author.mention}! I'm an AI-powered bot.\n"
                        "Use `/help` to see what I can do, or `/chat` to start a conversation!"
                    ),
                    color=0x00ff88
                )
                await message.reply(embed=embed)
                return
            
            # Get chat commands cog for AI response
            chat_cog = self.bot.get_cog('ChatCommands')
            if chat_cog:
                try:
                    # Generate AI response to the mention
                    guild_id = message.guild.id if message.guild else 0
                    context = chat_cog.conversation_memory.get_context(
                        message.author.id, 
                        guild_id
                    )
                    
                    response = await chat_cog.gemini_client.generate_chat_response(
                        message=content,
                        context=context,
                        temperature=0.7,
                        max_tokens=200,
                        user_id=message.author.id
                    )
                    
                    # Store in conversation memory
                    chat_cog.conversation_memory.add_message(
                        message.author.id,
                        guild_id,
                        "user",
                        content
                    )
                    chat_cog.conversation_memory.add_message(
                        message.author.id,
                        guild_id,
                        "assistant",
                        response
                    )
                    
                    # Reply with AI response
                    embed = discord.Embed(
                        description=response,
                        color=0x00ff88
                    )
                    embed.set_author(
                        name="Mimi's Response",
                        icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
                    )
                    
                    await message.reply(embed=embed)
                    
                except Exception as e:
                    logger.error(f"Error generating AI response to mention: {e}")
                    error_msg = "Sorry, I'm having trouble right now. Try using `/chat` instead!"
                    if "quota" in str(e).lower() or "credits" in str(e).lower():
                        error_msg = "⚠️ My OpenAI credits are low. Please ask the server admin to add credits to the OpenAI account."
                    await message.reply(error_msg)
            
        except Exception as e:
            logger.error(f"Error handling mention: {e}")

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """Log message deletions"""
        if message.author.bot:
            return
            
        # Log to mod channel if exists
        try:
            if not message.guild:
                return
            mod_channel = discord.utils.get(message.guild.channels, name="mod-log")
            if mod_channel:
                embed = discord.Embed(
                    title="🗑️ Message Deleted",
                    color=0xff6b6b,
                    timestamp=message.created_at
                )
                
                embed.add_field(
                    name="Author",
                    value=message.author.mention,
                    inline=True
                )
                
                embed.add_field(
                    name="Channel",
                    value=message.channel.mention,
                    inline=True
                )
                
                if message.content:
                    embed.add_field(
                        name="Content",
                        value=message.content[:500] + ("..." if len(message.content) > 500 else ""),
                        inline=False
                    )
                
                await mod_channel.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Error logging message deletion: {e}")

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """Log message edits"""
        if before.author.bot or before.content == after.content:
            return
            
        try:
            if not before.guild:
                return
            mod_channel = discord.utils.get(before.guild.channels, name="mod-log")
            if mod_channel:
                embed = discord.Embed(
                    title="✏️ Message Edited",
                    color=0xffa500,
                    timestamp=after.edited_at
                )
                
                embed.add_field(
                    name="Author",
                    value=before.author.mention,
                    inline=True
                )
                
                embed.add_field(
                    name="Channel",
                    value=before.channel.mention,
                    inline=True
                )
                
                embed.add_field(
                    name="Before",
                    value=before.content[:500] + ("..." if len(before.content) > 500 else ""),
                    inline=False
                )
                
                embed.add_field(
                    name="After",
                    value=after.content[:500] + ("..." if len(after.content) > 500 else ""),
                    inline=False
                )
                
                await mod_channel.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Error logging message edit: {e}")
