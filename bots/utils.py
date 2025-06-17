import uuid
import os
from django.core.files.storage import default_storage
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def generate_session_id():
    """Generate a unique session ID for conversations"""
    return str(uuid.uuid4())



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



