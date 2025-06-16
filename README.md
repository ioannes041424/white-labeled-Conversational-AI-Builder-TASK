# Conversational AI Builder

A white-labeled Django web application for creating AI chatbots with both text and voice responses, powered by GitHub Models GPT-4 and ElevenLabs text-to-speech.

## Features

- **Create AI Bots**: Configure custom AI personalities with system prompts
- **Interactive Chat**: Real-time messaging with AI bots
- **Voice Responses**: Text-to-speech conversion using ElevenLabs API
- **Audio Playback**: In-browser audio player for voice responses
- **Bot Management**: Create, edit, delete, and organize your bots
- **Usage Tracking**: Monitor ElevenLabs API usage and credits
- **Responsive Design**: Works on desktop and mobile devices

## Technology Stack

- **Backend**: Django 5.2.1 (Python)
- **Database**: SQLite (development), PostgreSQL/Supabase (production)
- **AI API**: GitHub Models GPT-4
- **Voice API**: ElevenLabs
- **Frontend**: Bootstrap 5, jQuery, HTML5 Audio
- **Styling**: Custom CSS with responsive design
- **Deployment**: Render (production), Gunicorn, WhiteNoise

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- GitHub account with access to GitHub Models
- ElevenLabs API account (free tier available)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd conversational_ai_builder
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

**For most systems (Linux, macOS, and production):**
```bash
pip install -r requirements.txt
```

**For Windows (if psycopg2-binary installation fails):**
```bash
# Option 1: Use requirements without PostgreSQL for local development
pip install -r requirements-windows.txt

# Option 2: Install dependencies individually
pip install Django==5.2.1 python-dotenv==1.0.0 azure-ai-inference==1.0.0b4 elevenlabs==0.2.26 requests==2.31.0 Pillow==10.4.0

# Option 3: Skip PostgreSQL for local development (use SQLite)
# Just comment out the DATABASE_URL in your .env file
```

**Note**: If you encounter PostgreSQL installation issues on Windows, you can develop locally with SQLite and use PostgreSQL only in production.

### 4. Configure Environment Variables

Create a `.env` file in the project root and add your API credentials:

```env
# API Configuration
GITHUB_TOKEN=your-github-token-here
ELEVENLABS_API_KEY=your-elevenlabs-api-key-here

# Django Configuration
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Configuration (choose one method)
# Method 1: Full connection string (recommended)
DATABASE_URL=postgresql://user:password@host:port/database

# Method 2: Individual settings (alternative)
# DB_NAME=postgres
# DB_USER=your-db-user
# DB_PASSWORD=your-db-password
# DB_HOST=your-db-host
# DB_PORT=5432
```

### 5. Database Setup

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Create Superuser (Optional)

```bash
python manage.py createsuperuser
```

### 7. Run Development Server

```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000` to access the application.

## API Setup

### GitHub Models Setup

1. Sign up for GitHub and get access to GitHub Models
2. Generate a personal access token with appropriate permissions
3. Add the token to your `.env` file as `GITHUB_TOKEN`
4. The app uses the `openai/gpt-4.1` model via GitHub Models API

### ElevenLabs Setup

1. Sign up for a free ElevenLabs account at https://elevenlabs.io
2. Get your API key from the profile settings
3. Add it to your `.env` file as `ELEVENLABS_API_KEY`
4. Free tier includes 10,000 characters per month

### Supabase Database Setup

1. Create a free Supabase account at https://supabase.com
2. Create a new project
3. Go to Settings → Database
4. Copy the connection string or individual connection details
5. Add to your `.env` file using one of these methods:

**Method 1: Connection String (Recommended)**
```env
DATABASE_URL=postgresql://postgres.username:password@host:port/postgres
```

**Method 2: Individual Settings**
```env
DB_NAME=postgres
DB_USER=postgres.username
DB_PASSWORD=your-password
DB_HOST=your-host
DB_PORT=6543
```

**Note**: The application will automatically use PostgreSQL if `DATABASE_URL` or `DB_NAME` is provided, otherwise it defaults to SQLite for local development.

## Usage

### Creating Your First Bot

1. Click "Create New Bot" on the homepage
2. Enter a descriptive name for your bot
3. Write a system prompt that defines the bot's personality and behavior
4. Adjust creativity level (temperature) and select a voice
5. Click "Create Bot"

### Chatting with Bots

1. Click "Chat" on any bot card
2. Type your message and press Enter or click Send
3. The AI will respond with text and optional voice audio
4. Click the play button to hear voice responses

