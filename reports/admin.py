from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Report, Communication, AuditLog
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .resources import Reportresource

@admin.register(Report)
class ReportImportExport(ImportExportModelAdmin):
    resource_classes = [Reportresource]

class ReportAdmin(admin.ModelAdmin):
    list_display = ['case_id', 'title','tip_type','misconduct_ongoing_status', 'status', 'assigned_investigator', 'created_at']
    list_filter = ['status',  'tip_type','organisation_type', 'created_at', 'assigned_investigator']
    search_fields = ['case_id', 'title']
    readonly_fields = ['case_id', 'access_code', 'created_at', 'updated_at']
    fieldsets = (
        ('Case Information', {
            'fields': ('case_id', 'access_code', 'status', 'assigned_investigator')
        }),
        #('Report Details', {
            #'fields': ('title', 'tip_type', 'category','organisation_type','misconduct_status','organisation_name','transaction_date', 'incident_date', 'persons_involved',
            #      'amount_involved','branch_address_of_organisation', 'description_of_tip','description','other_agency_name','other_agency_submitted_date','whistleblower_surname','whistleblower_firstname','whistleblower_mobile_number',
            #      'whistleblower_email','whistleblower_address','evidence_file')
        #}),
        ('Report Details', {
            'fields': ('title','tip_type','organisation_type','misconduct_ongoing_status','organisation_name','incident_date',
                'persons_involved','amount_involved','branch_address_of_organisation','description_of_tip','other_agency_name',
                'other_agency_submitted_date','whistleblower_surname','whistleblower_firstname','whistleblower_mobile_number','whistleblower_email','whistleblower_address',
                'evidence_file',)
        }),
        ('Investigation', {
            'fields': ('investigation_notes', 'resolution_summary', 'closed_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('assigned_investigator')

    def save_model(self, request, obj, form, change):
        if change:  # Only for updates
            # Create audit log for status changes
            if 'status' in form.changed_data:
                AuditLog.objects.create(
                    report=obj,
                    user=request.user,
                    action=f"Status Changed to {obj.get_status_display()}",
                    details=f"Status updated by {request.user.username}"
                )
        super().save_model(request, obj, form, change)


@admin.register(Communication)
class CommunicationAdmin(admin.ModelAdmin):
    list_display = ['report', 'sender_type', 'created_at', 'message_preview']
    list_filter = ['is_from_investigator', 'created_at']
    search_fields = ['report__case_id', 'message']
    readonly_fields = ['created_at']

    def sender_type(self, obj):
        return "Investigator" if obj.is_from_investigator else "Whistleblower"

    sender_type.short_description = 'Sender'

    def message_preview(self, obj):
        return obj.message[:100] + "..." if len(obj.message) > 100 else obj.message

    message_preview.short_description = 'Message Preview'
    
    # fieldsets = (
    #     ('Communication Messages', {
    #         'fields': ('new_evidence_file',)
    #     }),
    # )

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['report', 'action', 'user', 'timestamp']
    list_filter = ['action', 'timestamp', 'user']
    search_fields = ['report__case_id', 'action', 'details']
    readonly_fields = ['timestamp']

    def has_add_permission(self, request):
        return False  # Prevent manual addition of audit logs

    def has_change_permission(self, request, obj=None):
        return False  # Make audit logs read-only

