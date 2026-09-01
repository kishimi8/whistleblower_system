from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Report, Communication

class ChatFeatureTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.report = Report.objects.create(
            title="Test Corruption",
            tip_type="corruption",
            organisation_type="ministry",
            organisation_name="Test Ministry",
            incident_date="2024-01-01",
            other_agency_submitted_date="2024-01-01",
            other_agency_name="None",
            description_of_tip="Detailed description"
        )
        self.user = User.objects.create_superuser(username='admin', password='password123', email='admin@test.com')

    def test_whistleblower_can_send_message(self):
        url = reverse('track_case')
        data = {
            'case_id': self.report.case_id,
            'access_code': self.report.access_code,
            'message': 'Hello investigator'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302) # Redirect after success
        
        # Verify message created
        comm = Communication.objects.filter(report=self.report).last()
        self.assertEqual(comm.message, 'Hello investigator')
        self.assertFalse(comm.is_from_investigator)

    def test_investigator_message_visible(self):
        # Create investigator message
        Communication.objects.create(
            report=self.report,
            message="We are looking into it",
            is_from_investigator=True
        )
        
        # Access track case
        url = reverse('track_case')
        data = {
            'case_id': self.report.case_id,
            'access_code': self.report.access_code
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "We are looking into it")
        self.assertContains(response, "Official Investigator")

    def test_auto_close_message(self):
        # Close the report
        self.report.closed_at = timezone.now()
        self.report.resolution_summary = "Resolved successfully"
        self.report.save()

        # Check for auto-message
        comm = Communication.objects.filter(report=self.report).last()
        self.assertIn("officially closed", comm.message)
        self.assertIn("Resolved successfully", comm.message)
        self.assertTrue(comm.is_from_investigator)
