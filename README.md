# Conversational AI Builder

A simple, white-labeled Conversational AI Builder that allows users to create conversational AI bots with both text and voice responses. Built with Django, powered by GitHub Models GPT-4 and Google Cloud Text-to-Speech.

## 🔹 Task Implementation 🔹

This application fulfills the following requirements:

✅ **Enter a text prompt**: Users can create AI bots by entering system prompts that define bot behavior <br>
✅ **Generate conversational AI bot**: Powered by GitHub Models GPT-4 API for intelligent responses <br>
✅ **Voice input capability**: Speech-to-text using Web Speech API (free, no API keys required) <br>
✅ **Provide both text and voice responses**: Text responses with optional voice synthesis using Google Cloud Text-to-Speech <br>
✅ **Voice response playback**: In-browser audio player with replay functionality <br>
✅ **Hardcoded credentials**: API keys are configured in environment variables for easy setup <br>

## Features

- **Simple Bot Creation**: Enter a text prompt to define your AI bot's personality
- **Real-time Chat**: Interactive messaging with AI-powered responses
- **Voice Input**: Speech-to-text using browser's native Web Speech API
- **Voice Synthesis**: Automatic text-to-speech conversion for all AI responses
- **Audio Playback**: Click-to-play voice responses with replay controls
- **Clean UI**: Responsive, white-labeled interface built with Bootstrap


## Technology Stack

- **Backend**: Django 5.2.1 (Python)
- **Database**: SQLite (development), PostgreSQL/Supabase (production)
- **AI API**: GitHub Models GPT-4
- **Voice API**: Google Cloud Text-to-Speech
- **Frontend**: Bootstrap 5, jQuery, HTML5 Audio
- **Deployment**: Render
  
## Configuration

API keys are configured in environment variables for easy setup:

- **GitHub Models API**: Used for GPT-4 conversational AI responses
- **Google Cloud Text-to-Speech API**: Used for text-to-speech voice synthesis
- **Database**: PostgreSQL (Supabase) for production, SQLite for development

## Usage

### Creating Your First Bot

1. Click "Create New Bot" on the homepage
2. Enter a descriptive name for your bot
3. Write a system prompt that defines the bot's personality and behavior
4. Adjust creativity level (temperature) 
5. Click "Create Bot"

### Chatting with Bots

1. Click "Chat" on any bot card
2. Type or Speak your message and press Enter or click Send
3. The AI will respond with text and voice audio
4. Click the play button to hear/replay voice responses

### Managing Bots

- **Edit**: Modify bot settings and prompts
- **Delete**: Remove bots 
- **Clear Chat**: Start a new conversation session

## Project Structure

```
conversational_ai_builder/
├── manage.py
├── requirements.txt
├── README.md
├── .env
├── conversational_ai_builder/
│   ├── settings.py          # Django configuration
│   ├── urls.py              # Main URL routing
│   └── ...
├── bots/                    # Main application
│   ├── models.py            # Database models
│   ├── views.py             # View controllers
│   ├── forms.py             # Django forms
│   ├── services.py          # API integrations
│   ├── utils.py             # Helper functions
│   └── ...
├── templates/               # HTML templates
│   ├── base.html
│   └── bots/
├── static/                  # CSS, JS, images
│   ├── css/
│   ├── js/
│   └── images/
└── media/                   # Generated audio files
    └── audio/
```




## Acknowledgments

- GitHub Models for GPT-4 API access
- Google Cloud for text-to-speech API
- Django framework for Development
- Bootstrap for responsive design
- Render for hosting platform