### Managing Bots

- **Edit**: Modify bot settings, prompts, and voice
- **Delete**: Remove bots (soft delete preserves data)
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

## Configuration

### Django Settings

Key settings in `conversational_ai_builder/settings.py`:

- `GITHUB_TOKEN`: Your GitHub personal access token
- `ELEVENLABS_API_KEY`: Your ElevenLabs API key
- `SECRET_KEY`: Django secret key for security
- `DEBUG`: Set to False in production
- `ALLOWED_HOSTS`: Allowed hostnames for the application
- `DATABASE_URL`: PostgreSQL connection string for production
- `MEDIA_ROOT`: Directory for audio file storage

### Voice Options

Available ElevenLabs voices:
- Rachel (Default)
- Domi
- Bella
- Antoni
- Elli
- Josh
- Arnold
- Adam
- Sam

## Troubleshooting

### Common Issues

1. **API Key Errors**
   - Verify your API keys are correct in the `.env` file
   - Check that your GitHub token has proper permissions
   - Ensure ElevenLabs account has available credits

2. **Audio Not Playing**
   - Check browser audio permissions
   - Verify ElevenLabs API is working
   - Check network connectivity

3. **Database Errors**
   - Run `python manage.py migrate` to apply migrations
   - Check database file permissions

4. **Windows PostgreSQL Installation Issues**
   - If `psycopg2-binary` fails to install, use SQLite for local development
   - Comment out `DATABASE_URL` in your `.env` file to use SQLite
   - PostgreSQL will still work in production (Render) deployment
   - Alternative: Install PostgreSQL locally and add it to your PATH

### Debug Mode

Set `DEBUG=True` in your `.env` file for detailed error messages during development.

## Production Deployment

### Render Deployment

This application is configured for easy deployment on Render.com:

#### Prerequisites
- GitHub account with your code repository
- Render account (free tier available)
- GitHub token for API access
- ElevenLabs API key

#### Deployment Steps

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Initial commit"
   git push origin main
   ```

2. **Create Render Web Service**
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Configure the service:

#### Render Configuration

**Build & Deploy Settings:**
- **Environment**: `Python 3`
- **Build Command**: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
- **Start Command**: `gunicorn conversational_ai_builder.wsgi:application`
- **Instance Type**: `Free` (or higher for production)

**Environment Variables:**
Add these in Render's Environment tab:
```
SECRET_KEY=your-production-secret-key-here
DEBUG=False
GITHUB_TOKEN=your-github-token-here
ELEVENLABS_API_KEY=your-elevenlabs-api-key-here
ALLOWED_HOSTS=your-app-name.onrender.com
DATABASE_URL=postgresql://postgres.xtiugsyxdqsemfvnistd:16ajnBDJqHXobsrM@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres
```

**Database Setup:**
- **Option 1**: Use Supabase (recommended) - Use the DATABASE_URL provided above
- **Option 2**: Add PostgreSQL database in Render - The `DATABASE_URL` will be automatically provided

#### Post-Deployment Commands

After successful deployment, run these commands in Render's Shell:

```bash
# Create superuser (optional)
python manage.py createsuperuser

# Check deployment
python manage.py check --deploy
```

### Manual Production Setup

For other hosting providers:

1. Set `DEBUG=False` in environment variables
2. Configure PostgreSQL database with `DATABASE_URL`
3. Set up static file serving with WhiteNoise (included)
4. Use environment variables for all sensitive settings
5. Enable HTTPS for secure API communication
6. Use Gunicorn as WSGI server

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Check the troubleshooting section above
- Review Django and API documentation
- Create an issue in the repository

## Deployment Commands for Render

Here are all the commands you'll need for Render deployment:

### Build Command:
```bash
pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
```

### Start Command:
```bash
gunicorn conversational_ai_builder.wsgi:application
```

### Environment Variables to Set in Render:
```
SECRET_KEY=your-production-secret-key-here
DEBUG=False
GITHUB_TOKEN=your-github-token-here
ELEVENLABS_API_KEY=your-elevenlabs-api-key-here
ALLOWED_HOSTS=your-app-name.onrender.com
DATABASE_URL=postgresql://postgres.xtiugsyxdqsemfvnistd:16ajnBDJqHXobsrM@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres
```

## Acknowledgments

- GitHub Models for GPT-4 API access
- ElevenLabs for text-to-speech API
- Django framework and community
- Bootstrap for responsive design
- Render for hosting platform
