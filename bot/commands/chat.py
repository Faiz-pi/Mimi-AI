import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional

from bot.utils.gemini_client import GeminiClient
from bot.utils.conversation_memory import ConversationMemory
from bot.utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

class ChatCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.gemini_client = GeminiClient()
        self.conversation_memory = ConversationMemory()
        self.rate_limiter = RateLimiter()
        
    @app_commands.command(name="chat", description="Have a conversation with the AI")
    @app_commands.describe(
        message="Your message to the AI",
        temperature="Creativity level (0.0-2.0, default: 0.7)",
        max_tokens="Maximum response length (50-500, default: 200)"
    )
    async def chat(
        self, 
        interaction: discord.Interaction, 
        message: str,
        temperature: Optional[float] = 0.7,
        max_tokens: Optional[int] = 200
    ):
        """Main chat command for AI conversations"""
        await interaction.response.defer(thinking=True)
        
        try:
            # Check rate limits
            if not self.rate_limiter.check_rate_limit(interaction.user.id, "chat"):
                await interaction.followup.send(
                    "⏰ You're sending messages too quickly! Please wait a moment.",
                    ephemeral=True
                )
                return
            
            # Validate parameters
            temperature = max(0.0, min(2.0, temperature or 0.7))
            max_tokens = max(50, min(500, max_tokens or 200))
            
            # Get conversation context
            guild_id = interaction.guild_id or 0
            context = self.conversation_memory.get_context(
                interaction.user.id, 
                guild_id
            )
            
            # Generate AI response
            response = await self.gemini_client.generate_chat_response(
                message=message,
                context=context,
                temperature=temperature,
                max_tokens=max_tokens,
                user_id=interaction.user.id
            )
            
            # Store conversation in memory
            self.conversation_memory.add_message(
                interaction.user.id,
                guild_id,
                "user",
                message
            )
            self.conversation_memory.add_message(
                interaction.user.id,
                guild_id,
                "assistant",
                response
            )
            
            # Create embed for response
            embed = discord.Embed(
                title="🤖 Mimi's Response",
                description=response,
                color=0x00ff88
            )
            embed.set_footer(
                text=f"Requested by {interaction.user.display_name}",
                icon_url=interaction.user.avatar.url if interaction.user.avatar else None
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in chat command: {e}")
            error_message = str(e) if "OpenAI" in str(e) or "API" in str(e) else "❌ Sorry, I encountered an error while processing your request. Please try again later."
            await interaction.followup.send(
                error_message,
                ephemeral=True
            )

    @app_commands.command(name="ask", description="Ask the AI a question with context about the server")
    @app_commands.describe(question="Your question about the server or general topic")
    async def ask(self, interaction: discord.Interaction, question: str):
        """Ask command with server context"""
        await interaction.response.defer(thinking=True)
        
        try:
            # Check rate limits
            if not self.rate_limiter.check_rate_limit(interaction.user.id, "ask"):
                await interaction.followup.send(
                    "⏰ You're asking questions too quickly! Please wait a moment.",
                    ephemeral=True
                )
                return
            
            # Build server context
            guild_name = interaction.guild.name if interaction.guild else "DM"
            member_count = interaction.guild.member_count if interaction.guild else 0
            channel_name = getattr(interaction.channel, 'name', 'DM')
            server_context = f"""
            Server: {guild_name}
            Members: {member_count}
            Channel: #{channel_name}
            User: {interaction.user.display_name}
            """
            
            # Generate response with server context
            response = await self.gemini_client.generate_contextual_response(
                question=question,
                server_context=server_context,
                user_id=interaction.user.id
            )
            
            # Create embed
            embed = discord.Embed(
                title="🔍 Mimi's Answer",
                description=response,
                color=0x0099ff
            )
            embed.add_field(
                name="Question",
                value=question[:100] + ("..." if len(question) > 100 else ""),
                inline=False
            )
            embed.set_footer(
                text=f"Asked by {interaction.user.display_name}",
                icon_url=interaction.user.avatar.url if interaction.user.avatar else None
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in ask command: {e}")
            error_message = str(e) if "OpenAI" in str(e) or "API" in str(e) else "❌ Sorry, I couldn't process your question. Please try again later."
            await interaction.followup.send(
                error_message,
                ephemeral=True
            )

    @app_commands.command(name="clear_memory", description="Clear your conversation history with the AI")
    async def clear_memory(self, interaction: discord.Interaction):
        """Clear user's conversation memory"""
        try:
            guild_id = interaction.guild_id or 0
            self.conversation_memory.clear_user_memory(
                interaction.user.id, 
                guild_id
            )
            
            embed = discord.Embed(
                title="🧹 Memory Cleared",
                description="Your conversation history has been cleared. I'll start fresh!",
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error clearing memory: {e}")
            await interaction.response.send_message(
                "❌ Failed to clear memory. Please try again.",
                ephemeral=True
            )

    @app_commands.command(name="help", description="Get help with AI bot commands")
    async def help(self, interaction: discord.Interaction):
        """Help command"""
        embed = discord.Embed(
            title="🤖 AI Bot Help",
            description="Here are all the commands you can use:",
            color=0x9932cc
        )
        
        embed.add_field(
            name="💬 Chat Commands",
            value=(
                "`/chat <message>` - Chat with the AI\n"
                "`/ask <question>` - Ask a question with server context\n"
                "`/clear_memory` - Clear your conversation history"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🛡️ Moderation Commands",
            value=(
                "`/moderate <text>` - Check if text violates guidelines\n"
                "`/filter_toggle` - Toggle auto-moderation (Admin only)"
            ),
            inline=False
        )
        
        embed.add_field(
            name="⚙️ Server Commands",
            value=(
                "`/welcome_setup` - Configure welcome messages (Admin only)\n"
                "`/server_info` - Get server information"
            ),
            inline=False
        )
        
        embed.set_footer(text="Use commands responsibly and follow server rules!")
        
        await interaction.response.send_message(embed=embed)
