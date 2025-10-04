from django import forms
from .models import Report, Communication
from djmoney.forms.fields import MoneyField


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['title','tip_type','organisation_type','misconduct_ongoing_status','organisation_name','incident_date',
                'persons_involved','amount_involved','branch_address_of_organisation','description_of_tip','other_agency_name',
                'other_agency_submitted_date','whistleblower_surname','whistleblower_firstname','whistleblower_mobile_number','whistleblower_email','whistleblower_address',
                'evidence_file',]
        
 #   '''def __init__(self, *args, **kwargs):
#        super().__init__(*args, **kwargs)
#        self.fields['amount_involved'].widget.attrs.update({
#            'class': 'w-third px-4 py-2 border border-gray-300 rounded-lg focus:border-transparent rounded-md shadow-sm focus:outline-none focus:ring-blue-500',
 #           'placeholder': 'Enter amount (e.g. 100.00)',
#        })

        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Brief title of the incident'
            }),
            'tip_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            }),
            # 'category': forms.Select(attrs={
            #     'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            # }),
            'organisation_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            }),
            'misconduct_ongoing_status': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            }),
            'organisation_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Name of Government Organisation'
            }),
            ##'transaction_date': forms.DateInput(attrs={
           ##     'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            ##    'type': 'date'
           ## }),
            'incident_date': forms.DateInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'type': 'date'
            }),
            'persons_involved': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'rows': 2,
                'placeholder': 'Names or descriptions of persons involved (optional)'
            }),
                 
            # 'amount_involved': forms.NumberInput(attrs={
            #    'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            #     'rows': 1,
            #     'placeholder': 'Amount of Money Involved'
            # }),
            
            'branch_address_of_organisation': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'rows': 3,
                'placeholder': 'Location or Address of Branch where the Misconduct Occured. '
            }),
            'description_of_tip': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'rows': 6,
                'placeholder': 'Please provide detailed description of the Tip...'
            }),
            #'description': forms.Textarea(attrs={
            #    'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            #    'rows': 6,
            #    'placeholder': 'Please provide detailed description of the incident...'
           # }),
            'other_agency_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Name of other Government Organisation tip was Submitted to e.g ICPC, EFCC etc'
            }),
            'other_agency_submitted_date': forms.DateInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'type': 'date'
            }),
            'whistleblower_surname': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Your Surname'
            }),
            'whistleblower_firstname': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Your First name'
            }),
            'whistleblower_mobile_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Input Your contact phone number'
            }),
            'whistleblower_email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Input your Email address'
            }),
            'whistleblower_address': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Input your Contact address'
            }),
            'evidence_file': forms.FileInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            }),
        }


class CaseTrackingForm(forms.Form):
    case_id = forms.CharField(
        max_length=12,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Enter your Case ID (e.g., WB2024123456)'
        })
    )
    access_code = forms.CharField(
        max_length=8,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Enter your Access Code'
        })
    )


class CommunicationForm(forms.ModelForm):
    class Meta:
        model = Communication
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'rows': 4,
                'placeholder': 'Type your message here...'
            }),
        }
