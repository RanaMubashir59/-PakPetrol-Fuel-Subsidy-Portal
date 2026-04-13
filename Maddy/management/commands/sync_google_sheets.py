"""
Django management command to sync Google Sheets data to local CSV.
Usage: python manage.py sync_google_sheets
"""
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from pathlib import Path
from Maddy.google_sheets_helper import sync_sheets_to_csv, is_credentials_available


class Command(BaseCommand):
    help = 'Sync Google Sheets form responses to local CSV cache'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sheet-name',
            type=str,
            default='Form Responses 1',
            help='Name of the Google Sheet to sync (default: Form Responses 1)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sync even if credentials not available (uses cache)'
        )

    def handle(self, *args, **options):
        sheet_name = options['sheet_name']
        
        # Check credentials
        if not is_credentials_available() and not options['force']:
            self.stdout.write(
                self.style.ERROR(
                    '❌ credentials.json not found.\n'
                    'Set up Google Sheets API:\n'
                    '  1. Create a project at https://console.cloud.google.com\n'
                    '  2. Enable Google Sheets & Drive APIs\n'
                    '  3. Create a Service Account and download credentials.json\n'
                    '  4. Place credentials.json in project root\n'
                    '  5. Share your Google Sheet with the service account email'
                )
            )
            return
        
        # Sync data
        self.stdout.write(self.style.SUCCESS(f'🔄 Syncing data from "{sheet_name}"...'))
        
        csv_path = Path(settings.BASE_DIR) / "analysis" / "google_form_responses.csv"
        
        success = sync_sheets_to_csv(
            csv_path=csv_path,
            sheet_name=sheet_name
        )
        
        if success:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Successfully synced data to {csv_path}')
            )
        else:
            raise CommandError(f'❌ Failed to sync data from "{sheet_name}"')
