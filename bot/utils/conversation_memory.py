import json
import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class ConversationMemory:
    def __init__(self, max_messages_per_user: int = 20, memory_duration_hours: int = 24):
        """
        Initialize conversation memory system
        
        Args:
            max_messages_per_user: Maximum messages to remember per user
            memory_duration_hours: How long to keep messages in memory
        """
        self.max_messages_per_user = max_messages_per_user
        self.memory_duration = timedelta(hours=memory_duration_hours)
        
        # Structure: {user_id: {guild_id: deque of messages}}
        self.conversations = defaultdict(lambda: defaultdict(lambda: deque(maxlen=max_messages_per_user)))
        
        # Track message timestamps for cleanup
        self.message_timestamps = defaultdict(lambda: defaultdict(list))
        
    def add_message(self, user_id: int, guild_id: int, role: str, content: str):
        """
        Add a message to conversation memory
        
        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID
            role: 'user' or 'assistant'
            content: Message content
        """
        try:
            timestamp = datetime.utcnow()
            
            message = {
                "role": role,
                "content": content,
                "timestamp": timestamp.isoformat()
            }
            
            # Add to conversation
            self.conversations[user_id][guild_id].append(message)
            
            # Track timestamp for cleanup
            self.message_timestamps[user_id][guild_id].append(timestamp)
            
            # Clean old messages
            self._cleanup_old_messages(user_id, guild_id)
            
        except Exception as e:
            logger.error(f"Error adding message to memory: {e}")

    def get_context(self, user_id: int, guild_id: int, max_messages: int = 10) -> List[Dict[str, str]]:
        """
        Get conversation context for a user in a guild
        
        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID
            max_messages: Maximum number of messages to return
            
        Returns:
            List of message dictionaries
        """
        try:
            # Clean old messages first
            self._cleanup_old_messages(user_id, guild_id)
            
            messages = list(self.conversations[user_id][guild_id])
            
            # Return last N messages, but remove timestamps for OpenAI
            context = []
            for message in messages[-max_messages:]:
                context.append({
                    "role": message["role"],
                    "content": message["content"]
                })
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting context: {e}")
            return []

    def clear_user_memory(self, user_id: int, guild_id: int = None):
        """
        Clear conversation memory for a user
        
        Args:
            user_id: Discord user ID
            guild_id: Optional guild ID. If None, clears all guilds
        """
        try:
            if guild_id:
                # Clear specific guild
                if user_id in self.conversations:
                    self.conversations[user_id][guild_id].clear()
                    self.message_timestamps[user_id][guild_id].clear()
            else:
                # Clear all guilds for user
                if user_id in self.conversations:
                    self.conversations[user_id].clear()
                    self.message_timestamps[user_id].clear()
                    
        except Exception as e:
            logger.error(f"Error clearing user memory: {e}")

    def _cleanup_old_messages(self, user_id: int, guild_id: int):
        """
        Remove messages older than memory_duration
        """
        try:
            now = datetime.utcnow()
            cutoff_time = now - self.memory_duration
            
            # Get timestamps for this user/guild
            timestamps = self.message_timestamps[user_id][guild_id]
            messages = self.conversations[user_id][guild_id]
            
            # Find messages to remove
            remove_count = 0
            for timestamp in timestamps:
                if timestamp < cutoff_time:
                    remove_count += 1
                else:
                    break
            
            # Remove old messages and timestamps
            if remove_count > 0:
                # Remove from left (oldest first)
                for _ in range(remove_count):
                    if messages:
                        messages.popleft()
                    if timestamps:
                        timestamps.pop(0)
                        
        except Exception as e:
            logger.error(f"Error cleaning up old messages: {e}")

    def get_user_stats(self, user_id: int, guild_id: int) -> Dict[str, Any]:
        """
        Get statistics about a user's conversation
        """
        try:
            messages = list(self.conversations[user_id][guild_id])
            
            if not messages:
                return {
                    "total_messages": 0,
                    "user_messages": 0,
                    "ai_messages": 0,
                    "oldest_message": None,
                    "newest_message": None
                }
            
            user_messages = len([m for m in messages if m["role"] == "user"])
            ai_messages = len([m for m in messages if m["role"] == "assistant"])
            
            timestamps = [datetime.fromisoformat(m["timestamp"]) for m in messages]
            
            return {
                "total_messages": len(messages),
                "user_messages": user_messages,
                "ai_messages": ai_messages,
                "oldest_message": min(timestamps).isoformat(),
                "newest_message": max(timestamps).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {}

    def get_memory_usage(self) -> Dict[str, Any]:
        """
        Get overall memory usage statistics
        """
        try:
            total_users = len(self.conversations)
            total_guilds = sum(len(guilds) for guilds in self.conversations.values())
            total_messages = sum(
                len(messages) 
                for user_guilds in self.conversations.values()
                for messages in user_guilds.values()
            )
            
            return {
                "total_users": total_users,
                "total_guilds": total_guilds,
                "total_messages": total_messages,
                "max_messages_per_user": self.max_messages_per_user,
                "memory_duration_hours": self.memory_duration.total_seconds() / 3600
            }
            
        except Exception as e:
            logger.error(f"Error getting memory usage: {e}")
            return {}

    def export_conversation(self, user_id: int, guild_id: int) -> str:
        """
        Export conversation as JSON string
        """
        try:
            messages = list(self.conversations[user_id][guild_id])
            return json.dumps(messages, indent=2)
            
        except Exception as e:
            logger.error(f"Error exporting conversation: {e}")
            return "{}"

    def import_conversation(self, user_id: int, guild_id: int, json_data: str):
        """
        Import conversation from JSON string
        """
        try:
            messages = json.loads(json_data)
            
            # Clear existing conversation
            self.clear_user_memory(user_id, guild_id)
            
            # Import messages
            for message in messages:
                if "role" in message and "content" in message:
                    # Use timestamp from import if available, otherwise current time
                    if "timestamp" in message:
                        timestamp = datetime.fromisoformat(message["timestamp"])
                    else:
                        timestamp = datetime.utcnow()
                    
                    message_obj = {
                        "role": message["role"],
                        "content": message["content"],
                        "timestamp": timestamp.isoformat()
                    }
                    
                    self.conversations[user_id][guild_id].append(message_obj)
                    self.message_timestamps[user_id][guild_id].append(timestamp)
                    
        except Exception as e:
            logger.error(f"Error importing conversation: {e}")
