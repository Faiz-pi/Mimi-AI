import os
from typing import Optional

class BotConfig:
    """Configuration settings for the Discord AI Bot"""
    
    # Discord Configuration
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
    COMMAND_PREFIX: str = os.getenv("COMMAND_PREFIX", "!")
    
    # AI Configuration (Gemini)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    GEMINI_MAX_TOKENS: int = int(os.getenv("GEMINI_MAX_TOKENS", "500"))
    GEMINI_TEMPERATURE: float = float(os.getenv("GEMINI_TEMPERATURE", "0.7"))
    
    # Keep OpenAI for backwards compatibility (optional)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Bot Behavior Configuration
    MAX_CONVERSATION_HISTORY: int = int(os.getenv("MAX_CONVERSATION_HISTORY", "20"))
    CONVERSATION_MEMORY_HOURS: int = int(os.getenv("CONVERSATION_MEMORY_HOURS", "24"))
    
    # Rate Limiting Configuration
    CHAT_RATE_LIMIT: int = int(os.getenv("CHAT_RATE_LIMIT", "10"))  # per minute
    ASK_RATE_LIMIT: int = int(os.getenv("ASK_RATE_LIMIT", "5"))     # per minute
    MODERATE_RATE_LIMIT: int = int(os.getenv("MODERATE_RATE_LIMIT", "3"))  # per minute
    GLOBAL_RATE_LIMIT: int = int(os.getenv("GLOBAL_RATE_LIMIT", "20"))    # per minute
    
    # Moderation Configuration
    AUTO_MODERATION_ENABLED: bool = os.getenv("AUTO_MODERATION_ENABLED", "false").lower() == "true"
    MODERATION_LOG_CHANNEL: str = os.getenv("MODERATION_LOG_CHANNEL", "mod-log")
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    LOG_FILE: str = os.getenv("LOG_FILE", "bot.log")
    
    # Development Configuration
    DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "false").lower() == "true"
    DEVELOPMENT_GUILD_ID: Optional[int] = int(os.getenv("DEVELOPMENT_GUILD_ID", "0")) if os.getenv("DEVELOPMENT_GUILD_ID") else None
    
    # Feature Flags
    ENABLE_WELCOME_MESSAGES: bool = os.getenv("ENABLE_WELCOME_MESSAGES", "true").lower() == "true"
    ENABLE_MESSAGE_LOGGING: bool = os.getenv("ENABLE_MESSAGE_LOGGING", "true").lower() == "true"
    ENABLE_CONVERSATION_MEMORY: bool = os.getenv("ENABLE_CONVERSATION_MEMORY", "true").lower() == "true"
    
    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    @classmethod
    def validate_config(cls) -> bool:
        """
        Validate that required configuration is present
        
        Returns:
            True if configuration is valid, False otherwise
        """
        required_vars = [
            ("DISCORD_TOKEN", cls.DISCORD_TOKEN),
            ("GEMINI_API_KEY", cls.GEMINI_API_KEY)
        ]
        
        missing_vars = []
        for var_name, var_value in required_vars:
            if not var_value:
                missing_vars.append(var_name)
        
        if missing_vars:
            print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
            return False
        
        return True
    
    @classmethod
    def get_config_summary(cls) -> str:
        """
        Get a summary of current configuration (without sensitive data)
        
        Returns:
            Configuration summary string
        """
        return f"""
🤖 Discord AI Bot Configuration Summary:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Discord Settings:
  • Token: {'✓ Set' if cls.DISCORD_TOKEN else '❌ Missing'}
  • Command Prefix: {cls.COMMAND_PREFIX}

Gemini AI Settings:
  • API Key: {'✓ Set' if cls.GEMINI_API_KEY else '❌ Missing'}
  • Model: {cls.GEMINI_MODEL}
  • Max Tokens: {cls.GEMINI_MAX_TOKENS}
  • Temperature: {cls.GEMINI_TEMPERATURE}

Bot Behavior:
  • Conversation History: {cls.MAX_CONVERSATION_HISTORY} messages
  • Memory Duration: {cls.CONVERSATION_MEMORY_HOURS} hours
  • Auto Moderation: {'Enabled' if cls.AUTO_MODERATION_ENABLED else 'Disabled'}

Rate Limits (per minute):
  • Chat Commands: {cls.CHAT_RATE_LIMIT}
  • Ask Commands: {cls.ASK_RATE_LIMIT}
  • Moderation: {cls.MODERATE_RATE_LIMIT}
  • Global: {cls.GLOBAL_RATE_LIMIT}

Features:
  • Welcome Messages: {'✓' if cls.ENABLE_WELCOME_MESSAGES else '❌'}
  • Message Logging: {'✓' if cls.ENABLE_MESSAGE_LOGGING else '❌'}
  • Conversation Memory: {'✓' if cls.ENABLE_CONVERSATION_MEMORY else '❌'}

Development:
  • Debug Mode: {'✓' if cls.DEBUG_MODE else '❌'}
  • Dev Guild ID: {cls.DEVELOPMENT_GUILD_ID or 'Not Set'}
  • Log Level: {cls.LOG_LEVEL}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """.strip()

# Configuration validation on import
if __name__ == "__main__":
    if BotConfig.validate_config():
        print("✅ Configuration is valid!")
        print(BotConfig.get_config_summary())
    else:
        print("❌ Configuration validation failed!")
        exit(1)
