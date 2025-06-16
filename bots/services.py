import os
import json
import requests
from datetime import datetime, date
from django.conf import settings
from django.core.files.base import ContentFile
import elevenlabs
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential
from .models import ElevenLabsUsage, Message
import logging
import re

logger = logging.getLogger(__name__)


def markdown_to_clean_text(text):
    """
    Convert markdown text to clean, readable text for voice synthesis
    Removes all markdown formatting while preserving the actual content
    """
    if not text:
        return ""

    # Remove code blocks first (```code```)
    text = re.sub(r'```[\s\S]*?```', '', text)

    # Remove inline code (`code`)
    text = re.sub(r'`([^`]*)`', r'\1', text)

    # Remove bold and italic formatting
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # **bold**
    text = re.sub(r'__(.*?)__', r'\1', text)      # __bold__
    text = re.sub(r'\*(.*?)\*', r'\1', text)      # *italic*
    text = re.sub(r'_(.*?)_', r'\1', text)        # _italic_

    # Remove headers (# ## ###)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # Remove links but keep the text [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

    # Remove list markers (- * + 1. 2. etc.)
    text = re.sub(r'^[\s]*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[\s]*\d+\.\s+', '', text, flags=re.MULTILINE)

    # Remove blockquotes (>)
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)

    # Remove horizontal rules (--- or ***)
    text = re.sub(r'^[-*]{3,}$', '', text, flags=re.MULTILINE)

    # Clean up extra whitespace and line breaks
    text = re.sub(r'\n\s*\n', '\n\n', text)  # Multiple line breaks to double
    text = re.sub(r'\n{3,}', '\n\n', text)   # More than 2 line breaks to 2
    text = text.strip()

    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)

    # Add natural pauses for better speech
    # Replace double line breaks with longer pauses
    text = text.replace('\n\n', '. ')
    text = text.replace('\n', '. ')

    # Clean up any remaining formatting artifacts
    text = re.sub(r'[*_`#>]', '', text)

    return text.strip()


