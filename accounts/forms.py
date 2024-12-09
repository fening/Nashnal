import logging

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import User 
from .models import RegistrationInvitation
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox

from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

CustomUser = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True, help_text='First name')
    last_name = forms.CharField(max_length=30, required=True, help_text='Last name')

    role = forms.ChoiceField(
        choices=CustomUser.ROLE_CHOICES,
        required=True,
        help_text="Select your role"
    )

    supervisor = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(role='Supervisor'), 
        required=False,
        help_text='Select your supervisor (required for non-supervisor roles)'
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

        # If the user selects any role other than Supervisor, make sure they select a supervisor
        if role != 'Supervisor' and not supervisor:
            self.add_error('supervisor', 'A supervisor must be selected for non-supervisor roles.')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.cleaned_data['role']
        user.distance_office = self.cleaned_data['distance_office']
        user.time_office = self.cleaned_data['time_office']
        if commit:
            user.save()
        return user


import logging
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox

logger = logging.getLogger(__name__)

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-xl',
        'placeholder': 'Username',
        'required': True
    }))
    
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-xl',
        'placeholder': 'Password',
        'required': True
    }))
    
    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox(
        attrs={
            'data-theme': 'light',
            'data-size': 'normal',
            'data-callback': 'onRecaptchaSuccess',         # Added callback
            'data-expired-callback': 'onRecaptchaExpired', # Added expired callback
        }
    ))

    def clean(self):
        logger.debug("Starting form validation")
        try:
            cleaned_data = super().clean()
            logger.debug(f"Form data: {self.data}")
            logger.debug(f"Cleaned data: {cleaned_data}")
            if 'g-recaptcha-response' in self.data:
                logger.debug("reCAPTCHA response received")
            else:
                logger.warning("No reCAPTCHA response in form data")
            return cleaned_data
        except Exception as e:
            logger.error(f"Error in form validation: {str(e)}")
            raise


class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].widget.attrs.update({'class': 'form-control'})
        self.fields['new_password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['new_password2'].widget.attrs.update({'class': 'form-control'})
        
from django import forms
from django.contrib.auth import get_user_model
from .models import RegistrationInvitation

CustomUser = get_user_model()

class EmployeeForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    send_invitation = forms.BooleanField(
        initial=True,
        required=False,
        help_text="Send registration invitation email to the employee"
    )
    custom_role_title = forms.CharField(
        label='Title',
        max_length=50, 
        required=False,
        help_text="Required when 'Other' is selected as role"
    )

    class Meta:
        model = CustomUser
        fields = [
            'email', 'first_name', 'last_name', 'role','custom_role_title',
            'supervisor', 'distance_office', 'time_office',
            
        ]
        widgets = {
            'role': forms.Select(attrs={'class': 'form-control'}),
            'supervisor': forms.Select(attrs={'class': 'form-control'}),
            'distance_office': forms.NumberInput(attrs={'class': 'form-control'}),
            'time_office': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Update supervisor queryset to include active supervisors
        self.fields['supervisor'].queryset = CustomUser.objects.filter(
            role='Supervisor',
            is_active=True
        ).order_by('first_name', 'last_name')
        
        # Make supervisor field not required by default
        self.fields['supervisor'].required = False
        
        # Make some fields required
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['role'].required = True
        
        # Add help text
        self.fields['distance_office'].help_text = "Distance in miles"
        self.fields['time_office'].help_text = "Travel time to office in minutes"

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Exclude the current instance when checking for existing emails
        qs = CustomUser.objects.filter(email=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("An employee with this email already exists.")
        # Check if there's a pending invitation
        if RegistrationInvitation.objects.filter(email=email, used=False).exists():
            raise forms.ValidationError("A pending invitation already exists for this email.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        supervisor = cleaned_data.get('supervisor')
        custom_role_title = cleaned_data.get('custom_role_title')

        # Require supervisor for non-supervisor roles
        if role and role != 'Supervisor' and not supervisor:
            self.add_error('supervisor', 'A supervisor must be selected for non-supervisor roles.')
        if role == 'Other' and not custom_role_title:
            self.add_error('custom_role_title', 'Please specify a custom role title.')

