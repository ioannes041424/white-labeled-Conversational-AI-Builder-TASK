import json
import requests
from datetime import datetime, date
from django.conf import settings
from django.core.files.base import ContentFile
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential
from .models import GoogleCloudTTSUsage, Message
import logging
import re

logger = logging.getLogger(__name__)


def markdown_to_clean_text(text):
    """
    Convert markdown text to clean, readable text for voice synthesis
    Removes all markdown formatting, emojis, and special characters while preserving the actual content
    """
    if not text:
        return ""

    # Remove emojis and other Unicode symbols that shouldn't be read aloud
    # This regex removes most emoji ranges and symbols
    text = re.sub(r'[\U0001F600-\U0001F64F]', '', text)  # Emoticons
    text = re.sub(r'[\U0001F300-\U0001F5FF]', '', text)  # Symbols & pictographs
    text = re.sub(r'[\U0001F680-\U0001F6FF]', '', text)  # Transport & map symbols
    text = re.sub(r'[\U0001F1E0-\U0001F1FF]', '', text)  # Flags (iOS)
    text = re.sub(r'[\U00002702-\U000027B0]', '', text)  # Dingbats
    text = re.sub(r'[\U000024C2-\U0001F251]', '', text)  # Enclosed characters
    text = re.sub(r'[\U0001F900-\U0001F9FF]', '', text)  # Supplemental Symbols and Pictographs
    text = re.sub(r'[\U0001FA70-\U0001FAFF]', '', text)  # Symbols and Pictographs Extended-A

    # Remove common emoji-like characters
    text = re.sub(r'[😀-🙏🌀-🗿🚀-🛿🇀-🇿♀-♿⚀-⚿✀-➿]', '', text)

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

    # Remove any remaining special characters that might be read as symbols
    text = re.sub(r'[^\w\s\.,!?;:\'"()-]', '', text)

    return text.strip()


