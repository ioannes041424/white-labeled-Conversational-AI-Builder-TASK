from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class ConversationalBot(models.Model):
    """Model to store AI bot configurations"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    system_prompt = models.TextField(help_text="System prompt that defines the bot's behavior")
    temperature = models.FloatField(default=0.7, help_text="AI response creativity (0.0-1.0)")
    voice_id = models.CharField(max_length=100, default="21m00Tcm4TlvDq8ikWAM",
                               help_text="ElevenLabs voice ID")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_voice_name(self):
        """Get the human-readable name for the selected voice"""
        from .services import VoiceSelectionService
        return VoiceSelectionService.get_voice_name(self.voice_id)


class Conversation(models.Model):
    """Model to track chat sessions with bots"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bot = models.ForeignKey(ConversationalBot, on_delete=models.CASCADE, related_name='conversations')
    session_id = models.CharField(max_length=100, unique=True)
    started_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-last_activity']

    def __str__(self):
        return f"Conversation with {self.bot.name} - {self.session_id[:8]}"


class Message(models.Model):
    """Model to store individual messages in conversations"""
    MESSAGE_TYPES = [
        ('user', 'User'),
        ('ai', 'AI'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES)
    content = models.TextField()
    audio_file = models.FileField(upload_to='audio/', blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.message_type}: {self.content[:50]}..."


class ElevenLabsUsage(models.Model):
    """Model to track ElevenLabs API usage for credit management"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    month = models.DateField(help_text="Month for which usage is tracked")
    characters_used = models.IntegerField(default=0)
    characters_limit = models.IntegerField(default=10000)  # Free tier limit
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['month']
        ordering = ['-month']

    def __str__(self):
        return f"Usage for {self.month.strftime('%B %Y')}: {self.characters_used}/{self.characters_limit}"

    @property
    def usage_percentage(self):
        return (self.characters_used / self.characters_limit) * 100 if self.characters_limit > 0 else 0

    @property
    def is_near_limit(self):
        return self.usage_percentage >= 80

    @property
    def is_over_limit(self):
        return self.characters_used >= self.characters_limit
