from django import forms
from .models import TimeEntry, Job, JobDetails, LaborCode, TimeEntryApproval
from datetime import datetime, timedelta

class JobDescriptionChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.job_description

class LaborCodeDescriptionChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.labor_code_description

class TimeEntryForm(forms.ModelForm):
    # Depart from Home Section
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control date-field'}),
        label='Date:'
    )
    initial_leave_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control leave-time-field'}),
        label='Start Time:'
    )
    initial_mileage = forms.DecimalField(
        widget=forms.NumberInput(attrs={'placeholder': 'Enter mileage at start', 'class': 'form-control mileage-field'}),
        label='Mileage at Start:'
    )
    start_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control start-time-field'}),
        label='Work Start Time:'
    )
    # Return Home Section
    end_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control end-time-field'}),
        label='Work End Time:'
    )
    final_arrive_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control arrive-time-field'}),
        label='End Time:'
    )
    final_mileage = forms.DecimalField(
        widget=forms.NumberInput(attrs={'placeholder': 'Enter mileage at end', 'class': 'form-control mileage-field'}),
        label='Mileage at End:'
    )
    activity_end_mileage = forms.DecimalField(
        widget=forms.NumberInput(attrs={'readonly': 'readonly', 'placeholder': 'Automatically calculated after saving', 'class': 'form-control readonly-field'}),
        label='Mileage After Last Job:',
        required=False
    )
    start_location = forms.ChoiceField(
        choices=TimeEntry.LOCATION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Start Location:'
    )
    end_location = forms.ChoiceField(
        choices=TimeEntry.LOCATION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='End Location:'
    )
    comments = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'cols': 50, 'class': 'form-control'}),
        required=False,
        help_text="Any additional notes or comments for this time entry."
    )
    company_vehicle_used = forms.ChoiceField(choices=TimeEntry.VEHICLE_CHOICES,
        widget=forms.RadioSelect,
        initial=False,
        label="Vehicle Used"
    )

    class Meta:
        model = TimeEntry
        fields = [
            'date', 'company_vehicle_used', 'start_location', 'end_location',
            'initial_leave_time', 'final_arrive_time', 'initial_mileage', 'final_mileage',
            'hours_on_site', 'hours_for_the_day', 'travel_time_subtract', 'hours_to_be_paid',
            'total_miles', 'travel_miles_subtract', 'miles_to_be_paid',
            'comments'
        ]
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control start-time-field'}),
            'start_location': forms.Select(attrs={'class': 'form-control'}),
            'end_location': forms.Select(attrs={'class': 'form-control'}),
        }
        
        # Explicitly exclude start_time and end_time
        exclude = ['start_time', 'end_time']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove start_time and end_time from the form fields if they're somehow still there
        self.fields.pop('start_time', None)
        self.fields.pop('end_time', None)