class VoiceSelectionService:
    """Service for intelligently selecting ElevenLabs voices based on bot characteristics"""

    # Available ElevenLabs voices with their characteristics
    VOICE_PROFILES = {
        '21m00Tcm4TlvDq8ikWAM': {  # Rachel
            'name': 'Rachel',
            'gender': 'female',
            'age': 'young_adult',
            'tone': 'friendly',
            'accent': 'american',
            'personality': ['helpful', 'professional', 'warm', 'customer_service']
        },
        'AZnzlk1XvdvUeBnXmlld': {  # Domi
            'name': 'Domi',
            'gender': 'female',
            'age': 'young_adult',
            'tone': 'confident',
            'accent': 'american',
            'personality': ['assertive', 'modern', 'tech_savvy']
        },
        'EXAVITQu4vr4xnSDxMaL': {  # Bella
            'name': 'Bella',
            'gender': 'female',
            'age': 'young_adult',
            'tone': 'gentle',
            'accent': 'american',
            'personality': ['caring', 'empathetic', 'therapeutic', 'calm']
        },
        'ErXwobaYiN019PkySvjV': {  # Antoni
            'name': 'Antoni',
            'gender': 'male',
            'age': 'adult',
            'tone': 'authoritative',
            'accent': 'american',
            'personality': ['professional', 'business', 'serious', 'executive']
        },
        'MF3mGyEYCl7XYWbV9V6O': {  # Elli
            'name': 'Elli',
            'gender': 'female',
            'age': 'young_adult',
            'tone': 'energetic',
            'accent': 'american',
            'personality': ['enthusiastic', 'creative', 'artistic', 'upbeat']
        },
        'TxGEqnHWrfWFTfGW9XjX': {  # Josh
            'name': 'Josh',
            'gender': 'male',
            'age': 'young_adult',
            'tone': 'casual',
            'accent': 'american',
            'personality': ['friendly', 'approachable', 'tech_support', 'informal']
        },
        'VR6AewLTigWG4xSOukaG': {  # Arnold
            'name': 'Arnold',
            'gender': 'male',
            'age': 'mature',
            'tone': 'deep',
            'accent': 'american',
            'personality': ['wise', 'mentor', 'experienced', 'authoritative']
        },
        'pNInz6obpgDQGcFmaJgB': {  # Adam
            'name': 'Adam',
            'gender': 'male',
            'age': 'adult',
            'tone': 'neutral',
            'accent': 'american',
            'personality': ['balanced', 'versatile', 'professional', 'clear']
        },
        'yoZ06aMxZJJ28mfd3POQ': {  # Sam
            'name': 'Sam',
            'gender': 'male',
            'age': 'young_adult',
            'tone': 'warm',
            'accent': 'american',
            'personality': ['friendly', 'helpful', 'supportive', 'guidance']
        }
    }

    @classmethod
    def select_voice_for_bot(cls, bot_name, system_prompt):
        """
        Intelligently select the best voice based on bot name and system prompt

        Args:
            bot_name (str): Name of the bot
            system_prompt (str): System prompt describing bot behavior

        Returns:
            str: ElevenLabs voice ID
        """
        # Combine bot name and system prompt for analysis
        text_to_analyze = f"{bot_name} {system_prompt}".lower()

        # Score each voice based on keyword matching
        voice_scores = {}

        for voice_id, profile in cls.VOICE_PROFILES.items():
            score = 0

            # Check for gender preferences in text
            if 'female' in text_to_analyze or 'woman' in text_to_analyze or 'girl' in text_to_analyze:
                if profile['gender'] == 'female':
                    score += 3
            elif 'male' in text_to_analyze or 'man' in text_to_analyze or 'boy' in text_to_analyze:
                if profile['gender'] == 'male':
                    score += 3

            # Check for personality keywords
            personality_keywords = {
                'professional': ['professional', 'business', 'corporate', 'formal', 'executive'],
                'friendly': ['friendly', 'warm', 'welcoming', 'approachable', 'kind'],
                'helpful': ['helpful', 'assistant', 'support', 'service', 'guide'],
                'authoritative': ['expert', 'authority', 'leader', 'boss', 'manager', 'serious'],
                'calm': ['calm', 'peaceful', 'relaxing', 'therapeutic', 'meditation'],
                'energetic': ['energetic', 'enthusiastic', 'excited', 'upbeat', 'dynamic'],
                'tech_savvy': ['tech', 'technology', 'computer', 'software', 'digital', 'ai'],
                'creative': ['creative', 'artistic', 'design', 'innovative', 'imaginative'],
                'caring': ['caring', 'empathetic', 'compassionate', 'understanding', 'therapy'],
                'wise': ['wise', 'mentor', 'teacher', 'experienced', 'advisor', 'guru']
            }

            for trait in profile['personality']:
                if trait in personality_keywords:
                    for keyword in personality_keywords[trait]:
                        if keyword in text_to_analyze:
                            score += 2

            # Check for specific use cases
            use_case_keywords = {
                'customer_service': ['customer', 'support', 'service', 'help', 'assistance'],
                'education': ['teach', 'learn', 'education', 'tutor', 'instructor'],
                'healthcare': ['health', 'medical', 'doctor', 'nurse', 'therapy'],
                'business': ['business', 'sales', 'marketing', 'corporate'],
                'entertainment': ['fun', 'game', 'entertainment', 'joke', 'story'],
                'technical': ['technical', 'engineering', 'developer', 'programmer']
            }

            for use_case, keywords in use_case_keywords.items():
                for keyword in keywords:
                    if keyword in text_to_analyze:
                        # Match voices to use cases
                        if use_case == 'customer_service' and 'customer_service' in profile['personality']:
                            score += 3
                        elif use_case == 'business' and 'business' in profile['personality']:
                            score += 3
                        elif use_case == 'healthcare' and 'caring' in profile['personality']:
                            score += 3
                        elif use_case == 'technical' and 'tech_savvy' in profile['personality']:
                            score += 3

            # Check bot name for gender hints
            female_names = ['alice', 'emma', 'sophia', 'olivia', 'ava', 'isabella', 'mia', 'luna', 'aria', 'eva']
            male_names = ['alex', 'john', 'mike', 'david', 'james', 'robert', 'william', 'richard', 'thomas', 'max']

            bot_name_lower = bot_name.lower()
            for name in female_names:
                if name in bot_name_lower and profile['gender'] == 'female':
                    score += 2
            for name in male_names:
                if name in bot_name_lower and profile['gender'] == 'male':
                    score += 2

            voice_scores[voice_id] = score

        # Select the voice with the highest score
        best_voice = max(voice_scores.items(), key=lambda x: x[1])
        selected_voice_id = best_voice[0]

        logger.info(f"Voice selection for '{bot_name}': {cls.VOICE_PROFILES[selected_voice_id]['name']} (score: {best_voice[1]})")

        return selected_voice_id

    @classmethod
    def get_voice_name(cls, voice_id):
        """Get the human-readable name for a voice ID"""
        return cls.VOICE_PROFILES.get(voice_id, {}).get('name', 'Unknown')


