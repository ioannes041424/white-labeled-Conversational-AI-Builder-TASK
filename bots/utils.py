import uuid
import os
from datetime import date
from django.core.files.storage import default_storage
from django.conf import settings
from .models import ElevenLabsUsage
import logging

logger = logging.getLogger(__name__)


def generate_session_id():
    """Generate a unique session ID for conversations"""
    return str(uuid.uuid4())


def check_elevenlabs_credits(character_count=0):
    """
    Check if ElevenLabs credits are available for the current month
    
    Args:
        character_count (int): Number of characters to check against limit
        
    Returns:
        dict: Contains 'available', 'usage', 'limit', 'percentage' information
    """
    current_month = date.today().replace(day=1)
    
    try:
        usage, created = ElevenLabsUsage.objects.get_or_create(
            month=current_month,
            defaults={
                'characters_used': 0,
                'characters_limit': 10000  # Free tier limit
            }
        )
        
        available_credits = usage.characters_limit - usage.characters_used
        can_use = available_credits >= character_count
        usage_percentage = (usage.characters_used / usage.characters_limit) * 100
        
        return {
            'available': can_use,
            'usage': usage.characters_used,
            'limit': usage.characters_limit,
            'percentage': round(usage_percentage, 1),
            'remaining': available_credits,
            'is_near_limit': usage_percentage >= 80,
            'is_over_limit': usage.characters_used >= usage.characters_limit
        }
        
    except Exception as e:
        logger.error(f"Error checking ElevenLabs credits: {str(e)}")
        return {
            'available': False,
            'usage': 0,
            'limit': 10000,
            'percentage': 0,
            'remaining': 0,
            'is_near_limit': False,
            'is_over_limit': True,
            'error': str(e)
        }


def save_audio_file(audio_data, filename):
    """
    Save audio data to media storage
    
    Args:
        audio_data (bytes): Audio file data
        filename (str): Desired filename
        
    Returns:
        str: Path to saved file or None if failed
    """
    try:
        # Ensure audio directory exists
        audio_dir = os.path.join(settings.MEDIA_ROOT, 'audio')
        os.makedirs(audio_dir, exist_ok=True)
        
        # Generate unique filename if needed
        if not filename.endswith('.mp3'):
            filename += '.mp3'
        
        file_path = os.path.join('audio', filename)
        
        # Save file
        saved_path = default_storage.save(file_path, audio_data)
        return saved_path
        
    except Exception as e:
        logger.error(f"Error saving audio file: {str(e)}")
        return None


def cleanup_old_audio_files(days_old=7):
    """
    Clean up audio files older than specified days
    
    Args:
        days_old (int): Number of days after which to delete files
    """
    try:
        from datetime import datetime, timedelta
        from django.core.files.storage import default_storage
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        audio_dir = os.path.join(settings.MEDIA_ROOT, 'audio')
        
        if os.path.exists(audio_dir):
            for filename in os.listdir(audio_dir):
                file_path = os.path.join(audio_dir, filename)
                if os.path.isfile(file_path):
                    file_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_modified < cutoff_date:
                        try:
                            os.remove(file_path)
                            logger.info(f"Deleted old audio file: {filename}")
                        except Exception as e:
                            logger.error(f"Error deleting file {filename}: {str(e)}")
                            
    except Exception as e:
        logger.error(f"Error during audio cleanup: {str(e)}")


def format_usage_display(usage_info):
    """
    Format usage information for display in templates
    
    Args:
        usage_info (dict): Usage information from check_elevenlabs_credits
        
    Returns:
        dict: Formatted display information
    """
    if not usage_info:
        return {
            'display_text': 'Usage information unavailable',
            'css_class': 'text-warning',
            'show_warning': True
        }
    
    percentage = usage_info.get('percentage', 0)
    usage = usage_info.get('usage', 0)
    limit = usage_info.get('limit', 10000)
    remaining = usage_info.get('remaining', 0)
    
    # Determine CSS class based on usage
    if percentage >= 90:
        css_class = 'text-danger'
    elif percentage >= 80:
        css_class = 'text-warning'
    else:
        css_class = 'text-success'
    
    # Format display text
    display_text = f"{usage:,} / {limit:,} characters used ({percentage}%)"
    
    return {
        'display_text': display_text,
        'css_class': css_class,
        'percentage': percentage,
        'remaining': remaining,
        'characters_used': usage,  # Add this for template access
        'show_warning': percentage >= 80,
        'warning_message': f"Warning: Only {remaining:,} characters remaining this month!" if percentage >= 80 else None
    }


def validate_voice_id(voice_id):
    """
    Validate ElevenLabs voice ID
    
    Args:
        voice_id (str): Voice ID to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    # List of known ElevenLabs voice IDs
    valid_voices = [
        "21m00Tcm4TlvDq8ikWAM",  # Rachel
        "AZnzlk1XvdvUeBnXmlld",  # Domi
        "EXAVITQu4vr4xnSDxMaL",  # Bella
        "ErXwobaYiN019PkySvjV",  # Antoni
        "MF3mGyEYCl7XYWbV9V6O",  # Elli
        "TxGEqnHWrfWFTfGW9XjX",  # Josh
        "VR6AewLTigWG4xSOukaG",  # Arnold
        "pNInz6obpgDQGcFmaJgB",  # Adam
        "yoZ06aMxZJJ28mfd3POQ",  # Sam
    ]
    
    return voice_id in valid_voices


def truncate_text(text, max_length=100):
    """
    Truncate text to specified length with ellipsis

    Args:
        text (str): Text to truncate
        max_length (int): Maximum length

    Returns:
        str: Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."



