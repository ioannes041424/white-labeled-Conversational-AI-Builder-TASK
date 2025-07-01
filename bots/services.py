# Standard library imports
import json  # Used for REST API calls to Google Cloud TTS
import requests  # Used for HTTP requests to Google Cloud TTS API
import re  # Used for regex pattern matching in markdown processing
import logging

# Django imports
from django.conf import settings
from django.core.files.base import ContentFile

# Azure AI SDK imports for GitHub Models integration
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

# Local imports
from .models import Message

# Configure logging for this module
logger = logging.getLogger(__name__)


def markdown_to_clean_text(text):
    """
    Convert markdown text to clean, readable text for voice synthesis.

    This function is critical for the TTS pipeline as it ensures that AI-generated
    markdown content is converted to natural speech. It removes all formatting,
    emojis, and special characters while preserving the actual readable content.

    Processing Steps:
    1. Remove emojis and Unicode symbols that shouldn't be spoken
    2. Strip markdown formatting (bold, italic, headers, links, etc.)
    3. Clean up code blocks and inline code
    4. Normalize whitespace and add natural speech pauses
    5. Remove any remaining special characters

    Args:
        text (str): Raw markdown text from AI response

    Returns:
        str: Clean text suitable for text-to-speech synthesis

    Example:
        Input:  "**Hello!** Here's a `code` example:\n```python\nprint('hi')\n```"
        Output: "Hello! Here's a code example."
    """
    if not text:
        return ""

    # Step 1: Remove emojis and Unicode symbols that shouldn't be read aloud
    # These regex patterns cover most emoji ranges and symbols
    text = re.sub(r'[\U0001F600-\U0001F64F]', '', text)  # Emoticons
    text = re.sub(r'[\U0001F300-\U0001F5FF]', '', text)  # Symbols & pictographs
    text = re.sub(r'[\U0001F680-\U0001F6FF]', '', text)  # Transport & map symbols
    text = re.sub(r'[\U0001F1E0-\U0001F1FF]', '', text)  # Flags (iOS)
    text = re.sub(r'[\U00002702-\U000027B0]', '', text)  # Dingbats
    text = re.sub(r'[\U000024C2-\U0001F251]', '', text)  # Enclosed characters
    text = re.sub(r'[\U0001F900-\U0001F9FF]', '', text)  # Supplemental Symbols and Pictographs
    text = re.sub(r'[\U0001FA70-\U0001FAFF]', '', text)  # Symbols and Pictographs Extended-A

    # Additional emoji cleanup for common ranges
    text = re.sub(r'[😀-🙏🌀-🗿🚀-🛿🇀-🇿♀-♿⚀-⚿✀-➿]', '', text)

    # Step 2: Remove code blocks first (```code```) - these shouldn't be spoken
    text = re.sub(r'```[\s\S]*?```', '', text)

    # Step 3: Remove inline code (`code`) but keep the content
    text = re.sub(r'`([^`]*)`', r'\1', text)

    # Step 4: Remove markdown formatting while preserving content
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # **bold** -> content
    text = re.sub(r'__(.*?)__', r'\1', text)      # __bold__ -> content
    text = re.sub(r'\*(.*?)\*', r'\1', text)      # *italic* -> content
    text = re.sub(r'_(.*?)_', r'\1', text)        # _italic_ -> content

    # Step 5: Remove headers (# ## ###) - just keep the text
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # Step 6: Remove links but keep the text [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

    # Step 7: Remove list markers (- * + 1. 2. etc.)
    text = re.sub(r'^[\s]*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[\s]*\d+\.\s+', '', text, flags=re.MULTILINE)

    # Step 8: Remove blockquotes (>)
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)

    # Step 9: Remove horizontal rules (--- or ***)
    text = re.sub(r'^[-*]{3,}$', '', text, flags=re.MULTILINE)

    # Step 10: Clean up whitespace and normalize line breaks
    text = re.sub(r'\n\s*\n', '\n\n', text)  # Multiple line breaks to double
    text = re.sub(r'\n{3,}', '\n\n', text)   # More than 2 line breaks to 2
    text = text.strip()

    # Step 11: Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)

    # Step 12: Add natural pauses for better speech synthesis
    # Replace line breaks with periods for natural speech pauses
    text = text.replace('\n\n', '. ')  # Paragraph breaks become longer pauses
    text = text.replace('\n', '. ')    # Line breaks become shorter pauses

    # Step 13: Clean up any remaining formatting artifacts
    text = re.sub(r'[*_`#>]', '', text)

    # Step 14: Remove any remaining special characters that might be read as symbols
    # Keep only alphanumeric, whitespace, and basic punctuation
    text = re.sub(r'[^\w\s\.,!?;:\'"()-]', '', text)

    return text.strip()


