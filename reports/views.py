from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from .models import Report, Communication, AuditLog
from .forms import ReportForm, CaseTrackingForm, CommunicationForm
from tablib import Dataset
from .resources import Reportresource


def home(request):
    """Landing page with report submission form"""
    if request.method == 'POST':
        form = ReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save()

            # Create audit log
            AuditLog.objects.create(
                report=report,
                action="Report Submitted",
                details=f"New report submitted: {report.title}"
            )

            return render(request, 'reports/submission_success.html', {
                'case_id': report.case_id,
                'access_code': report.access_code
            })
    else:
        form = ReportForm()

    return render(request, 'reports/home.html', {'form': form})


def track_case(request):
    """Case tracking page"""
    report = None
    communications = []

    if request.method == 'POST':
        tracking_form = CaseTrackingForm(request.POST)
        if tracking_form.is_valid():
            case_id = tracking_form.cleaned_data['case_id']
            access_code = tracking_form.cleaned_data['access_code']

            try:
                report = Report.objects.get(case_id=case_id, access_code=access_code)
                communications = report.communications.all()

                # Handle new message submission if message field is present
                if request.POST.get('message'):
                    comm_form = CommunicationForm(request.POST)
                    if comm_form.is_valid():
                        communication = comm_form.save(commit=False)
                        communication.report = report
                        communication.is_from_investigator = False
                        communication.save()

                        # Create audit log
                        AuditLog.objects.create(
                            report=report,
                            action="Message from Whistleblower",
                            details="New message received from whistleblower"
                        )

                        messages.success(request, 'Your message has been sent.')
                        return redirect('track_case')
                    else:
                        # If form is invalid, keep the form with errors
                        pass
                else:
                    comm_form = CommunicationForm()

            except Report.DoesNotExist:
                messages.error(request, 'Invalid Case ID or Access Code.')
                tracking_form = CaseTrackingForm()
                comm_form = None
        else:
            comm_form = None
    else:
        tracking_form = CaseTrackingForm()
        comm_form = None

    return render(request, 'reports/track_case.html', {
        'tracking_form': tracking_form,
        'comm_form': comm_form,
        'report': report,
        'communications': communications
    })


def about(request):
    """About page explaining the whistleblowing process"""
    return render(request, 'reports/about.html')


## export files

def export_data(request):
    if request.method == 'POST':
        # Get selected option from form
        file_format = request.POST['file-format']
        report_resource = Reportresource()
        dataset = report_resource.export()
        if file_format == 'CSV':
            response = HttpResponse(dataset.csv, content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="exported_data.csv"'
            return response        
        elif file_format == 'JSON':
            response = HttpResponse(dataset.json, content_type='application/json')
            response['Content-Disposition'] = 'attachment; filename="exported_data.json"'
            return response
        elif file_format == 'XLS (Excel)':
            response = HttpResponse(dataset.xls, content_type='application/vnd.ms-excel')
            response['Content-Disposition'] = 'attachment; filename="exported_data.xls"'
            return response   

    return render(request, 'export.html')


## import 

def import_data(request):
    if request.method == 'POST':
        file_format = request.POST['file-format']
        report_resource = Reportresource
        dataset = Dataset()
        new_report = request.FILES['importData']

        if file_format == 'CSV':
            imported_data = dataset.load(new_report.read().decode('utf-8'),format='csv')
            result = report_resource.import_data(dataset, dry_run=True)                                                                 
        elif file_format == 'JSON':
            imported_data = dataset.load(new_report.read().decode('utf-8'),format='json')
            # Testing data import
            result = report_resource.import_data(dataset, dry_run=True) 

        if not result.has_errors():
            # Import now
            report_resource.import_data(dataset, dry_run=False)

    return render(request, 'import.html')    