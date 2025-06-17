from django.core.management.base import BaseCommand
from bots.models import ConversationalBot
from bots.services import VoiceSelectionService


class Command(BaseCommand):
    help = 'Update existing bots with AI-selected voices'

    def handle(self, *args, **options):
        bots = ConversationalBot.objects.filter(is_active=True)
        updated_count = 0
        
        for bot in bots:
            old_voice = bot.voice_name
            new_voice = VoiceSelectionService.select_voice_for_bot(
                bot.name,
                bot.system_prompt
            )

            if old_voice != new_voice:
                bot.voice_name = new_voice
                bot.save()
                
                old_name = VoiceSelectionService.get_voice_name(old_voice) if old_voice else 'None'
                new_name = VoiceSelectionService.get_voice_name(new_voice)
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Updated "{bot.name}": {old_name} → {new_name}'
                    )
                )
                updated_count += 1
            else:
                voice_name = VoiceSelectionService.get_voice_name(new_voice)
                self.stdout.write(
                    f'"{bot.name}": Already using optimal voice ({voice_name})'
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nCompleted! Updated {updated_count} bot(s) with AI-selected voices.'
            )
        )
