# Django core imports for views, HTTP responses, and utilities
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.views import View
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

# Standard library imports
import json
import uuid
import logging

# Local application imports
from .models import ConversationalBot, Conversation, Message
from .forms import BotCreateForm, BotEditForm, ChatMessageForm
from .services import ConversationManager, VoiceSelectionService
from .utils import generate_session_id

# Configure logging for this module
logger = logging.getLogger(__name__)


class BotListView(ListView):
    """
    Display all active conversational bots in a paginated list.

    This is the main landing page where users can see all their created bots,
    access existing conversations, and navigate to bot creation/editing.

    Template: bots/bot_list.html
    Context: 'bots' - paginated list of active ConversationalBot objects
    """
    model = ConversationalBot
    template_name = 'bots/bot_list.html'
    context_object_name = 'bots'
    paginate_by = 12  # Show 12 bots per page for optimal UX

    def get_queryset(self):
        """
        Return only active bots, ordered by creation date (newest first).

        Returns:
            QuerySet: Active ConversationalBot objects ordered by creation date
        """
        return ConversationalBot.objects.filter(is_active=True).order_by('-created_at')

    def get_context_data(self, **kwargs):
        """
        Add additional context data to the template.

        Args:
            **kwargs: Standard context data from parent class

        Returns:
            dict: Enhanced context with additional data for the template
        """
        context = super().get_context_data(**kwargs)
        # Additional context can be added here if needed
        # For example: total bot count, recent activity, etc.
        return context


class BotCreateView(CreateView):
    """
    Handle creation of new conversational bots with AI-powered voice selection.

    This view processes the bot creation form, automatically selects the most
    appropriate voice using AI analysis of the bot's name and system prompt,
    and redirects to the chat interface upon successful creation.

    Template: bots/bot_create.html
    Form: BotCreateForm (name, system_prompt, temperature)
    Success: Redirects to chat interface with the new bot
    """
    model = ConversationalBot
    form_class = BotCreateForm
    template_name = 'bots/bot_create.html'

    def form_valid(self, form):
        """
        Process valid form submission with AI voice selection.

        This method is called when the form passes validation. It:
        1. Uses AI to select the most appropriate voice for the bot
        2. Saves the bot with the selected voice
        3. Shows success message with voice selection details
        4. Redirects to chat interface

        Args:
            form: Valid BotCreateForm instance

        Returns:
            HttpResponseRedirect: Redirect to chat interface
        """
        # Get the bot instance from the form (not yet saved to database)
        bot = form.instance

        # Use AI service to automatically select the best voice
        # This analyzes both the bot name and system prompt to choose
        # from 4 high-quality Google Cloud TTS voices
        selected_voice = VoiceSelectionService.select_voice_for_bot(
            bot.name,
            bot.system_prompt
        )
        bot.voice_name = selected_voice

        # Get human-readable voice name for user feedback
        voice_name = VoiceSelectionService.get_voice_name(selected_voice)

        # Show success message with AI voice selection details
        messages.success(
            self.request,
            f'Bot "{bot.name}" created successfully! AI selected voice: {voice_name}. Starting chat...'
        )

        # Call parent method to save the bot and handle redirect
        return super().form_valid(form)

    def get_success_url(self):
        """
        Determine where to redirect after successful bot creation.

        Returns:
            str: URL to redirect to (chat interface with new bot)
        """
        # Redirect directly to chat interface for immediate interaction
        return reverse('chat', kwargs={'bot_id': self.object.id})

    def form_invalid(self, form):
        """
        Handle invalid form submission.

        Args:
            form: Invalid BotCreateForm instance

        Returns:
            HttpResponse: Re-rendered form with error messages
        """
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class BotEditView(UpdateView):
    """
    Handle editing of existing conversational bots with voice re-selection.

    This view allows users to modify bot configurations including name,
    system prompt, and temperature. When changes are made, the AI voice
    selection service re-evaluates and potentially updates the voice.

    Template: bots/bot_edit.html
    Form: BotEditForm (name, system_prompt, temperature)
    Success: Redirects to bot list with success message
    """
    model = ConversationalBot
    form_class = BotEditForm
    template_name = 'bots/bot_edit.html'
    context_object_name = 'bot'

    def get_success_url(self):
        """
        Determine where to redirect after successful bot update.

        Returns:
            str: URL to redirect to (bot list page)
        """
        return reverse('bot_list')

    def form_valid(self, form):
        """
        Process valid form submission with voice re-selection.

        When a bot is updated, the AI voice selection service re-analyzes
        the bot's characteristics to ensure the voice still matches the
        updated personality and role.

        Args:
            form: Valid BotEditForm instance

        Returns:
            HttpResponseRedirect: Redirect to bot list
        """
        # Get the updated bot instance
        bot = form.instance

        # Re-run AI voice selection in case the bot's characteristics changed
        # This ensures the voice remains appropriate for the updated bot
        selected_voice = VoiceSelectionService.select_voice_for_bot(
            bot.name,
            bot.system_prompt
        )
        bot.voice_name = selected_voice

        # Get human-readable voice name for user feedback
        voice_name = VoiceSelectionService.get_voice_name(selected_voice)

        # Show success message with voice selection details
        messages.success(
            self.request,
            f'Bot "{bot.name}" updated successfully! AI selected voice: {voice_name}'
        )

        # Call parent method to save changes and handle redirect
        return super().form_valid(form)

    def form_invalid(self, form):
        """
        Handle invalid form submission.

        Args:
            form: Invalid BotEditForm instance

        Returns:
            HttpResponse: Re-rendered form with error messages
        """
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class BotDeleteView(DeleteView):
    """
    Handle bot deletion with soft delete functionality.

    This view provides a confirmation page for bot deletion and implements
    soft delete (marking as inactive) rather than hard delete to preserve
    conversation history and allow potential recovery.

    Template: bots/bot_confirm_delete.html
    Success: Redirects to bot list with success message
    """
    model = ConversationalBot
    template_name = 'bots/bot_confirm_delete.html'
    success_url = reverse_lazy('bot_list')
    context_object_name = 'bot'

    def delete(self, request, *args, **kwargs):
        """
        Perform soft delete of the bot.

        Instead of actually deleting the bot from the database, this method
        marks it as inactive. This preserves all conversation history and
        allows for potential recovery if needed.

        Args:
            request: HTTP request object
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments

        Returns:
            HttpResponseRedirect: Redirect to bot list
        """
        bot = self.get_object()
        bot.is_active = False  # Soft delete - preserve data but hide from users
        bot.save()

        messages.success(request, f'Bot "{bot.name}" deleted successfully!')
        return redirect(self.success_url)


