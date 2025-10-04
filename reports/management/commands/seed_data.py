from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from reports.models import Report, Communication
from datetime import datetime, timedelta
import random
from faker import Faker


class Command(BaseCommand):
    help = 'Seed the database with dummy whistleblowing data'

    def __init__(self):
        super().__init__()
        self.fake = Faker()

    def add_arguments(self, parser):
        parser.add_argument(
            '--reports',
            type=int,
            help='Number of reports to create',
            default=20
        )
        parser.add_argument(
            '--users',
            type=int,
            help='Number of investigator users to create',
            default=3
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            Report.objects.all().delete()
            Communication.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()

        # Create investigator users
        self.create_investigators(options['users'])

        # Create reports
        self.create_reports(options['reports'])

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully seeded {options["reports"]} reports and {options["users"]} investigators'
            )
        )

    def create_investigators(self, count):
        """Create investigator users"""
        investigators = []
        for i in range(count):
            username = f"investigator_{i + 1}"
            email = f"investigator{i + 1}@bank.com"

            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': self.fake.first_name(),
                    'last_name': self.fake.last_name(),
                    'is_staff': True,
                    'is_active': True,
                }
            )

            if created:
                user.set_password('password123')
                user.save()
                investigators.append(user)
                self.stdout.write(f'Created investigator: {username}')

        return investigators

    def create_reports(self, count):
        """Create dummy reports with various statuses"""
        investigators = list(User.objects.filter(is_staff=True))

        # Sample report data
        fraud_scenarios = [
            {
                'title': 'Unauthorized access to customer accounts',
                'description': 'A colleague has been accessing customer accounts without authorization and sharing confidential information with external parties.',
                'persons_involved': 'Customer Service Representative Mike Wilson'
            },
            {
                'title': 'Falsification of transaction records',
                'description': 'I discovered that someone has been altering transaction records to hide suspicious money transfers. This appears to be systematic and ongoing.',
                'persons_involved': 'Operations Manager Lisa Brown, Teller David Chen'
            },
            {
                'title': 'Insider trading activities',
                'description': 'Senior staff members are allegedly using confidential client information to make personal investment decisions before public announcements.',
                'persons_involved': 'Investment Advisor Robert Taylor, Portfolio Manager Jennifer Davis'
            },
            {
                'title': 'Money laundering scheme',
                'description': 'Large cash deposits are being processed without proper KYC verification. The amounts and frequency suggest potential money laundering activities.',
                'persons_involved': 'Branch Manager Tom Anderson, Compliance Officer Maria Garcia'
            }
        ]

        harassment_scenarios = [
            {
                'title': 'Workplace harassment by supervisor',
                'description': 'My supervisor has been making inappropriate comments and creating a hostile work environment. Several colleagues have witnessed this behavior.',
                'persons_involved': 'Department Head James Wilson'
            },
            {
                'title': 'Discrimination in promotion decisions',
                'description': 'Qualified minority employees are consistently passed over for promotions in favor of less qualified candidates.',
                'persons_involved': 'HR Manager Patricia Lee, Regional Director Mark Johnson'
            },
            {
                'title': 'Bullying and intimidation',
                'description': 'A senior employee has been bullying junior staff, using threats and intimidation to prevent them from reporting issues.',
                'persons_involved': 'Senior Analyst Kevin Brown'
            }
        ]

        regulatory_scenarios = [
            {
                'title': 'Non-compliance with reporting requirements',
                'description': 'The bank is failing to submit required regulatory reports on time and some reports contain inaccurate information.',
                'persons_involved': 'Compliance Department Head Susan Davis'
            },
            {
                'title': 'Inadequate risk management practices',
                'description': 'Risk assessment procedures are not being followed properly, potentially exposing the bank to significant financial risks.',
                'persons_involved': 'Risk Manager Paul Martinez, Chief Risk Officer Linda Thompson'
            }
        ]

        all_scenarios = (
                [(scenario, 'fraud') for scenario in fraud_scenarios] +
                [(scenario, 'harassment') for scenario in harassment_scenarios] +
                [(scenario, 'regulatory') for scenario in regulatory_scenarios]
        )

        for i in range(count):
            # Random scenario selection
            if i < len(all_scenarios):
                scenario, category = all_scenarios[i]
            else:
                scenario, category = random.choice(all_scenarios)

            # Random dates within the last 6 months
            created_date = self.fake.date_time_between(
                start_date='-6M',
                end_date='now',
                tzinfo=timezone.get_current_timezone()
            )

            # Random incident date within 30 days before creation
            incident_date = self.fake.date_between(
                start_date=created_date.date() - timedelta(days=30),
                end_date=created_date.date()
            )

            # Determine status based on age of report
            days_since_creation = (timezone.now() - created_date).days
            if days_since_creation < 2:
                status = 'new'
                assigned_investigator = None
            elif days_since_creation < 7:
                status = random.choice(['new', 'under_review'])
                assigned_investigator = random.choice(
                    investigators) if status == 'under_review' and investigators else None
            elif days_since_creation < 30:
                status = random.choice(['under_review', 'investigating'])
                assigned_investigator = random.choice(investigators) if investigators else None
            else:
                status = random.choice(['investigating', 'closed'])
                assigned_investigator = random.choice(investigators) if investigators else None

            # Create the report
            report = Report.objects.create(
                title=scenario['title'],
                description=scenario['description'],
                category=category,
                incident_date=incident_date,
                persons_involved=scenario['persons_involved'],
                status=status,
                assigned_investigator=assigned_investigator,
                created_at=created_date,
                updated_at=created_date + timedelta(days=random.randint(0, days_since_creation))
            )

            # Add resolution summary for closed cases
            if status == 'closed':
                resolutions = [
                    "Investigation completed. Appropriate disciplinary action has been taken. Policies have been updated to prevent similar incidents.",
                    "Matter resolved through internal procedures. Staff training has been enhanced and additional controls implemented.",
                    "Investigation concluded. The reported issues have been addressed and corrective measures are in place.",
                    "Case closed after thorough investigation. Necessary actions taken to ensure compliance and prevent recurrence."
                ]
                report.resolution_summary = random.choice(resolutions)
                report.save()

            # Create some communications for reports that have investigators
            if assigned_investigator and status in ['under_review', 'investigating', 'closed']:
                self.create_communications_for_report(report, assigned_investigator)

            self.stdout.write(f'Created report: {report.case_id} - {report.title[:50]}...')

    def create_communications_for_report(self, report, investigator):
        """Create sample communications between investigator and whistleblower"""

        # Initial investigator message
        initial_messages = [
            "Thank you for your report. We have begun our investigation and may need additional information from you. Please check back regularly for updates.",
            "We have received your report and assigned it for investigation. We appreciate your courage in bringing this matter to our attention.",
            "Your report is now under review. We take all reports seriously and will investigate this matter thoroughly."
        ]

        Communication.objects.create(
            report=report,
            is_from_investigator=True,
            message=random.choice(initial_messages),
            created_at=report.created_at + timedelta(days=random.randint(1, 3))
        )

        # Maybe add a follow-up question
        if random.choice([True, False]):
            followup_messages = [
                "Could you provide more specific dates when you observed these incidents?",
                "Do you have any documentation or evidence that could support this investigation?",
                "Are there any witnesses who might be willing to provide additional information?",
                "Can you provide more details about the specific procedures that were not followed?"
            ]

            Communication.objects.create(
                report=report,
                is_from_investigator=True,
                message=random.choice(followup_messages),
                created_at=report.created_at + timedelta(days=random.randint(5, 10))
            )

            # Maybe add a whistleblower response
            if random.choice([True, False]):
                responses = [
                    "I have gathered some additional documentation that might be helpful. The incidents occurred primarily during the last week of each month.",
                    "Yes, there are at least two other employees who witnessed similar behavior. I can provide more details if needed.",
                    "I observed these activities during my regular audit checks. I have screenshots of the suspicious transactions.",
                    "I can provide specific dates and times. This has been going on for several months now."
                ]

                Communication.objects.create(
                    report=report,
                    is_from_investigator=False,
                    message=random.choice(responses),
                    created_at=report.created_at + timedelta(days=random.randint(12, 15))
                )

        # Final update for closed cases
        if report.status == 'closed':
            final_messages = [
                "Our investigation has been completed. Thank you for bringing this matter to our attention. Appropriate action has been taken.",
                "The investigation is now closed. We have implemented additional controls to address the issues you reported.",
                "Thank you for your report. The matter has been resolved and we have taken steps to prevent similar incidents in the future."
            ]

            Communication.objects.create(
                report=report,
                is_from_investigator=True,
                message=random.choice(final_messages),
                created_at=report.updated_at
            )