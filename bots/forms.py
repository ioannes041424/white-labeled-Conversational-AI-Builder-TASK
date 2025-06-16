from django import forms
from .models import ConversationalBot


class BotCreateForm(forms.ModelForm):
    """Form for creating new conversational bots"""
    
    class Meta:
        model = ConversationalBot
        fields = ['name', 'system_prompt', 'temperature']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter bot name (e.g., Customer Support Bot)',
                'maxlength': 200
            }),
            'system_prompt': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8,
                'placeholder': 'Define your bot\'s personality and behavior...\n\nExample:\nYou are a helpful customer support assistant. You are friendly, professional, and always try to solve customer problems. Keep responses concise but informative.',
            }),
            'temperature': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0.0,
                'max': 1.0,
                'step': 0.1,
                'value': 0.7
            }),

        }
        labels = {
            'name': 'Bot Name',
            'system_prompt': 'System Prompt',
            'temperature': 'Creativity Level (0.0 = Focused, 1.0 = Creative)'
        }
        help_texts = {
            'name': 'Give your bot a descriptive name',
            'system_prompt': 'This defines how your bot will behave and respond to users. The AI will automatically select the best voice based on the bot\'s personality.',
            'temperature': 'Controls response creativity. Lower values = more focused, higher values = more creative'
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
            if len(name) < 2:
                raise forms.ValidationError("Bot name must be at least 2 characters long.")
        return name

    def clean_system_prompt(self):
        system_prompt = self.cleaned_data.get('system_prompt')
        if system_prompt:
            system_prompt = system_prompt.strip()
            if len(system_prompt) < 10:
                raise forms.ValidationError("System prompt must be at least 10 characters long.")
        return system_prompt

    def clean_temperature(self):
        temperature = self.cleaned_data.get('temperature')
        if temperature is not None:
            if temperature < 0.0 or temperature > 1.0:
                raise forms.ValidationError("Temperature must be between 0.0 and 1.0.")
        return temperature


class BotEditForm(BotCreateForm):
    """Form for editing existing conversational bots"""
    
    class Meta(BotCreateForm.Meta):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add any edit-specific customizations here
        self.fields['name'].help_text = 'Update your bot\'s name'


class ChatMessageForm(forms.Form):
    """Form for sending chat messages"""
    message = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Type your message...',
            'autocomplete': 'off',
            'maxlength': 1000
        }),
        max_length=1000,
        required=True
    )

    def clean_message(self):
        message = self.cleaned_data.get('message')
        if message:
            message = message.strip()
            if len(message) < 1:
                raise forms.ValidationError("Message cannot be empty.")
        return message