class ChatView(View):
    """
    Main chat interface for conversing with a bot.

    This view handles the chat interface where users interact with their bots.
    It manages conversation sessions, loads message history, and provides the
    real-time chat experience with both text and voice capabilities.

    Template: bots/chat.html
    Context: bot, conversation, messages, form, session_id
    """
    template_name = 'bots/chat.html'

    def get(self, request, bot_id):
        """
        Display the chat interface for a specific bot.

        This method:
        1. Retrieves the bot or returns 404 if not found/inactive
        2. Manages conversation sessions using browser session storage
        3. Creates or retrieves existing conversation
        4. Loads message history for context
        5. Provides form for new messages

        Args:
            request: HTTP request object
            bot_id: UUID of the bot to chat with

        Returns:
            HttpResponse: Rendered chat interface
        """
        # Get the bot or return 404 if not found or inactive
        bot = get_object_or_404(ConversationalBot, id=bot_id, is_active=True)

        # Session management: Get or create conversation session
        # This allows conversation persistence across browser sessions
        session_key = f'conversation_{bot_id}'
        session_id = request.session.get(session_key)

        if not session_id:
            # Generate new session ID for first-time visitors
            session_id = generate_session_id()
            request.session[session_key] = session_id

        # Get or create conversation record in database
        conversation, created = Conversation.objects.get_or_create(
            bot=bot,
            session_id=session_id,
            defaults={'is_active': True}
        )

        # Load message history for this conversation
        # Ordered chronologically to maintain conversation flow
        messages_list = conversation.messages.order_by('timestamp')

        # Prepare context for template rendering
        context = {
            'bot': bot,                    # Bot configuration and details
            'conversation': conversation,   # Current conversation session
            'messages': messages_list,     # Historical messages
            'form': ChatMessageForm(),     # Form for new messages
            'session_id': session_id       # Session ID for AJAX requests
        }

        return render(request, self.template_name, context)


@method_decorator(csrf_exempt, name='dispatch')
class SendMessageView(View):
    """AJAX endpoint for chat messages"""

    def post(self, request, bot_id):
        try:
            bot = get_object_or_404(ConversationalBot, id=bot_id, is_active=True)

            # Parse JSON data
            data = json.loads(request.body)
            message_text = data.get('message', '').strip()
            session_id = data.get('session_id')

            if not message_text:
                return JsonResponse({'success': False, 'error': 'Message cannot be empty'})

            if not session_id:
                return JsonResponse({'success': False, 'error': 'Invalid session'})

            # Get conversation
            conversation = get_object_or_404(
                Conversation,
                bot=bot,
                session_id=session_id,
                is_active=True
            )

            # Process message using ConversationManager
            conversation_manager = ConversationManager()
            result = conversation_manager.process_user_message(conversation, message_text)

            if result['success']:
                user_message = result['user_message']
                ai_message = result['ai_message']

                response_data = {
                    'success': True,
                    'user_message': {
                        'id': str(user_message.id),
                        'content': user_message.content,
                        'timestamp': user_message.timestamp.strftime('%H:%M')
                    },
                    'ai_message': {
                        'id': str(ai_message.id),
                        'content': ai_message.content,
                        'timestamp': ai_message.timestamp.strftime('%H:%M'),
                        'audio_url': ai_message.audio_file.url if ai_message.audio_file else None
                    },
                    'audio_generated': result.get('audio_generated', False),
                    'audio_error': result.get('audio_error', None)
                }

                return JsonResponse(response_data)
            else:
                return JsonResponse({
                    'success': False,
                    'error': result.get('error', 'Failed to process message')
                })

        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class ClearConversationView(View):
    """Clear conversation history"""

    def post(self, request, bot_id):
        try:
            bot = get_object_or_404(ConversationalBot, id=bot_id, is_active=True)
            session_id = request.session.get(f'conversation_{bot_id}')

            if session_id:
                # Mark old conversation as inactive
                Conversation.objects.filter(
                    bot=bot,
                    session_id=session_id
                ).update(is_active=False)

                # Create new session
                new_session_id = generate_session_id()
                request.session[f'conversation_{bot_id}'] = new_session_id

                messages.success(request, 'Conversation cleared successfully!')

            return redirect('chat', bot_id=bot_id)

        except Exception as e:
            messages.error(request, f'Error clearing conversation: {str(e)}')
            return redirect('chat', bot_id=bot_id)


# Removed unused APITestView and QuickTestView classes
# These were development/debugging utilities that were never connected to URLs
# and had no corresponding templates. The core application functionality
# is handled by the main chat interface and bot management views above.
