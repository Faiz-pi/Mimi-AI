import time
import logging
from typing import Dict, DefaultDict
from collections import defaultdict, deque
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class RateLimit:
    requests: int
    window: int  # seconds
    
class RateLimiter:
    def __init__(self):
        """
        Initialize rate limiter with different limits for different command types
        """
        # Define rate limits for different command types
        self.limits = {
            "chat": RateLimit(requests=10, window=60),      # 10 chats per minute
            "ask": RateLimit(requests=5, window=60),        # 5 asks per minute
            "moderate": RateLimit(requests=3, window=60),   # 3 moderations per minute
            "global": RateLimit(requests=20, window=60),    # 20 total commands per minute
        }
        
        # Track requests per user per command type
        # Structure: {user_id: {command_type: deque of timestamps}}
        self.user_requests: DefaultDict[int, DefaultDict[str, deque]] = defaultdict(
            lambda: defaultdict(lambda: deque())
        )
        
        # Track global requests per user
        self.global_requests: DefaultDict[int, deque] = defaultdict(lambda: deque())
        
    def check_rate_limit(self, user_id: int, command_type: str) -> bool:
        """
        Check if user is within rate limits for a specific command type
        
        Args:
            user_id: Discord user ID
            command_type: Type of command (chat, ask, moderate, etc.)
            
        Returns:
            True if request is allowed, False if rate limited
        """
        try:
            current_time = time.time()
            
            # Check global rate limit first
            if not self._check_global_limit(user_id, current_time):
                logger.warning(f"User {user_id} hit global rate limit")
                return False
            
            # Check specific command rate limit
            if command_type in self.limits:
                if not self._check_command_limit(user_id, command_type, current_time):
                    logger.warning(f"User {user_id} hit {command_type} rate limit")
                    return False
            
            # Record the request
            self._record_request(user_id, command_type, current_time)
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            # Default to allowing request if error occurs
            return True
    
    def _check_global_limit(self, user_id: int, current_time: float) -> bool:
        """Check global rate limit for user"""
        global_limit = self.limits["global"]
        user_global_requests = self.global_requests[user_id]
        
        # Remove old requests outside the window
        while user_global_requests and current_time - user_global_requests[0] > global_limit.window:
            user_global_requests.popleft()
        
        return len(user_global_requests) < global_limit.requests
    
    def _check_command_limit(self, user_id: int, command_type: str, current_time: float) -> bool:
        """Check specific command rate limit for user"""
        command_limit = self.limits[command_type]
        user_command_requests = self.user_requests[user_id][command_type]
        
        # Remove old requests outside the window
        while user_command_requests and current_time - user_command_requests[0] > command_limit.window:
            user_command_requests.popleft()
        
        return len(user_command_requests) < command_limit.requests
    
    def _record_request(self, user_id: int, command_type: str, current_time: float):
        """Record a request for both global and command-specific tracking"""
        # Record global request
        self.global_requests[user_id].append(current_time)
        
        # Record command-specific request
        if command_type in self.limits:
            self.user_requests[user_id][command_type].append(current_time)
    
    def get_time_until_reset(self, user_id: int, command_type: str = None) -> int:
        """
        Get seconds until rate limit resets for user
        
        Args:
            user_id: Discord user ID
            command_type: Optional specific command type
            
        Returns:
            Seconds until rate limit resets, 0 if not rate limited
        """
        try:
            current_time = time.time()
            
            if command_type and command_type in self.limits:
                # Check specific command limit
                command_limit = self.limits[command_type]
                user_command_requests = self.user_requests[user_id][command_type]
                
                if len(user_command_requests) >= command_limit.requests and user_command_requests:
                    oldest_request = user_command_requests[0]
                    time_until_reset = command_limit.window - (current_time - oldest_request)
                    return max(0, int(time_until_reset))
            
            # Check global limit
            global_limit = self.limits["global"]
            user_global_requests = self.global_requests[user_id]
            
            if len(user_global_requests) >= global_limit.requests and user_global_requests:
                oldest_request = user_global_requests[0]
                time_until_reset = global_limit.window - (current_time - oldest_request)
                return max(0, int(time_until_reset))
            
            return 0
            
        except Exception as e:
            logger.error(f"Error getting time until reset: {e}")
            return 0
    
    def get_user_stats(self, user_id: int) -> Dict[str, any]:
        """Get rate limit statistics for a user"""
        try:
            current_time = time.time()
            stats = {}
            
            # Global stats
            global_requests = self.global_requests[user_id]
            global_limit = self.limits["global"]
            
            # Count recent global requests
            recent_global = sum(1 for req_time in global_requests 
                              if current_time - req_time <= global_limit.window)
            
            stats["global"] = {
                "requests_used": recent_global,
                "requests_limit": global_limit.requests,
                "window_seconds": global_limit.window,
                "time_until_reset": self.get_time_until_reset(user_id)
            }
            
            # Command-specific stats
            for command_type, limit in self.limits.items():
                if command_type == "global":
                    continue
                    
                command_requests = self.user_requests[user_id][command_type]
                recent_requests = sum(1 for req_time in command_requests 
                                    if current_time - req_time <= limit.window)
                
                stats[command_type] = {
                    "requests_used": recent_requests,
                    "requests_limit": limit.requests,
                    "window_seconds": limit.window,
                    "time_until_reset": self.get_time_until_reset(user_id, command_type)
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {}
    
    def reset_user_limits(self, user_id: int, command_type: str = None):
        """
        Reset rate limits for a user
        
        Args:
            user_id: Discord user ID
            command_type: Optional specific command type to reset
        """
        try:
            if command_type:
                # Reset specific command
                if command_type in self.user_requests[user_id]:
                    self.user_requests[user_id][command_type].clear()
            else:
                # Reset all limits for user
                self.user_requests[user_id].clear()
                self.global_requests[user_id].clear()
                
        except Exception as e:
            logger.error(f"Error resetting user limits: {e}")
    
    def cleanup_old_data(self):
        """Clean up old request data to prevent memory leaks"""
        try:
            current_time = time.time()
            max_window = max(limit.window for limit in self.limits.values())
            
            # Clean global requests
            for user_id in list(self.global_requests.keys()):
                user_requests = self.global_requests[user_id]
                while user_requests and current_time - user_requests[0] > max_window:
                    user_requests.popleft()
                
                # Remove empty deques
                if not user_requests:
                    del self.global_requests[user_id]
            
            # Clean command-specific requests
            for user_id in list(self.user_requests.keys()):
                user_commands = self.user_requests[user_id]
                
                for command_type in list(user_commands.keys()):
                    command_requests = user_commands[command_type]
                    limit = self.limits.get(command_type)
                    
                    if limit:
                        while command_requests and current_time - command_requests[0] > limit.window:
                            command_requests.popleft()
                    
                    # Remove empty deques
                    if not command_requests:
                        del user_commands[command_type]
                
                # Remove empty user entries
                if not user_commands:
                    del self.user_requests[user_id]
                    
        except Exception as e:
            logger.error(f"Error cleaning up rate limiter data: {e}")
