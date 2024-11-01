from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import User 

from django.contrib.auth import get_user_model

CustomUser = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True, help_text='First name')
    last_name = forms.CharField(max_length=30, required=True, help_text='Last name')

    # Add role field for the user to select if they are a technician or supervisor
    role = forms.ChoiceField(
        choices=[('Technician', 'Technician'), ('Supervisor', 'Supervisor')],
        required=True,
        help_text="Select your role"
    )

    # Add supervisor field for technician to select their supervisor
    supervisor = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(role='Supervisor'), 
        required=False,
        help_text='Select your supervisor (only required for technicians)'
    )

    distance_office = forms.DecimalField(max_digits=8, decimal_places=2, required=False, help_text="Distance in miles")
    time_office = forms.IntegerField(required=False, help_text="Travel time to office in minutes")

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name', 'role', 'supervisor', 'distance_office', 'time_office', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter supervisors only when the form is initialized
        self.fields['supervisor'].queryset = CustomUser.objects.filter(role='Supervisor')

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        supervisor = cleaned_data.get('supervisor')

        # If the user selects Technician role, make sure they select a supervisor
        if role == 'Technician' and not supervisor:
            self.add_error('supervisor', 'Technicians must select a supervisor.')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.cleaned_data['role']
        user.distance_office = self.cleaned_data['distance_office']
        user.time_office = self.cleaned_data['time_office']
        if commit:
            user.save()
        return user


class CustomAuthenticationForm(AuthenticationForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'password']
        
        
class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].widget.attrs.update({'class': 'form-control'})
        self.fields['new_password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['new_password2'].widget.attrs.update({'class': 'form-control'})
        
class EmployeeForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name', 'role', 
                 'supervisor', 'distance_office', 'time_office', 'is_active']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['supervisor'].queryset = CustomUser.objects.filter(role='Supervisor')
        self.fields['is_active'].help_text = "Uncheck this to deactivate the employee's account"