class VoiceSelectionService:
    """Service for intelligently selecting Google Cloud Text-to-Speech voices based on bot characteristics"""

    # Available Google Cloud Text-to-Speech voices with their characteristics
    # Using natural Chirp3-HD voices for the most human-like speech (12 total)
    VOICE_PROFILES = {
        # Chirp3-HD Voices - Most natural and human-like (all available English voices)
        'en-US-Chirp3-HD-Achernar': {  # Female, friendly and warm
            'name': 'Achernar',
            'gender': 'female',
            'age': 'young_adult',
            'tone': 'friendly',
            'accent': 'american',
            'personality': ['helpful', 'professional', 'warm', 'customer_service', 'natural']
        },
        'en-US-Chirp3-HD-Aoede': {  # Female, melodic and artistic
            'name': 'Aoede',
            'gender': 'female',
            'age': 'young_adult',
            'tone': 'melodic',
            'accent': 'american',
            'personality': ['creative', 'artistic', 'expressive', 'musical', 'natural']
        },
        'en-US-Chirp3-HD-Puck': {  # Male, playful and energetic
            'name': 'Puck',
            'gender': 'male',
            'age': 'young_adult',
            'tone': 'playful',
            'accent': 'american',
            'personality': ['energetic', 'fun', 'creative', 'youthful', 'natural']
        },
        'en-US-Chirp3-HD-Charon': {  # Male, deep and authoritative
            'name': 'Charon',
            'gender': 'male',
            'age': 'adult',
            'tone': 'deep',
            'accent': 'american',
            'personality': ['authoritative', 'serious', 'professional', 'mature', 'natural']
        },
        'en-US-Chirp3-HD-Kore': {  # Female, gentle and caring
            'name': 'Kore',
            'gender': 'female',
            'age': 'adult',
            'tone': 'gentle',
            'accent': 'american',
            'personality': ['caring', 'nurturing', 'supportive', 'healthcare', 'natural']
        },
        'en-US-Chirp3-HD-Fenrir': {  # Male, strong and confident
            'name': 'Fenrir',
            'gender': 'male',
            'age': 'adult',
            'tone': 'confident',
            'accent': 'american',
            'personality': ['strong', 'confident', 'leadership', 'powerful', 'natural']
        },
        'en-US-Chirp3-HD-Leda': {  # Female, elegant and sophisticated
            'name': 'Leda',
            'gender': 'female',
            'age': 'adult',
            'tone': 'elegant',
            'accent': 'american',
            'personality': ['sophisticated', 'refined', 'professional', 'polished', 'natural']
        },
        'en-US-Chirp3-HD-Orus': {  # Male, warm and approachable
            'name': 'Orus',
            'gender': 'male',
            'age': 'adult',
            'tone': 'warm',
            'accent': 'american',
            'personality': ['warm', 'approachable', 'friendly', 'supportive', 'natural']
        },
        'en-US-Chirp3-HD-Zephyr': {  # Female, light and breezy
            'name': 'Zephyr',
            'gender': 'female',
            'age': 'young_adult',
            'tone': 'light',
            'accent': 'american',
            'personality': ['cheerful', 'upbeat', 'optimistic', 'fresh', 'natural']
        },

        # Additional Chirp3-HD voices for more variety
        'en-US-Chirp3-HD-Achird': {  # Male, technical and precise
            'name': 'Achird',
            'gender': 'male',
            'age': 'adult',
            'tone': 'precise',
            'accent': 'american',
            'personality': ['technical', 'analytical', 'clear', 'informative', 'natural']
        },
        'en-US-Chirp3-HD-Autonoe': {  # Female, intelligent and articulate
            'name': 'Autonoe',
            'gender': 'female',
            'age': 'adult',
            'tone': 'articulate',
            'accent': 'american',
            'personality': ['intelligent', 'educational', 'clear', 'professional', 'natural']
        },
        'en-US-Chirp3-HD-Callirrhoe': {  # Female, flowing and expressive
            'name': 'Callirrhoe',
            'gender': 'female',
            'age': 'young_adult',
            'tone': 'expressive',
            'accent': 'american',
            'personality': ['expressive', 'dynamic', 'engaging', 'storytelling', 'natural']
        },


    }

    @classmethod
    def select_voice_for_bot(cls, bot_name, system_prompt):
        """
        Intelligently select the best premium voice based on bot name and system prompt
        Uses advanced scoring algorithm optimized for Studio and Wavenet voices

        Args:
            bot_name (str): Name of the bot
            system_prompt (str): System prompt describing bot behavior

        Returns:
            str: Google Cloud Text-to-Speech voice name
        """
        # Combine bot name and system prompt for analysis
        text_to_analyze = f"{bot_name} {system_prompt}".lower()
        voice_scores = {}

        for voice_id, profile in cls.VOICE_PROFILES.items():
            score = 0

            # Premium voice bonus (Studio voices get higher priority)
            if 'Studio' in voice_id:
                score += 5  # Studio voices are premium
            elif 'Wavenet' in voice_id:
                score += 3  # Wavenet voices are high-quality

            # Enhanced gender detection with more keywords
            gender_keywords = {
                'female': ['female', 'woman', 'girl', 'lady', 'she', 'her', 'maya', 'sophia', 'emma', 'alice', 'bella', 'luna'],
                'male': ['male', 'man', 'boy', 'guy', 'he', 'him', 'alex', 'john', 'mike', 'david', 'max', 'sam', 'coach']
            }

            for gender, keywords in gender_keywords.items():
                if any(keyword in text_to_analyze for keyword in keywords):
                    if profile['gender'] == gender:
                        score += 8  # Strong gender match bonus

            # Advanced personality and tone matching
            personality_scoring = {
                # High-priority matches (perfect fit)
                'authoritative': {
                    'keywords': ['expert', 'authority', 'leader', 'boss', 'manager', 'serious', 'professional', 'business', 'executive', 'advisor'],
                    'bonus': 10
                },
                'friendly': {
                    'keywords': ['friendly', 'warm', 'welcoming', 'approachable', 'kind', 'helpful', 'support', 'customer'],
                    'bonus': 8
                },
                'confident': {
                    'keywords': ['confident', 'assertive', 'modern', 'tech', 'technology', 'ai', 'smart', 'innovative'],
                    'bonus': 8
                },
                'gentle': {
                    'keywords': ['gentle', 'calm', 'peaceful', 'therapeutic', 'therapy', 'caring', 'empathetic', 'meditation', 'health'],
                    'bonus': 10
                },
                'energetic': {
                    'keywords': ['energetic', 'enthusiastic', 'excited', 'upbeat', 'dynamic', 'fitness', 'coach', 'motivate'],
                    'bonus': 10
                },
                'professional': {
                    'keywords': ['professional', 'business', 'corporate', 'formal', 'reliable', 'trustworthy'],
                    'bonus': 7
                },
                'casual': {
                    'keywords': ['casual', 'informal', 'friend', 'buddy', 'chat', 'conversation', 'relaxed'],
                    'bonus': 6
                },
                'deep': {
                    'keywords': ['wise', 'mentor', 'teacher', 'experienced', 'guru', 'guide', 'elder', 'master'],
                    'bonus': 9
                },
                'neutral': {
                    'keywords': ['neutral', 'balanced', 'versatile', 'general', 'standard', 'clear'],
                    'bonus': 4
                },
                'warm': {
                    'keywords': ['warm', 'supportive', 'guidance', 'help', 'assist', 'companion'],
                    'bonus': 7
                }
            }

            # Score based on tone and personality matches
            bot_tone = profile.get('tone', '')
            for tone, config in personality_scoring.items():
                if tone == bot_tone:
                    # Check if any keywords match
                    keyword_matches = sum(1 for keyword in config['keywords'] if keyword in text_to_analyze)
                    if keyword_matches > 0:
                        score += config['bonus'] + (keyword_matches * 2)

            # Enhanced use case matching with Chirp3-HD voices only
            use_case_mapping = {
                'customer_service': {
                    'keywords': ['customer', 'support', 'service', 'help', 'assistance', 'helpdesk'],
                    'preferred_voices': ['en-US-Chirp3-HD-Achernar', 'en-US-Chirp3-HD-Kore'],
                    'bonus': 15
                },
                'business': {
                    'keywords': ['business', 'sales', 'marketing', 'corporate', 'executive', 'professional'],
                    'preferred_voices': ['en-US-Chirp3-HD-Charon', 'en-US-Chirp3-HD-Leda'],
                    'bonus': 12
                },
                'education': {
                    'keywords': ['teach', 'learn', 'education', 'tutor', 'instructor', 'study', 'academic'],
                    'preferred_voices': ['en-US-Chirp3-HD-Autonoe', 'en-US-Chirp3-HD-Orus'],
                    'bonus': 12
                },
                'healthcare': {
                    'keywords': ['health', 'medical', 'doctor', 'nurse', 'therapy', 'wellness', 'care'],
                    'preferred_voices': ['en-US-Chirp3-HD-Kore', 'en-US-Chirp3-HD-Achernar'],
                    'bonus': 15
                },
                'technology': {
                    'keywords': ['tech', 'technology', 'ai', 'software', 'digital', 'computer', 'programming'],
                    'preferred_voices': ['en-US-Chirp3-HD-Achird', 'en-US-Chirp3-HD-Autonoe'],
                    'bonus': 12
                },
                'creative': {
                    'keywords': ['creative', 'artistic', 'design', 'writing', 'content', 'innovative'],
                    'preferred_voices': ['en-US-Chirp3-HD-Aoede', 'en-US-Chirp3-HD-Callirrhoe'],
                    'bonus': 12
                },
                'fitness': {
                    'keywords': ['fitness', 'coach', 'workout', 'exercise', 'health', 'training'],
                    'preferred_voices': ['en-US-Chirp3-HD-Puck', 'en-US-Chirp3-HD-Fenrir'],
                    'bonus': 12
                },
                'entertainment': {
                    'keywords': ['fun', 'entertainment', 'game', 'story', 'adventure', 'playful'],
                    'preferred_voices': ['en-US-Chirp3-HD-Puck', 'en-US-Chirp3-HD-Zephyr', 'en-US-Chirp3-HD-Callirrhoe'],
                    'bonus': 12
                }
            }

            # Apply use case bonuses
            for use_case, config in use_case_mapping.items():
                if any(keyword in text_to_analyze for keyword in config['keywords']):
                    if voice_id in config['preferred_voices']:
                        score += config['bonus']

            # Bot name analysis for better matching with Chirp3-HD voices only
            name_patterns = {
                'coach': ['en-US-Chirp3-HD-Puck', 'en-US-Chirp3-HD-Fenrir'],
                'assistant': ['en-US-Chirp3-HD-Achernar', 'en-US-Chirp3-HD-Kore'],
                'advisor': ['en-US-Chirp3-HD-Charon', 'en-US-Chirp3-HD-Leda'],
                'buddy': ['en-US-Chirp3-HD-Puck', 'en-US-Chirp3-HD-Orus'],
                'expert': ['en-US-Chirp3-HD-Achird', 'en-US-Chirp3-HD-Autonoe'],
                'support': ['en-US-Chirp3-HD-Achernar', 'en-US-Chirp3-HD-Kore'],
                'wise': ['en-US-Chirp3-HD-Charon', 'en-US-Chirp3-HD-Orus'],
                'creative': ['en-US-Chirp3-HD-Aoede', 'en-US-Chirp3-HD-Callirrhoe'],
                'teacher': ['en-US-Chirp3-HD-Autonoe', 'en-US-Chirp3-HD-Orus']
            }

            for pattern, preferred_voices in name_patterns.items():
                if pattern in bot_name.lower() and voice_id in preferred_voices:
                    score += 8

            voice_scores[voice_id] = score

        # Select the voice with the highest score, with fallback logic
        if not voice_scores:
            return 'en-US-Studio-O'  # Default fallback

        # Ensure we have at least one voice scored
        if not voice_scores:
            logger.warning("No voice scores calculated, using default Chirp3-HD-Achernar voice")
            return "en-US-Chirp3-HD-Achernar"

        best_voice = max(voice_scores.items(), key=lambda x: x[1])
        selected_voice_id = best_voice[0]
        selected_voice_name = cls.VOICE_PROFILES[selected_voice_id]['name']

        logger.info(f"🎤 Voice selection for bot '{bot_name}': {selected_voice_name} (score: {best_voice[1]})")
        logger.info(f"Voice analysis: '{text_to_analyze[:100]}...'")

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


