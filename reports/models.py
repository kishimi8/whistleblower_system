from django.db import models
from django.contrib.auth.models import User
import secrets
import string
from django.utils import timezone
from djmoney.models.fields import MoneyField



class Report(models.Model):
    STATUS_CHOICES = [
        ('new', 'New'),
        ('under_review', 'Under Review'),
        ('investigating', 'Investigating'),
        ('closed', 'Closed'),
    ]

    CATEGORY_CHOICES = [
        ('fraud', 'Fraud'),
        ('corruption', 'Corruption'),
        ('harassment', 'Harassment'),
        ('discrimination', 'Discrimination'),
        ('safety', 'Safety Violation'),
        ('regulatory', 'Regulatory Violation'),
        ('other', 'Other'),
    ]

    ORGANISATION_TYPE= [
        ('ministry','Ministry'),
        ('department','Department'),
        ('agency','Agency'),
        ('other','Other'),
    ]

    MISCONDUCT_STATUS= [
        ('yes','Yes'),
        ('no','No'),
        ('unknown','Unknown'),
    ]

    TIP_TYPE_CHOICES = [
        ('diversion_of_revenues','Diversion of Revenues'),
        ('curruption','Curruption'),
        ('noncompliance_with_efficiency_guidelines', 'NonCompliance with Efficiency Unit Expenditure Guidelines/Circulars'),
        ('fraud','Fraud'),
        ('information_on_stolen_public_funds','Information on Stolen Public Funds'),
        ('manipulation_of_data_or_records','Manipulation of Data or Records'),
        ('conversion_of_funds_to_personal_use','Conversion of Funds to Personal Use'),
        ('violation_of_tsa_guidlines','Violation of TSA Guidlines'),
        ('misappropriation_of_public_funds','Misappropriation of Public Funds or Assets'),
        ('conflict_of_interest','Conflict of Interest'),
        ('collecting_soliciting_bribes','Collecting/Soliciting for Bribes'),
        ('fraudulent_payment','Fraudulent Payments'),
        ('undocumented_expenditures','Undocumented Expenditures'),
        ('splitting_contracts','Splitting of Contracts'),
        ('violation_Procurement_procedures', 'Violation of Procurement Procedures'),
        ('procurement_fraud', 'Procurement Fraud(Kickbacks, Over invoicing etc)'),
        ('nonremittance_lateremittance_revenue','NonRemittance/ Latre Remittance of Revenue'),
        ('concealed_funds_info','Information on Concealed Public Funds'),
        ('unapproved_expenditures', 'Unapproved Expenditures'),
    ]

    case_id = models.CharField(max_length=12, unique=True, editable=False)
    access_code = models.CharField(max_length=8, editable=False)

    # Report details
    title = models.CharField(max_length=200)
    tip_type = models.CharField(max_length=60, choices=TIP_TYPE_CHOICES)
    #category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    organisation_type = models.CharField(max_length=20, choices=ORGANISATION_TYPE)
    misconduct_ongoing_status = models.CharField(max_length=20, choices=MISCONDUCT_STATUS,default='yes')
    organisation_name = models.CharField(max_length=200)
    ## transaction_date = models.DateField()
    incident_date = models.DateField()
    persons_involved = models.TextField(blank=True, null=True)
    amount_involved= MoneyField(max_digits=19, decimal_places=4, null=True, default_currency='NGN', currency_choices=[("NGN", "NGN"), ("USD", "USD"),("GBP", "GBP"),("EUR", "EUR")])
    ##amount_involved = models.FloatField(blank=True, null=True)
    branch_address_of_organisation = models.TextField(blank=True, null=True)
    description_of_tip = models.TextField()
    ##description = models.TextField()

    #other agency submitted informtion
    other_agency_name = models.CharField(max_length=100)
    other_agency_submitted_date = models.DateField(blank=True)

    #Optional whistleblower details
    whistleblower_surname = models.CharField(max_length=100, blank=True, null=True)
    whistleblower_firstname = models.CharField(max_length=100, blank=True, null=True)
    whistleblower_mobile_number = models.IntegerField(blank=True, null=True)
    whistleblower_email = models.CharField(max_length=200, blank=True, null=True)
    whistleblower_address = models.TextField(max_length=500, blank=True, null=True)

    # File attachments
    evidence_file = models.FileField(upload_to='evidence/', blank=True, null=True)

    # System fields
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Investigation
    assigned_investigator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_reports'
    )
    investigation_notes = models.TextField(blank=True, null=True)
    resolution_summary = models.TextField(blank=True, null=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.case_id:
            self.case_id = self.generate_case_id()
        if not self.access_code:
            self.access_code = self.generate_access_code()
        super().save(*args, **kwargs)

    def generate_case_id(self):
        return f"WB{timezone.now().year}{secrets.randbelow(999999):06d}"

    def generate_access_code(self):
        return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))

    def close_case(self, resolution_summary):
        self.status = 'closed'
        self.closed_at = timezone.now()
        self.resolution_summary = resolution_summary
        self.save()

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Whistleblower Report'
        verbose_name_plural = 'Whistleblower Reports'

    def __str__(self):
        return f"{self.case_id} - {self.title}"


class Communication(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='communications')
    message = models.TextField()
    is_from_investigator = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    sender_name = models.CharField(max_length=100, default='Anonymous')
    new_evidence_file = models.FileField(upload_to='new_evidence/', blank=True, null=True)
    class Meta:
        ordering = ['created_at']

    def __str__(self):
        sender = "Investigator" if self.is_from_investigator else "Whistleblower"
        return f"{self.report.case_id} - {sender} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class AuditLog(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    details = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.report.case_id} - {self.action} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"