import json
import logging
import os
from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime, timedelta

from google import genai
from google.genai import types
from config.settings import BotConfig

logger = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self):
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
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
        Generate AI chat response using Gemini
        """
        try:
            await self._check_rate_limit()
            
            # Build conversation context
            conversation_text = ""
            if context:
                for msg in context[-10:]:  # Last 10 messages for context
                    role = "User" if msg["role"] == "user" else "Assistant"
                    conversation_text += f"{role}: {msg['content']}\n"
            
            # Create the full prompt
            system_prompt = (
                "You are a helpful, friendly AI assistant for a Discord server. "
                "Keep responses conversational, engaging, and appropriate for a community setting. "
                "Be concise but informative. Use emojis sparingly and naturally. "
                "If asked about moderation or server management, refer users to server moderators. "
                "Stay positive and helpful while maintaining appropriate boundaries."
            )
            
            full_prompt = f"{system_prompt}\n\nConversation history:\n{conversation_text}\nUser: {message}\nAssistant:"
            
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model="gemini-2.5-flash",
                contents=full_prompt
            )
            
            # Get the response text
            response_text = response.text if response.text else None
            
            if response_text:
                return response_text.strip()
            else:
                logger.warning(f"Empty response from Gemini. Finish reason: {response.candidates[0].finish_reason if response.candidates else 'unknown'}")
                return "I'm having trouble generating a response right now. Please try again!"
            
        except Exception as e:
            logger.error(f"Error generating chat response: {e}")
            if "quota" in str(e).lower() or "exceeded" in str(e).lower():
                raise Exception("⚠️ Gemini API quota exceeded. Please try again later.")
            elif "401" in str(e) or "authentication" in str(e).lower():
                raise Exception("❌ Invalid Gemini API key. Please check your API key.")
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
            
            prompt = f"""
            You are an AI assistant for a Discord server. Use the provided server context 
            to give relevant, helpful answers. If the question is about server-specific 
            information, use the context. For general questions, provide helpful information. 
            Keep responses friendly and appropriate for a community setting.
            
            Server Context:
            {server_context}
            
            Question: {question}
            
            Answer:
            """
            
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model="gemini-2.5-flash",
                contents=prompt
            )
            
            response_text = response.text if response.text else None
            
            if response_text:
                return response_text.strip()
            else:
                return "I'm sorry, I couldn't generate a response."
            
        except Exception as e:
            logger.error(f"Error generating contextual response: {e}")
            if "quota" in str(e).lower() or "exceeded" in str(e).lower():
                raise Exception("⚠️ Gemini API quota exceeded. Please try again later.")
            elif "401" in str(e) or "authentication" in str(e).lower():
                raise Exception("❌ Invalid Gemini API key. Please check your API key.")
            else:
                raise Exception("Failed to generate AI response")

    async def moderate_content(self, text: str) -> Dict[str, Any]:
        """
        Check content using Gemini for moderation
        """
        try:
            await self._check_rate_limit()
            
            prompt = f"""
            Analyze the following text for potential policy violations or inappropriate content.
            Consider harassment, hate speech, violence, explicit content, spam, or other harmful content.
            
            Text to analyze: "{text}"
            
            Respond with JSON in this exact format:
            {{
                "flagged": true/false,
                "categories": {{
                    "harassment": true/false,
                    "hate": true/false,
                    "violence": true/false,
                    "sexual": true/false,
                    "spam": true/false
                }},
                "reason": "brief explanation if flagged"
            }}
            """
            
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                    max_output_tokens=200
                )
            )
            
            response_text = None
            if hasattr(response, 'text') and response.text:
                response_text = response.text
            elif hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content:
                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                        text_parts = [part.text for part in candidate.content.parts if hasattr(part, 'text') and part.text]
                        if text_parts:
                            response_text = ' '.join(text_parts)
            
            if response_text:
                try:
                    result = json.loads(response_text)
                    return {
                        "flagged": result.get("flagged", False),
                        "categories": result.get("categories", {}),
                        "reason": result.get("reason", "")
                    }
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse moderation response: {response_text}")
            
            # Default to safe if parsing fails
            return {
                "flagged": False,
                "categories": {},
                "reason": ""
            }
            
        except Exception as e:
            logger.error(f"Error moderating content: {e}")
            # Default to safe if moderation fails
            return {
                "flagged": False,
                "categories": {},
                "reason": ""
            }

    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of text
        """
        try:
            await self._check_rate_limit()
            
            prompt = f"""
            Analyze the sentiment of the following text and provide a rating 
            from 1-5 (1=very negative, 5=very positive) and confidence score 0-1.
            
            Text: "{text}"
            
            Respond with JSON in this exact format:
            {{
                "sentiment": 1-5,
                "confidence": 0.0-1.0,
                "emotion": "string describing the emotion"
            }}
            """
            
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.3,
                    max_output_tokens=100
                )
            )
            
            response_text = None
            if hasattr(response, 'text') and response.text:
                response_text = response.text
            elif hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content:
                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                        text_parts = [part.text for part in candidate.content.parts if hasattr(part, 'text') and part.text]
                        if text_parts:
                            response_text = ' '.join(text_parts)
            
            if response_text:
                try:
                    result = json.loads(response_text)
                    return {
                        "sentiment": max(1, min(5, int(result.get("sentiment", 3)))),
                        "confidence": max(0, min(1, float(result.get("confidence", 0.5)))),
                        "emotion": result.get("emotion", "neutral")
                    }
                except (json.JSONDecodeError, ValueError):
                    logger.error(f"Failed to parse sentiment response: {response_text}")
            
            return {
                "sentiment": 3,
                "confidence": 0.5,
                "emotion": "neutral"
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
            
            prompt = f"""
            Summarize the following Discord conversation concisely, 
            highlighting key points and main topics discussed. 
            Keep it friendly and informative.
            
            Conversation:
            {text_to_summarize}
            
            Summary:
            """
            
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.5,
                    max_output_tokens=max_length
                )
            )
            
            if hasattr(response, 'text') and response.text:
                return response.text.strip()
            elif hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content:
                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                        text_parts = [part.text for part in candidate.content.parts if hasattr(part, 'text') and part.text]
                        if text_parts:
                            return ' '.join(text_parts).strip()
            
            return "Unable to generate summary."
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            if "quota" in str(e).lower() or "exceeded" in str(e).lower():
                raise Exception("⚠️ Gemini API quota exceeded. Please try again later.")
            elif "401" in str(e) or "authentication" in str(e).lower():
                raise Exception("❌ Invalid Gemini API key. Please check your API key.")
            else:
                raise Exception("Failed to generate summary")