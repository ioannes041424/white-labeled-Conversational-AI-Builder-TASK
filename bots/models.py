# Django core imports for database models and utilities
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class ConversationalBot(models.Model):
    """
    Core model representing an AI chatbot configuration.

    This model stores all the essential information needed to create and manage
    a conversational AI bot, including its personality (system prompt), voice
    characteristics, and behavioral parameters.

    Architecture Notes:
    - Uses UUID as primary key for better security and scalability
    - Integrates with GitHub Models GPT-4 for AI responses
    - Integrates with Google Cloud Text-to-Speech for voice synthesis
    - Supports AI-powered voice selection based on bot characteristics
    """

    # Primary key: UUID for security and distributed system compatibility
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the bot (UUID format for security)"
    )

    # Bot identity and configuration
    name = models.CharField(
        max_length=200,
        help_text="Human-readable name for the bot (e.g., 'Customer Support Assistant')"
    )

    # AI behavior configuration - this is the core of the bot's personality
    system_prompt = models.TextField(
        help_text="System prompt that defines the bot's behavior, personality, and role. "
                 "This is sent to GPT-4 to establish the bot's character and response style."
    )

    # AI response creativity control (0.0 = deterministic, 1.0 = very creative)
    temperature = models.FloatField(
        default=0.7,
        help_text="AI response creativity level (0.0-1.0). Lower values = more consistent, "
                 "higher values = more creative and varied responses"
    )

    # Voice synthesis configuration - automatically selected by AI
    voice_name = models.CharField(
        max_length=100,
        default="en-US-Chirp3-HD-Achernar",
        help_text="Google Cloud Text-to-Speech Chirp3-HD voice name. "
                 "Automatically selected by AI based on bot name and system prompt."
    )

    # Metadata timestamps for tracking and auditing
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the bot was first created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the bot configuration was last modified"
    )

    # Soft delete functionality - allows deactivation without data loss
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the bot is active and available for conversations. "
                 "Inactive bots are hidden from users but data is preserved."
    )

    class Meta:
        # Order bots by creation date (newest first) for better UX
        ordering = ['-created_at']
        verbose_name = "Conversational Bot"
        verbose_name_plural = "Conversational Bots"

    def __str__(self):
        """String representation for admin interface and debugging"""
        return f"{self.name} ({'Active' if self.is_active else 'Inactive'})"

    def get_voice_display_name(self):
        """
        Get human-readable voice name for display in UI.

        Returns:
            str: Formatted voice name with gender and personality traits
        """
        from .services import VoiceSelectionService
        return VoiceSelectionService.get_voice_name(self.voice_name)

    @property
    def conversation_count(self):
        """Get the total number of conversations for this bot"""
        return self.conversations.filter(is_active=True).count()

    @property
    def message_count(self):
        """Get the total number of messages across all conversations for this bot"""
        return sum(conv.messages.count() for conv in self.conversations.filter(is_active=True))


class Conversation(models.Model):
    """
    Model representing a chat session between a user and a bot.

    Each conversation maintains context and message history for a specific
    interaction session. Sessions are identified by unique session IDs
    stored in the user's browser session.

    Architecture Notes:
    - One-to-many relationship with ConversationalBot
    - One-to-many relationship with Message
    - Session-based identification (no user authentication required)
    - Supports conversation persistence and history
    """

    # Primary key: UUID for consistency with other models
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the conversation session"
    )

    # Foreign key relationship to the bot being conversed with
    bot = models.ForeignKey(
        ConversationalBot,
        on_delete=models.CASCADE,
        related_name='conversations',
        help_text="The bot that this conversation is with. "
                 "Cascade delete ensures conversations are removed when bot is deleted."
    )

    # Session identification - links to browser session
    session_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique session identifier stored in user's browser session. "
                 "Allows conversation persistence without user authentication."
    )

    # Conversation lifecycle timestamps
    started_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the conversation was first initiated"
    )
    last_activity = models.DateTimeField(
        auto_now=True,
        help_text="Last time a message was sent in this conversation. "
                 "Used for sorting and cleanup of old conversations."
    )

    # Conversation state management
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the conversation is active. "
                 "Inactive conversations are hidden but preserved for history."
    )

    class Meta:
        # Order by most recent activity for better UX
        ordering = ['-last_activity']
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"

    def __str__(self):
        """String representation showing bot name and session ID"""
        return f"Conversation with {self.bot.name} - {self.session_id[:8]}..."


