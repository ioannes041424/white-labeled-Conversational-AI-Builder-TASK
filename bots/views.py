from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.views import View
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import uuid
import logging
from .models import ConversationalBot, Conversation, Message
from .forms import BotCreateForm, BotEditForm, ChatMessageForm
from .services import ConversationManager, VoiceSelectionService, GPTService, GoogleCloudTTSService
from .utils import generate_session_id

logger = logging.getLogger(__name__)


class BotListView(ListView):
    """Display all user's bots"""
    model = ConversationalBot
    template_name = 'bots/bot_list.html'
    context_object_name = 'bots'
    paginate_by = 12

    def get_queryset(self):
        return ConversationalBot.objects.filter(is_active=True).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        return context


class BotCreateView(CreateView):
    """Form to create new bot"""
    model = ConversationalBot
    form_class = BotCreateForm
    template_name = 'bots/bot_create.html'

    def form_valid(self, form):
        # Automatically select the best voice for this bot
        bot = form.instance
        selected_voice = VoiceSelectionService.select_voice_for_bot(
            bot.name,
            bot.system_prompt
        )
        bot.voice_name = selected_voice

        # Get voice name for the success message
        voice_name = VoiceSelectionService.get_voice_name(selected_voice)

        messages.success(
            self.request,
            f'Bot "{bot.name}" created successfully! AI selected voice: {voice_name}. Starting chat...'
        )
        return super().form_valid(form)

    def get_success_url(self):
        # Redirect to chat interface instead of bot list
        return reverse('chat', kwargs={'bot_id': self.object.id})

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class BotEditView(UpdateView):
    """Form to edit existing bot"""
    model = ConversationalBot
    form_class = BotEditForm
    template_name = 'bots/bot_edit.html'
    context_object_name = 'bot'

    def get_success_url(self):
        return reverse('bot_list')

    def form_valid(self, form):
        # Re-select voice if name or system prompt changed
        bot = form.instance
        selected_voice = VoiceSelectionService.select_voice_for_bot(
            bot.name,
            bot.system_prompt
        )
        bot.voice_name = selected_voice

        # Get voice name for the success message
        voice_name = VoiceSelectionService.get_voice_name(selected_voice)

        messages.success(
            self.request,
            f'Bot "{bot.name}" updated successfully! AI selected voice: {voice_name}'
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class BotDeleteView(DeleteView):
    """Delete bot confirmation"""
    model = ConversationalBot
    template_name = 'bots/bot_confirm_delete.html'
    success_url = reverse_lazy('bot_list')
    context_object_name = 'bot'

    def delete(self, request, *args, **kwargs):
        bot = self.get_object()
        bot.is_active = False  # Soft delete
        bot.save()
        messages.success(request, f'Bot "{bot.name}" deleted successfully!')
        return redirect(self.success_url)


class ChatView(View):
    """Main chat interface"""
    template_name = 'bots/chat.html'

    def get(self, request, bot_id):
        bot = get_object_or_404(ConversationalBot, id=bot_id, is_active=True)

        # Get or create conversation session
        session_id = request.session.get(f'conversation_{bot_id}')
        if not session_id:
            session_id = generate_session_id()
            request.session[f'conversation_{bot_id}'] = session_id

        conversation, created = Conversation.objects.get_or_create(
            bot=bot,
            session_id=session_id,
            defaults={'is_active': True}
        )

        # Get message history
        messages_list = conversation.messages.order_by('timestamp')

        context = {
            'bot': bot,
            'conversation': conversation,
            'messages': messages_list,
            'form': ChatMessageForm(),
            'session_id': session_id
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


class APITestView(View):
    """Simple API test interface"""
    template_name = 'bots/api_test.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        try:
            test_message = request.POST.get('test_message', '').strip()
            if not test_message:
                return JsonResponse({'success': False, 'error': 'Please enter a test message'})

            # Test GitHub Models API
            gpt_service = GPTService()
            if not gpt_service.client:
                return JsonResponse({'success': False, 'error': 'GitHub Models API not initialized'})

            # Create a simple test conversation
            from azure.ai.inference.models import SystemMessage, UserMessage
            messages = [
                SystemMessage(content="You are a helpful assistant. Respond briefly and clearly."),
                UserMessage(content=test_message)
            ]

            response = gpt_service.client.complete(
                messages=messages,
                model=gpt_service.model,
                temperature=0.7,
                max_tokens=200,
                top_p=1.0
            )

            ai_response = response.choices[0].message.content.strip()

            # Test Google Cloud TTS API
            tts_service = GoogleCloudTTSService()
            audio_success = False
            audio_error = None

            try:
                audio_data = tts_service.text_to_speech(ai_response[:100])  # Limit to 100 chars for test
                audio_success = audio_data is not None
                if not audio_success:
                    audio_error = "Failed to generate audio"
            except Exception as e:
                audio_error = str(e)

            return JsonResponse({
                'success': True,
                'user_message': test_message,
                'ai_response': ai_response,
                'audio_success': audio_success,
                'audio_error': audio_error,
                'github_model': gpt_service.model
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': f'API Test Error: {str(e)}'})


@method_decorator(csrf_exempt, name='dispatch')
class QuickTestView(View):
    """Quick AJAX test endpoint"""

    def post(self, request):
        try:
            data = json.loads(request.body)
            test_message = data.get('message', '').strip()

            if not test_message:
                return JsonResponse({'success': False, 'error': 'Message required'})

            # Quick test of GitHub Models API
            gpt_service = GPTService()

            from azure.ai.inference.models import SystemMessage, UserMessage
            messages = [
                SystemMessage(content="You are a helpful assistant."),
                UserMessage(content=test_message)
            ]

            response = gpt_service.client.complete(
                messages=messages,
                model=gpt_service.model,
                temperature=0.7,
                max_tokens=150
            )

            return JsonResponse({
                'success': True,
                'response': response.choices[0].message.content.strip(),
                'model': gpt_service.model
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