class JobForm(forms.ModelForm):
    id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    
    job_number = forms.ModelChoiceField(
        queryset=JobDetails.objects.all().order_by('job_number'),
        required=False,
        empty_label="Select a job number",
        widget=forms.Select(attrs={
            'class': 'form-control job-number-field', 
            'data-dependency': 'job_description_field'
        }),
        label='Job Number'
    )
    job_description = JobDescriptionChoiceField(
        queryset=JobDetails.objects.all().order_by('job_description'),
        empty_label="Select a job description",
        widget=forms.Select(attrs={
            'class': 'form-control job-description-field', 
            'data-dependency': 'job_number_field'
        }),
        label='Job Description'
    )
    labor_code = forms.ModelChoiceField(
        queryset=LaborCode.objects.all().order_by('laborcode'),
        required=False,
        empty_label="Select a labor code",
        widget=forms.Select(attrs={
            'class': 'form-control labor-code-field', 
            'data-dependency': 'labor_code_description_field'
        }),
        label='Labor Code'
    )
    labor_code_description = LaborCodeDescriptionChoiceField(
        queryset=LaborCode.objects.all().order_by('labor_code_description'),
        empty_label="Select a labor code description",
        widget=forms.Select(attrs={
            'class': 'form-control labor-code-description-field', 
            'data-dependency': 'labor_code_field'
        }),
        label='Labor Code Description'
    )

    activity_arrive_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control arrive-time-field'}),
        label='Arrive Time:'
    )
    activity_start_mileage = forms.DecimalField(
        widget=forms.NumberInput(attrs={'placeholder': 'Enter mileage at arrival', 'class': 'form-control mileage-field'}),
        label='Mileage at Arrival:'
    )
    activity_leave_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control leave-time-field'}),
        label='Leave Time:'
    )
    activity_end_mileage = forms.DecimalField(
        widget=forms.NumberInput(attrs={'placeholder': 'Enter mileage at departure', 'class': 'form-control mileage-field'}),
        label='Mileage at Departure:'
    )

    class Meta:
        model = Job
        fields = [
            'id','job_number', 'job_description',
            'labor_code', 'labor_code_description',
            'activity_arrive_time', 'activity_leave_time',
            'activity_start_mileage', 'activity_end_mileage'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['id'].required = False
        if self.instance and self.instance.pk:
            self.fields['id'].initial = self.instance.pk
            if self.instance.job_number:
                self.fields['job_number'].initial = self.instance.job_number
                self.fields['job_description'].initial = self.instance.job_number
            if self.instance.labor_code:
                self.fields['labor_code'].initial = self.instance.labor_code
                self.fields['labor_code_description'].initial = self.instance.labor_code

    def clean(self):
        cleaned_data = super().clean()
        
        if cleaned_data.get('id') == '':
            cleaned_data['id'] = None
        
        job_number = cleaned_data.get('job_number')
        job_description = cleaned_data.get('job_description')
        
        if not job_number and not job_description:
            raise forms.ValidationError('Either Job Number or Job Description must be selected.')
        
        labor_code = cleaned_data.get('labor_code')
        labor_code_description = cleaned_data.get('labor_code_description')
        
        if not labor_code and not labor_code_description:
            raise forms.ValidationError('Either Labor Code or Labor Code Description must be selected.')
        
        return cleaned_data

    def save(self, commit=True):
        job = super().save(commit=False)

        job_number = self.cleaned_data.get('job_number') or self.cleaned_data.get('job_description')
        if job_number:
            job.job_number = job_number

        labor_code = self.cleaned_data.get('labor_code') or self.cleaned_data.get('labor_code_description')
        if labor_code:
            job.labor_code = labor_code

        if commit:
            job.save()

        return job


class JobDetailsForm(forms.ModelForm):
    class Meta:
        model = JobDetails
        fields = ['job_description', 'distance_office', 'time_office']
        widgets = {
            'job_description': forms.TextInput(attrs={'class': 'form-control'}),
            'distance_office': forms.NumberInput(attrs={'class': 'form-control'}),
            'time_office': forms.NumberInput(attrs={'class': 'form-control'}),  # Use NumberInput for numeric fields
        }

    def clean_time_office(self):
        time = self.cleaned_data['time_office']
        if isinstance(time, str):
            # Convert string time to timedelta
            hours, minutes, seconds = map(int, time.split(':'))
            return timedelta(hours=hours, minutes=minutes, seconds=seconds)
        return time

class LaborCodeForm(forms.ModelForm):
    class Meta:
        model = LaborCode
        fields = ['labor_code_description']
        widgets = {
            'labor_code_description': forms.TextInput(attrs={'class': 'form-control'}),
        }
        
class TimeEntryApprovalForm(forms.ModelForm):
    """Form for submitting a time entry for approval"""
    class Meta:
        model = TimeEntryApproval
        fields = ['submitter_comments']
        widgets = {
            'submitter_comments': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Add any comments for your supervisor...'
            })
        }

class TimeEntryReviewForm(forms.ModelForm):
    """Form for reviewing a submitted time entry"""
    
    REVIEW_CHOICES = [
        ('approve', 'Approve'),
        ('reject', 'Reject')
    ]
    
    review_action = forms.ChoiceField(
        choices=REVIEW_CHOICES,
        widget=forms.RadioSelect,
        required=True,
        label='Review Action'
    )
    
    comments = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Add review comments...'
        }),
        required=False
    )

    class Meta:
        model = TimeEntryApproval
        fields = ['comments']

    def clean(self):
        cleaned_data = super().clean()
        review_action = cleaned_data.get('review_action')
        comments = cleaned_data.get('comments')

        if review_action == 'reject' and not comments:
            raise forms.ValidationError({
                'comments': 'Comments are required when rejecting a time entry.'
            })
        
        return cleaned_data