import openai
import json
import logging
from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime, timedelta

from config.settings import BotConfig

logger = logging.getLogger(__name__)

class OpenAIClient:
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=BotConfig.OPENAI_API_KEY)
        # Rate limiting tracking
        self.request_times = []
        self.max_requests_per_minute = 60
        
    async def _check_rate_limit(self):
        """Check if we're within rate limits"""
        now = datetime.now()
        # Remove requests older than 1 minute
        self.request_times = [req_time for req_time in self.request_times 
                             if now - req_time < timedelta(minutes=1)]
        
        if len(self.request_times) >= self.max_requests_per_minute:
            wait_time = 60 - (now - self.request_times[0]).seconds
            await asyncio.sleep(wait_time)
            
        self.request_times.append(now)

    async def generate_chat_response(
        self, 
        message: str, 
        context: List[Dict[str, str]] = None,
        temperature: float = 0.7,
        max_tokens: int = 200,
        user_id: int = None
    ) -> str:
        """
        Generate AI chat response using OpenAI
        """
        try:
            await self._check_rate_limit()
            
            # Build messages for conversation
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful, friendly AI assistant for a Discord server. "
                        "Keep responses conversational, engaging, and appropriate for a community setting. "
                        "Be concise but informative. Use emojis sparingly and naturally. "
                        "If asked about moderation or server management, refer users to server moderators. "
                        "Stay positive and helpful while maintaining appropriate boundaries."
                    )
                }
            ]
            
            # Add conversation context if available
            if context:
                messages.extend(context[-10:])  # Last 10 messages for context
            
            # Add current message
            messages.append({"role": "user", "content": message})
            
            # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
            # do not change this unless explicitly requested by the user
            response = await self.client.chat.completions.create(
                model="gpt-5",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                user=str(user_id) if user_id else ""
            )
            
            return (response.choices[0].message.content or "").strip()
            
        except Exception as e:
            logger.error(f"Error generating chat response: {e}")
            if "insufficient_quota" in str(e) or "429" in str(e):
                raise Exception("⚠️ OpenAI API quota exceeded. Please add credits to your OpenAI account at https://platform.openai.com/account/billing")
            elif "401" in str(e):
                raise Exception("❌ Invalid OpenAI API key. Please check your API key.")
            else:
                raise Exception("Failed to generate AI response")

    async def generate_contextual_response(
        self, 
        question: str, 
        server_context: str,
        user_id: int = None
    ) -> str:
        """
        Generate response with server context
        """
        try:
            await self._check_rate_limit()
            
            system_prompt = (
                "You are an AI assistant for a Discord server. Use the provided server context "
                "to give relevant, helpful answers. If the question is about server-specific "
                "information, use the context. For general questions, provide helpful information. "
                "Keep responses friendly and appropriate for a community setting."
            )
            
            user_prompt = f"""
            Server Context:
            {server_context}
            
            Question: {question}
            """
            
            # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
            # do not change this unless explicitly requested by the user
            response = await self.client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=300,
                user=str(user_id) if user_id else ""
            )
            
            return (response.choices[0].message.content or "").strip()
            
        except Exception as e:
            logger.error(f"Error generating contextual response: {e}")
            if "insufficient_quota" in str(e) or "429" in str(e):
                raise Exception("⚠️ OpenAI API quota exceeded. Please add credits to your OpenAI account at https://platform.openai.com/account/billing")
            elif "401" in str(e):
                raise Exception("❌ Invalid OpenAI API key. Please check your API key.")
            else:
                raise Exception("Failed to generate AI response")

    async def moderate_content(self, text: str) -> Dict[str, Any]:
        """
        Check content using OpenAI's moderation API
        """
        try:
            await self._check_rate_limit()
            
            response = await self.client.moderations.create(input=text)
            moderation_result = response.results[0]
            
            return {
                "flagged": moderation_result.flagged,
                "categories": moderation_result.categories.model_dump(),
                "category_scores": moderation_result.category_scores.model_dump()
            }
            
        except Exception as e:
            logger.error(f"Error moderating content: {e}")
            # Default to safe if moderation fails
            return {
                "flagged": False,
                "categories": {},
                "category_scores": {}
            }

    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of text for advanced moderation
        """
        try:
            await self._check_rate_limit()
            
            # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
            # do not change this unless explicitly requested by the user
            response = await self.client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a sentiment analysis expert. Analyze the sentiment "
                            "and provide a rating from 1-5 (1=very negative, 5=very positive) "
                            "and confidence score 0-1. Respond only with JSON in this format: "
                            "{'sentiment': number, 'confidence': number, 'emotion': 'string'}"
                        )
                    },
                    {"role": "user", "content": text}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=100
            )
            
            result = json.loads(response.choices[0].message.content or "{}")
            return {
                "sentiment": max(1, min(5, round(result.get("sentiment", 3)))),
                "confidence": max(0, min(1, result.get("confidence", 0.5))),
                "emotion": result.get("emotion", "neutral")
            }
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return {
                "sentiment": 3,
                "confidence": 0.5,
                "emotion": "neutral"
            }

    async def generate_summary(self, messages: List[str], max_length: int = 200) -> str:
        """
        Generate summary of conversation or messages
        """
        try:
            await self._check_rate_limit()
            
            text_to_summarize = "\n".join(messages)
            
            # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
            # do not change this unless explicitly requested by the user
            response = await self.client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Summarize the following Discord conversation concisely, "
                            "highlighting key points and main topics discussed. "
                            "Keep it friendly and informative."
                        )
                    },
                    {"role": "user", "content": text_to_summarize}
                ],
                temperature=0.5,
                max_tokens=max_length
            )
            
            return (response.choices[0].message.content or "").strip()
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            if "insufficient_quota" in str(e) or "429" in str(e):
                raise Exception("⚠️ OpenAI API quota exceeded. Please add credits to your OpenAI account at https://platform.openai.com/account/billing")
            elif "401" in str(e):
                raise Exception("❌ Invalid OpenAI API key. Please check your API key.")
            else:
                raise Exception("Failed to generate summary")
