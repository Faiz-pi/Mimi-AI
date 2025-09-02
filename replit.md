# AI Discord Bot

## Overview

This is a Discord AI bot built with Python that integrates OpenAI's GPT models to provide conversational AI capabilities, content moderation, and server management features. The bot uses discord.py for Discord API interaction and implements a modular architecture with separate command groups, event handlers, and utility services.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Core Bot Framework
- **Discord.py Library**: Uses discord.py with application commands (slash commands) for modern Discord interactions
- **Command Structure**: Modular cog-based architecture separating chat commands, moderation commands, and server management
- **Event Handling**: Dedicated event handlers for message processing and member management
- **Configuration Management**: Environment-based configuration system with comprehensive settings validation

### AI Integration
- **OpenAI Client**: Asynchronous OpenAI API client with built-in rate limiting and error handling
- **Conversation Memory**: In-memory conversation history system that maintains context per user per guild with configurable retention
- **Content Moderation**: Integration with OpenAI's moderation API for automatic and manual content filtering

### Rate Limiting and Performance
- **Multi-tier Rate Limiting**: Separate rate limits for different command types (chat, moderation, global)
- **Request Throttling**: Built-in request queuing and timing controls to respect API limits
- **Memory Management**: Automatic cleanup of conversation history based on time and message count limits

### Bot Permissions and Intents
- **Message Content Intent**: Required for processing message content and mentions
- **Members Intent**: Enables member join/leave event handling and user information access
- **Guilds Intent**: Provides access to server information and channel management

### Logging and Monitoring
- **Structured Logging**: File and console logging with configurable levels
- **Event Tracking**: Comprehensive logging of bot operations, errors, and user interactions
- **Debug Mode**: Development-specific features and enhanced logging capabilities

## External Dependencies

### Required APIs
- **Discord Bot Token**: Primary Discord application authentication
- **OpenAI API Key**: GPT model access for chat responses and content moderation

### Python Libraries
- **discord.py**: Discord API wrapper and bot framework
- **openai**: Official OpenAI Python client for GPT and moderation APIs
- **python-dotenv**: Environment variable management
- **asyncio**: Asynchronous programming support

### Optional Integrations
- **Moderation Logging**: Configurable mod-log channels for automated moderation alerts
- **Welcome Messages**: Automated member greeting system with customizable settings
- **Development Guild**: Test server configuration for development and debugging

### Configuration Requirements
- Environment variables for API keys, rate limits, and feature toggles
- Guild-specific settings for moderation and welcome message preferences
- Logging configuration with file output and rotation capabilities