class GPTService:
    """Service for handling GitHub Models API GPT-4 calls"""

    def __init__(self):
        try:
            if not settings.GITHUB_TOKEN:
                logger.error("GITHUB_TOKEN not configured in settings")
                self.client = None
                self.model = None
                return

            endpoint = "https://models.github.ai/inference"
            model = "openai/gpt-4.1"

            self.client = ChatCompletionsClient(
                endpoint=endpoint,
                credential=AzureKeyCredential(settings.GITHUB_TOKEN),
            )
            self.model = model
            logger.info("GitHub Models client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize GitHub Models client: {str(e)}")
            self.client = None
            self.model = None
    
    def generate_response(self, conversation, user_message, bot):
        """Generate AI response using GitHub Models GPT-4"""
        try:
            if not self.client:
                logger.error("GitHub Models client not initialized")
                return "I apologize, but the AI service is not available right now. Please try again later."

            # Build conversation history for context
            messages = self._build_conversation_context(conversation, user_message, bot)

            logger.info(f"Sending request to GitHub Models API with model: {self.model}")
            logger.info(f"Messages count: {len(messages)}")

            response = self.client.complete(
                messages=messages,
                model=self.model,
                temperature=bot.temperature,
                max_tokens=500,
                top_p=1.0
            )

            logger.info("Successfully received response from GitHub Models API")
            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"GPT API error: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            return f"I apologize, but I'm having trouble processing your request right now. Error: {str(e)}"
    
    def _build_conversation_context(self, conversation, user_message, bot):
        """Build conversation context for GitHub Models API"""
        messages = [
            SystemMessage(content=bot.system_prompt)
        ]

        # Add recent conversation history (last 5 messages for context to avoid token limits)
        recent_messages = conversation.messages.order_by('-timestamp')[:5]
        for msg in reversed(recent_messages):
            if msg.message_type == "user":
                messages.append(UserMessage(content=msg.content))
            # Skip assistant messages for now to simplify the context

        # Add current user message
        messages.append(UserMessage(content=user_message))

        return messages


class ElevenLabsService:
    """Service for handling ElevenLabs text-to-speech API"""

    def __init__(self):
        if settings.ELEVENLABS_API_KEY:
            elevenlabs.set_api_key(settings.ELEVENLABS_API_KEY)

    def text_to_speech(self, text, voice_id="21m00Tcm4TlvDq8ikWAM"):
        """Convert text to speech using ElevenLabs API"""
        try:
            if not settings.ELEVENLABS_API_KEY:
                logger.warning("ElevenLabs API key not configured")
                return None

            # Clean the text by removing markdown formatting
            clean_text = markdown_to_clean_text(text)

            if not clean_text.strip():
                logger.warning("No readable text after markdown cleanup")
                return None

            # Check if we have enough credits (use clean text length for accurate tracking)
            if not self._check_credits(len(clean_text)):
                logger.warning("ElevenLabs credits exhausted")
                return None

            logger.info(f"Converting to speech: '{clean_text[:100]}...' (cleaned from markdown)")

            # Generate audio using the cleaned text
            audio_bytes = elevenlabs.generate(
                text=clean_text,
                voice=voice_id,
                model="eleven_monolingual_v1"
            )

            # Update usage tracking (use clean text length for accurate tracking)
            self._update_usage(len(clean_text))

            return audio_bytes

        except Exception as e:
            logger.error(f"ElevenLabs API error: {str(e)}")
            return None
    
    def _check_credits(self, character_count):
        """Check if we have enough ElevenLabs credits"""
        current_month = date.today().replace(day=1)
        usage, _ = ElevenLabsUsage.objects.get_or_create(
            month=current_month,
            defaults={'characters_used': 0, 'characters_limit': 10000}
        )

        return (usage.characters_used + character_count) <= usage.characters_limit

    def _update_usage(self, character_count):
        """Update ElevenLabs usage tracking"""
        current_month = date.today().replace(day=1)
        usage, _ = ElevenLabsUsage.objects.get_or_create(
            month=current_month,
            defaults={'characters_used': 0, 'characters_limit': 10000}
        )

        usage.characters_used += character_count
        usage.save()

    def get_current_usage(self):
        """Get current month's usage statistics"""
        current_month = date.today().replace(day=1)
        usage, _ = ElevenLabsUsage.objects.get_or_create(
            month=current_month,
            defaults={'characters_used': 0, 'characters_limit': 10000}
        )
        return usage


class ConversationManager:
    """Service for managing conversations and message flow"""
    
    def __init__(self):
        self.gpt_service = GPTService()
        self.tts_service = ElevenLabsService()
    
    def process_user_message(self, conversation, user_message_text):
        """Process a user message and generate AI response with optional audio"""
        try:
            # Save user message
            user_message = Message.objects.create(
                conversation=conversation,
                message_type='user',
                content=user_message_text
            )
            
            # Generate AI response
            ai_response_text = self.gpt_service.generate_response(
                conversation, user_message_text, conversation.bot
            )
            
            # Create AI message
            ai_message = Message.objects.create(
                conversation=conversation,
                message_type='ai',
                content=ai_response_text
            )
            
            # Generate audio if possible
            audio_data = self.tts_service.text_to_speech(
                ai_response_text, conversation.bot.voice_id
            )
            
            if audio_data:
                # Save audio file
                audio_filename = f"response_{ai_message.id}.mp3"
                ai_message.audio_file.save(
                    audio_filename,
                    ContentFile(audio_data),
                    save=True
                )
            
            return {
                'user_message': user_message,
                'ai_message': ai_message,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_usage_info(self):
        """Get current ElevenLabs usage information"""
        return self.tts_service.get_current_usage()