class VoiceSelectionService:
    """
    AI-powered service for intelligently selecting Google Cloud Text-to-Speech voices.

    This service uses GPT-4 to analyze bot characteristics (name and system prompt)
    and automatically select the most appropriate voice from a curated set of 4
    high-quality Google Cloud TTS Chirp3-HD voices.

    Architecture:
    - Uses GitHub Models GPT-4 for intelligent voice matching
    - Curated selection of 4 premium voices (2 male, 2 female)
    - Fallback system for when AI selection fails
    - Voice profiles with personality and tone characteristics

    Voice Selection Process:
    1. Analyze bot name for gender/personality hints
    2. Analyze system prompt for role and tone requirements
    3. Use AI to match characteristics to voice profiles
    4. Return the most appropriate voice ID
    """

    # Curated selection of the 4 best Google Cloud TTS voices
    # These are premium Chirp3-HD voices chosen for naturalness and quality
    VOICE_PROFILES = {
        # Female voices - natural and expressive
        'en-US-Chirp3-HD-Achernar': {
            'name': 'Achernar',
            'gender': 'female',
            'age': 'adult',
            'tone': 'friendly',
            'accent': 'american',
            'personality': ['helpful', 'warm', 'conversational', 'natural'],
            'description': 'Female voice with friendly, warm tone - ideal for customer service, assistants, and conversational bots'
        },
        'en-US-Chirp3-HD-Leda': {
            'name': 'Leda',
            'gender': 'female',
            'age': 'adult',
            'tone': 'elegant',
            'accent': 'american',
            'personality': ['sophisticated', 'professional', 'polished', 'natural'],
            'description': 'Female voice with elegant, sophisticated tone - ideal for professional, business, and educational bots'
        },

        # Male voices - natural and authoritative
        'en-US-Chirp3-HD-Orus': {
            'name': 'Orus',
            'gender': 'male',
            'age': 'adult',
            'tone': 'warm',
            'accent': 'american',
            'personality': ['warm', 'friendly', 'supportive', 'natural'],
            'description': 'Male voice with warm, approachable tone - ideal for coaching, support, and friendly assistant bots'
        },
        'en-US-Chirp3-HD-Charon': {
            'name': 'Charon',
            'gender': 'male',
            'age': 'adult',
            'tone': 'authoritative',
            'accent': 'american',
            'personality': ['authoritative', 'professional', 'confident', 'natural'],
            'description': 'Male voice with authoritative, confident tone - ideal for expert, advisor, and professional bots'
        }
    }

    @classmethod
    def select_voice_for_bot(cls, bot_name, system_prompt):
        """
        Use AI to intelligently select the most appropriate voice for a bot.

        This method leverages GPT-4 to analyze both the bot's name and system prompt
        to determine the most suitable voice from the curated selection. The AI
        considers factors like gender hints, personality traits, professional tone,
        and use case to make an intelligent matching decision.

        Process:
        1. Initialize GitHub Models GPT-4 client
        2. Create structured prompt with voice options and analysis criteria
        3. Send bot characteristics to AI for analysis
        4. Parse AI response to extract voice selection
        5. Validate selection and fallback if needed

        Args:
            bot_name (str): Name of the bot (may contain gender/personality hints)
            system_prompt (str): Bot's system prompt defining role and personality

        Returns:
            str: Google Cloud TTS voice ID (e.g., 'en-US-Chirp3-HD-Achernar')

        Example:
            select_voice_for_bot("Sarah Assistant", "You are a friendly customer service rep")
            # Returns: 'en-US-Chirp3-HD-Achernar' (female, friendly)
        """
        logger.info(f"🎯 AI selecting voice for bot: '{bot_name}'")

        try:
            # Import here to avoid circular imports with Django settings
            from django.conf import settings
            from azure.ai.inference import ChatCompletionsClient
            from azure.ai.inference.models import SystemMessage, UserMessage
            from azure.core.credentials import AzureKeyCredential

            # Check if GitHub token is available for AI selection
            if not settings.GITHUB_TOKEN:
                logger.warning("GitHub token not available, using rule-based fallback")
                return cls._simple_fallback(bot_name, system_prompt)

            # Initialize GitHub Models client for GPT-4 access
            client = ChatCompletionsClient(
                endpoint="https://models.github.ai/inference",
                credential=AzureKeyCredential(settings.GITHUB_TOKEN),
            )

            # Create structured AI prompt for voice selection
            # This prompt provides clear options and analysis criteria
            system_message = """You are an expert voice selector for conversational AI bots. Choose the BEST voice from these 4 premium options:

1. en-US-Chirp3-HD-Achernar (female, friendly, warm, conversational)
   - Best for: Customer service, assistants, helpful bots

2. en-US-Chirp3-HD-Leda (female, elegant, sophisticated, professional)
   - Best for: Business, professional, educational bots

3. en-US-Chirp3-HD-Orus (male, warm, friendly, supportive)
   - Best for: Coaching, support, friendly assistant bots

4. en-US-Chirp3-HD-Charon (male, authoritative, professional, confident)
   - Best for: Expert advisors, professional consultants, authoritative bots

Analyze BOTH the bot name AND the system prompt to determine:
- Gender preference (from name hints or role requirements)
- Personality type (professional/friendly/authoritative/warm)
- Use case (business/casual/support/educational)
- Tone requirements (formal/casual/supportive/confident)

Return ONLY the voice ID. Example: en-US-Chirp3-HD-Achernar"""

            # Create user message with bot characteristics for analysis
            user_message = f"""Bot Name: "{bot_name}"

System Prompt: "{system_prompt}"

Based on the bot's name and role/personality described in the system prompt, which voice fits best?"""

            # Prepare messages for AI completion
            messages = [
                SystemMessage(content=system_message),
                UserMessage(content=user_message)
            ]

            # Send request to AI for voice selection
            logger.info(f"📤 Sending AI voice selection request for '{bot_name}'")

            response = client.complete(
                messages=messages,
                model="openai/gpt-4o-mini",  # Use mini for faster, cost-effective responses
                temperature=0.1,  # Low temperature for consistent, focused responses
                max_tokens=150,   # Short response expected (just voice ID)
                top_p=0.9        # Focused sampling for better consistency
            )

            # Process AI response
            if response and response.choices and response.choices[0].message.content:
                ai_response = response.choices[0].message.content.strip()
                logger.info(f"📥 AI raw response: '{ai_response}'")

                # Extract and validate voice ID from AI response
                selected_voice = cls._extract_voice_from_response(ai_response)

                if selected_voice:
                    voice_name = cls.VOICE_PROFILES[selected_voice]['name']
                    logger.info(f"✅ AI selected voice: {voice_name} ({selected_voice}) for '{bot_name}'")
                    return selected_voice
                else:
                    logger.warning(f"⚠️ AI returned invalid voice: '{ai_response}', using fallback")
                    return cls._simple_fallback(bot_name, system_prompt)
            else:
                logger.warning("⚠️ AI returned empty response, using fallback")
                return cls._simple_fallback(bot_name, system_prompt)

        except Exception as e:
            logger.error(f"❌ Error in AI voice selection: {str(e)}")
            return cls._simple_fallback(bot_name, system_prompt)

    @classmethod
    def _extract_voice_from_response(cls, ai_response):
        """
        Extract and validate voice ID from AI response.

        The AI may return the voice ID in various formats, so this method
        handles different response patterns and extracts the valid voice ID.

        Args:
            ai_response (str): Raw response from AI

        Returns:
            str or None: Valid voice ID if found, None otherwise
        """
        # Clean the response by removing quotes and extra whitespace
        cleaned = ai_response.strip().replace('"', '').replace("'", "")

        # First, check for exact voice ID matches (most reliable)
        for voice_id in cls.VOICE_PROFILES.keys():
            if voice_id in cleaned:
                return voice_id

        # Fallback: Check for voice name matches (case-insensitive)
        cleaned_lower = cleaned.lower()
        if "achernar" in cleaned_lower:
            return "en-US-Chirp3-HD-Achernar"
        elif "leda" in cleaned_lower:
            return "en-US-Chirp3-HD-Leda"
        elif "orus" in cleaned_lower:
            return "en-US-Chirp3-HD-Orus"
        elif "charon" in cleaned_lower:
            return "en-US-Chirp3-HD-Charon"

        # No valid voice found
        return None

    @classmethod
    def _simple_fallback(cls, bot_name, system_prompt):
        """
        Rule-based fallback voice selection when AI is unavailable.

        This method provides a simple but effective fallback using basic
        pattern matching on bot names and system prompts. While not as
        sophisticated as AI selection, it provides reasonable defaults.

        Selection Logic:
        1. Check for obvious gender indicators in bot name
        2. Analyze system prompt for professional vs. casual tone
        3. Apply default voice based on detected characteristics

        Args:
            bot_name (str): Name of the bot
            system_prompt (str): Bot's system prompt

        Returns:
            str: Voice ID selected using rule-based logic
        """
        logger.info(f"🔄 Using rule-based fallback for '{bot_name}'")

        # Convert to lowercase for case-insensitive matching
        name_lower = bot_name.lower()
        prompt_lower = system_prompt.lower()

        # Check for obvious male name indicators
        male_indicators = ['john', 'mike', 'alex', 'david', 'james', 'coach', 'mr', 'sir']
        if any(name in name_lower for name in male_indicators):
            # Choose male voice based on professional context
            if any(term in prompt_lower for term in ['professional', 'business', 'manager', 'expert', 'advisor']):
                return "en-US-Chirp3-HD-Charon"  # Authoritative male
            else:
                return "en-US-Chirp3-HD-Orus"    # Warm male

        # Check for obvious female name indicators
        female_indicators = ['sarah', 'emma', 'lisa', 'maya', 'anna', 'assistant', 'ms', 'mrs']
        if any(name in name_lower for name in female_indicators):
            # Choose female voice based on professional context
            if any(term in prompt_lower for term in ['professional', 'business', 'manager', 'expert', 'advisor']):
                return "en-US-Chirp3-HD-Leda"      # Elegant female
            else:
                return "en-US-Chirp3-HD-Achernar"  # Friendly female

        # No clear gender indicators - choose based on context
        if any(term in prompt_lower for term in ['professional', 'business', 'manager', 'expert', 'advisor']):
            return "en-US-Chirp3-HD-Leda"      # Professional default (female)
        else:
            return "en-US-Chirp3-HD-Achernar"  # Friendly default (female)

    @classmethod
    def get_voice_name(cls, voice_id):
        """
        Get the human-readable name for a voice ID.

        Args:
            voice_id (str): Google Cloud TTS voice ID

        Returns:
            str: Human-readable voice name or 'Unknown' if not found
        """
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
            model = "openai/gpt-4o"  # Correct format: publisher/model_name

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
                max_tokens=600,
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
        # Create enhanced system prompt that includes the bot's name
        enhanced_system_prompt = f"Your name is {bot.name}. Your system prompt is: {bot.system_prompt}"

        messages = [
            SystemMessage(content=enhanced_system_prompt)
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
    