class Message(models.Model):
    """
    Model representing individual messages within a conversation.

    Stores both user inputs and AI responses, along with associated
    audio files for AI responses. Each message is linked to a specific
    conversation and maintains chronological order.

    Architecture Notes:
    - Supports both text and audio content
    - AI messages automatically get audio files via TTS
    - Chronological ordering for conversation flow
    - Cascade delete with conversation cleanup
    """

    # Message type choices - defines who sent the message
    MESSAGE_TYPES = [
        ('user', 'User'),  # Human user input (text or speech-to-text)
        ('ai', 'AI'),      # AI bot response (with mandatory audio)
    ]

    # Primary key: UUID for consistency and security
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the message"
    )

    # Foreign key relationship to the conversation this message belongs to
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
        help_text="The conversation this message is part of. "
                 "Cascade delete ensures messages are removed with conversation."
    )

    # Message metadata - who sent it (user or AI)
    message_type = models.CharField(
        max_length=10,
        choices=MESSAGE_TYPES,
        help_text="Whether this message was sent by the user or generated by AI"
    )

    # Message content - the actual text of the message
    content = models.TextField(
        help_text="The text content of the message. For AI messages, this may contain "
                 "markdown formatting that gets converted to clean text for TTS."
    )

    # Audio file - generated for AI responses using Google Cloud TTS
    audio_file = models.FileField(
        upload_to='audio/',
        blank=True,
        null=True,
        help_text="Audio file containing the spoken version of AI responses. "
                 "Generated automatically using Google Cloud Text-to-Speech API."
    )

    # Message timestamp for chronological ordering
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="When the message was created"
    )

    class Meta:
        # Order messages chronologically within conversations
        ordering = ['timestamp']
        verbose_name = "Message"
        verbose_name_plural = "Messages"

    def __str__(self):
        """String representation showing message type and content preview"""
        return f"{self.message_type.upper()}: {self.content[:50]}..."


class GoogleCloudTTSUsage(models.Model):
    """
    Model to track Google Cloud Text-to-Speech API usage for monitoring and cost control.

    Tracks character usage per month to monitor API consumption and provide
    warnings when approaching usage limits. This helps with cost management
    and prevents unexpected charges.

    Architecture Notes:
    - Monthly tracking granularity for cost management
    - Configurable warning limits for proactive monitoring
    - Properties for easy usage percentage calculations
    - Unique constraint ensures one record per month

    Note: With unlimited API key, this is primarily for monitoring rather than limiting.
    """

    # Primary key: UUID for consistency with other models
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the usage record"
    )

    # Month being tracked - used as natural key for uniqueness
    month = models.DateField(
        help_text="Month for which usage is tracked (YYYY-MM-01 format)"
    )

    # Usage tracking - characters processed through TTS API
    characters_used = models.IntegerField(
        default=0,
        help_text="Total number of characters processed through Google Cloud TTS this month"
    )

    # Warning threshold for usage monitoring
    characters_limit = models.IntegerField(
        default=10000,
        help_text="Warning limit for usage tracking. Alerts are triggered when approaching this limit."
    )

    # Last update timestamp for tracking when usage was last calculated
    last_updated = models.DateTimeField(
        auto_now=True,
        help_text="When this usage record was last updated"
    )

    class Meta:
        # Ensure only one record per month
        unique_together = ['month']
        # Order by most recent month first
        ordering = ['-month']
        verbose_name = "Google Cloud TTS Usage"
        verbose_name_plural = "Google Cloud TTS Usage Records"

    def __str__(self):
        """String representation showing month and usage statistics"""
        return f"Usage for {self.month.strftime('%B %Y')}: {self.characters_used:,}/{self.characters_limit:,}"

    @property
    def usage_percentage(self):
        """
        Calculate usage as a percentage of the limit.

        Returns:
            float: Usage percentage (0-100+)
        """
        return (self.characters_used / self.characters_limit) * 100 if self.characters_limit > 0 else 0

    @property
    def is_near_limit(self):
        """
        Check if usage is approaching the warning limit (80% threshold).

        Returns:
            bool: True if usage is at or above 80% of limit
        """
        return self.usage_percentage >= 80

    @property
    def is_over_limit(self):
        """
        Check if usage has exceeded the warning limit.

        Returns:
            bool: True if usage exceeds the set limit
        """
        return self.characters_used >= self.characters_limit

    def add_usage(self, characters):
        """
        Add character usage to this month's total.

        Args:
            characters (int): Number of characters to add to usage
        """
        self.characters_used += characters
        self.save(update_fields=['characters_used', 'last_updated'])
