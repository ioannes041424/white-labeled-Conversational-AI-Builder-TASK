from django.contrib import admin
from .models import ConversationalBot, Conversation, Message, GoogleCloudTTSUsage


@admin.register(ConversationalBot)
class ConversationalBotAdmin(admin.ModelAdmin):
    list_display = ['name', 'temperature', 'voice_name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at', 'voice_name']
    search_fields = ['name', 'system_prompt']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'system_prompt', 'is_active')
        }),
        ('AI Configuration', {
            'fields': ('temperature', 'voice_name')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['bot', 'session_id', 'started_at', 'last_activity', 'is_active']
    list_filter = ['is_active', 'started_at', 'bot']
    search_fields = ['session_id', 'bot__name']
    readonly_fields = ['id', 'started_at', 'last_activity']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'message_type', 'content_preview', 'has_audio', 'timestamp']
    list_filter = ['message_type', 'timestamp']
    search_fields = ['content', 'conversation__session_id']
    readonly_fields = ['id', 'timestamp']

    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'

    def has_audio(self, obj):
        return bool(obj.audio_file)
    has_audio.boolean = True
    has_audio.short_description = 'Audio'


@admin.register(GoogleCloudTTSUsage)
class GoogleCloudTTSUsageAdmin(admin.ModelAdmin):
    list_display = ['month', 'characters_used', 'characters_limit', 'usage_percentage', 'last_updated']
    readonly_fields = ['id', 'last_updated', 'usage_percentage']

    def usage_percentage(self, obj):
        return f"{obj.usage_percentage:.1f}%"
    usage_percentage.short_description = 'Usage %'