class GoogleCloudTTSService:
    """Service for handling Google Cloud Text-to-Speech API with API key authentication"""

    def __init__(self):
        try:
            # Use API key authentication (simple and unlimited)
            if hasattr(settings, 'GOOGLE_CLOUD_API_KEY') and settings.GOOGLE_CLOUD_API_KEY:
                # Store API key for authentication
                self.api_key = settings.GOOGLE_CLOUD_API_KEY
                self.client = None  # We'll use REST API instead of client library

                logger.info(f"Google Cloud Text-to-Speech service initialized with API key: {self.api_key[:20]}...")

            else:
                logger.error("No Google Cloud API key found in settings")
                self.client = None
                self.api_key = None

        except Exception as e:
            logger.error(f"Failed to initialize Google Cloud TTS service: {str(e)}")
            self.client = None
            self.api_key = None

    def text_to_speech(self, text, voice_name="en-US-Chirp3-HD-Achernar"):
        """Convert text to speech using Google Cloud Text-to-Speech API"""
        try:
            # Clean the text by removing markdown formatting
            clean_text = markdown_to_clean_text(text)

            if not clean_text.strip():
                logger.warning("No readable text after markdown cleanup")
                return None

            # Note: API is now unlimited, no usage limit checks needed
            logger.info(f"Processing {len(clean_text)} characters for TTS (unlimited API)")

            logger.info(f"Converting to speech: '{clean_text[:100]}...' (cleaned from markdown)")
            logger.info(f"Using voice: {voice_name}")

            # Use REST API with API key (most reliable method)
            if self.api_key:
                return self._synthesize_with_rest_api(clean_text, voice_name)
            else:
                logger.error("No Google Cloud API key available")
                return None

        except Exception as e:
            logger.error(f"Google Cloud TTS API error: {str(e)}")
            return None



    def _synthesize_with_rest_api(self, text, voice_name):
        """Synthesize speech using direct REST API calls with API key"""
        import requests
        import json

        url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={self.api_key}"

        payload = {
            "input": {"text": text},
            "voice": {
                "languageCode": "en-US",
                "name": voice_name
            },
            "audioConfig": {
                "audioEncoding": "MP3"
            }
        }

        headers = {
            "Content-Type": "application/json"
        }

        response = requests.post(url, headers=headers, data=json.dumps(payload))

        if response.status_code == 200:
            result = response.json()
            if 'audioContent' in result:
                import base64
                audio_content = base64.b64decode(result['audioContent'])

                logger.info("✅ Speech synthesis successful using REST API")
                return audio_content
            else:
                logger.error("No audio content in REST API response")
                return None
        else:
            logger.error(f"REST API request failed: {response.status_code} - {response.text}")
            return None
    
    def _check_credits(self, character_count):
        """Check if we have enough Google Cloud TTS credits"""
        current_month = date.today().replace(day=1)
        usage, _ = GoogleCloudTTSUsage.objects.get_or_create(
            month=current_month,
            defaults={'characters_used': 0, 'characters_limit': 10000}
        )

        return (usage.characters_used + character_count) <= usage.characters_limit

    def _update_usage(self, character_count):
        """Update Google Cloud TTS usage tracking"""
        current_month = date.today().replace(day=1)
        usage, _ = GoogleCloudTTSUsage.objects.get_or_create(
            month=current_month,
            defaults={'characters_used': 0, 'characters_limit': 10000}
        )

        usage.characters_used += character_count
        usage.save()

    def get_current_usage(self):
        """Get current month's usage statistics"""
        current_month = date.today().replace(day=1)
        usage, _ = GoogleCloudTTSUsage.objects.get_or_create(
            month=current_month,
            defaults={'characters_used': 0, 'characters_limit': 10000}
        )
        return usage


