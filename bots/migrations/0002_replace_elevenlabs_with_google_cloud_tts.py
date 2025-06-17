# Generated migration for replacing ElevenLabs with Google Cloud TTS

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('bots', '0001_initial'),
    ]

    operations = [
        # Rename voice_id to voice_name in ConversationalBot
        migrations.RenameField(
            model_name='conversationalbot',
            old_name='voice_id',
            new_name='voice_name',
        ),
        
        # Update the help text for voice_name
        migrations.AlterField(
            model_name='conversationalbot',
            name='voice_name',
            field=models.CharField(
                default='en-US-Chirp3-HD-Achernar',
                help_text='Google Cloud Text-to-Speech voice name',
                max_length=100
            ),
        ),
        
        # Rename ElevenLabsUsage to GoogleCloudTTSUsage
        migrations.RenameModel(
            old_name='ElevenLabsUsage',
            new_name='GoogleCloudTTSUsage',
        ),
        
        # Update the help text for characters_limit
        migrations.AlterField(
            model_name='googlecloudttsusage',
            name='characters_limit',
            field=models.IntegerField(default=10000, help_text='Warning limit for usage tracking'),
        ),
    ]
