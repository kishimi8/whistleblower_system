from django.core.management.base import BaseCommand
from reports.models import Report
from django.utils import timezone
from datetime import timedelta
import random

class Command(BaseCommand):
    help = 'Seeds database with dummy reports for dashboard testing'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding data...')
        
        # diverse statuses and dates
        statuses = ['new', 'under_review', 'investigating', 'closed']
        types = ['corruption', 'fraud', 'harassment']
        
        for i in range(20):
            # Random date within last 30 days
            days_ago = random.randint(0, 30)
            date = timezone.now() - timedelta(days=days_ago)
            
            Report.objects.create(
                title=f"Test Report {i}",
                tip_type=random.choice(types),
                organisation_type="ministry",
                organisation_name="Test Org",
                incident_date="2024-01-01",
                other_agency_submitted_date="2024-01-01",
                other_agency_name="None",
                description_of_tip="Auto-generated for testing",
                status=random.choice(statuses),
                created_at=date # Note: manually setting created_at usually requires auto_now_add=False or custom save override, but for basic testing models.create handles it if override allows. Wait, auto_now_add makes it read-only on save.
            )
            # Fix created_at after creation since auto_now_add overrides init
            r = Report.objects.last()
            r.created_at = date
            r.save()
            
        self.stdout.write(self.style.SUCCESS(f'Successfully created 20 reports'))