class ConversationManager:
    """Service for managing conversations and message flow"""
    
    def __init__(self):
        self.gpt_service = GPTService()
        self.tts_service = GoogleCloudTTSService()
    
    def process_user_message(self, conversation, user_message_text):
        """Process a user message and generate AI response with mandatory audio"""
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

            # ALWAYS generate audio for AI responses - this is mandatory
            audio_data = None
            audio_error = None

            try:
                logger.info(f"Generating voice response for bot '{conversation.bot.name}' using voice '{conversation.bot.voice_name}'")
                audio_data = self.tts_service.text_to_speech(
                    ai_response_text, conversation.bot.voice_name
                )

                if audio_data:
                    # Save audio file
                    audio_filename = f"response_{ai_message.id}.mp3"
                    ai_message.audio_file.save(
                        audio_filename,
                        ContentFile(audio_data),
                        save=True
                    )
                    logger.info(f"Voice response generated successfully for message {ai_message.id}")
                else:
                    audio_error = "TTS service returned no audio data"
                    logger.warning(f"Failed to generate voice response: {audio_error}")

            except Exception as audio_exception:
                audio_error = str(audio_exception)
                logger.error(f"Error generating voice response: {audio_error}")

            # Log audio generation status
            if not audio_data:
                logger.warning(f"AI response will be sent without voice audio. Error: {audio_error}")

            return {
                'user_message': user_message,
                'ai_message': ai_message,
                'audio_generated': audio_data is not None,
                'audio_error': audio_error,
                'success': True
            }

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_usage_info(self):
        """Get current Google Cloud TTS usage information"""
        return self.tts_service.get_current_usage()
