from django import forms
from .models import TimeEntry, Job

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
            'date', 'company_vehicle_used','start_location', 'initial_leave_time', 'initial_mileage',  # Depart from Home
            'end_location', 'final_arrive_time', 'final_mileage', 'activity_end_mileage','comments'  # Return Home
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
    # Jobs Section
    activity_arrive_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control arrive-time-field'}),
        label='Arrive Time:'
    )
    activity_start_mileage = forms.DecimalField(
        widget=forms.NumberInput(attrs={'placeholder': 'Enter mileage at arrival', 'class': 'form-control mileage-field'}),
        label='Mileage at Arrival:'
    )
    labor_code = forms.ChoiceField(
        choices=[(code, code) for code, _ in Job.LABOR_CODE_CHOICES],
        widget=forms.Select(attrs={'class': 'form-control labor-code-field', 'onchange': 'updateLaborCodeDescription(this)'}),
        label='Labor Code:'
    )
    labor_code_description = forms.CharField(
        widget=forms.TextInput(attrs={'readonly': 'readonly', 'placeholder': 'Enter labor code description', 'class': 'form-control readonly-field'}),
        label='Labor Code Description:',
        required=False 
    )
    description = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Describe the work performed', 'rows': 4, 'class': 'form-control description-field'}),
        label='Description:'
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
        fields = ['labor_code', 'labor_code_description', 'description', 'activity_arrive_time', 'activity_start_mileage', 'activity_leave_time', 'activity_end_mileage']
        widgets = {
            'labor_code': forms.Select(attrs={'class': 'form-control labor-code-field'}),
            'labor_code_description': forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control readonly-field'}),
            'description': forms.Textarea(attrs={'placeholder': 'Describe the work performed', 'rows': 4, 'class': 'form-control description-field'}),
            'activity_arrive_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control arrive-time-field'}),
            'activity_start_mileage': forms.NumberInput(attrs={'class': 'form-control mileage-field'}),
            'activity_leave_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control leave-time-field'}),
            'activity_end_mileage': forms.NumberInput(attrs={'class': 'form-control mileage-field'}),
        }
