from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Max
from .forms import CustomPasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .forms import CustomPasswordChangeForm, EmployeeForm
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.contrib.auth.models import Group
from django.db import transaction
from django.conf import settings

CustomUser = get_user_model()

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create user
                    user = form.save(commit=False)
                    max_id = CustomUser.objects.aggregate(Max('id'))['id__max'] or 0
                    user.id = max_id + 1
                    
                    # Save the user first
                    user.save()
                    print(f"New user created with ID: {user.id}")
                    
                    # Handle supervisor role
                    if user.role == 'Supervisor':
                        # Get or create supervisor group
                        supervisor_group, _ = Group.objects.get_or_create(name='Supervisor')
                        # Add user to supervisor group
                        supervisor_group.user_set.add(user)
                        print(f"Added user to Supervisor group")
                    
                    # Log in the user
                    login(request, user)
                    messages.success(request, f"Account created successfully! Welcome, {user.username}.")
                    
                    # Always redirect to dashboard initially
                    return redirect('timesheets:dashboard')
                    
            except IntegrityError as e:
                print(f"IntegrityError: {e}")
                messages.error(request, "An error occurred while creating your account. Please try again.")
        else:
            print(f"Form errors: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        
        # Skip reCAPTCHA validation in development
        if settings.DEBUG or getattr(settings, 'RECAPTCHA_ENABLED', False) is False:
            if form.is_valid():
                username = form.cleaned_data.get('username')
                password = form.cleaned_data.get('password')
                try:
                    user = authenticate(username=username, password=password)
                    if user is not None:
                        login(request, user)
                        next_url = request.GET.get('next')
                        if next_url:
                            return redirect(next_url)
                        return redirect('timesheets:dashboard')
                    else:
                        messages.error(request, 'Invalid username or password.')
                except Exception as e:
                    messages.error(request, f'Authentication error: {str(e)}')
            else:
                messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomAuthenticationForm()
    
    context = {
        'form': form,
        'recaptcha_enabled': not settings.DEBUG and getattr(settings, 'RECAPTCHA_ENABLED', False)
    }
    return render(request, 'accounts/login.html', context)

@login_required
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return render(request, 'accounts/logged_out.html')
    return render(request, 'accounts/logout.html')

def logged_out_view(request):
    session_expired = request.GET.get('expired', False)
    context = {
        'session_expired': session_expired
    }
    return render(request, 'accounts/logged_out.html', context)
    
@login_required
def profile_view(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Password successfully changed.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = CustomPasswordChangeForm(request.user)
    
    return render(request, 'accounts/profile.html', {'form': form})

@login_required
def employee_list_view(request):
    """View for listing all employees"""
    # Check permissions
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'Supervisor')):
        messages.error(request, "You don't have permission to view this page.")
        return redirect('timesheets:dashboard')

    # Set appropriate view title based on user role
    if request.user.is_superuser:
        view_title = "Employee Management - All Employees"
    else:
        view_title = "Employee Management - My Team"

    # Query for employees based on user role
    if request.user.is_superuser:
        # For superusers, show all employees including other superusers
        employees = CustomUser.objects.all().order_by('role', 'last_name', 'first_name')
    elif request.user.role == 'Supervisor':
        # For supervisors, only show their supervisees
        employees = CustomUser.objects.filter(
            supervisor=request.user,
        ).order_by('last_name', 'first_name')
    else:
        employees = CustomUser.objects.none()

    # Calculate statistics
    total_employees = employees.count()
    active_employees = employees.filter(is_active=True).count()
    
    # Count by role
    field_technicians = employees.filter(role='Field Technician').count()
    lab_technicians = employees.filter(role='Lab Technician').count()
    office_support = employees.filter(role='Office Support').count()
    operations_support = employees.filter(role='Operations Support').count()
    supervisors = employees.filter(role='Supervisor').count()

    # Group employees by role for better organization
    if request.user.is_superuser:
        supervisors_list = employees.filter(role='Supervisor')
        field_technicians_list = employees.filter(role='Field Technician')
        lab_technicians_list = employees.filter(role='Lab Technician')
        office_support_list = employees.filter(role='Office Support')
        operations_support_list = employees.filter(role='Operations Support')
        
        # Combine lists with supervisors first
        employees = list(supervisors_list) + \
                   list(field_technicians_list) + \
                   list(lab_technicians_list) + \
                   list(office_support_list) + \
                   list(operations_support_list)

    context = {
        'view_title': view_title,
        'employees': employees,
        'stats': {
            'total': total_employees,
            'active': active_employees,
            'field_technicians': field_technicians,
            'lab_technicians': lab_technicians,
            'office_support': office_support,
            'operations_support': operations_support,
            'supervisors': supervisors
        },
        'is_supervisor': request.user.role == 'Supervisor' if hasattr(request.user, 'role') else False,
        'is_superuser': request.user.is_superuser
    }
    
    return render(request, 'accounts/employee_list.html', context)

@login_required
def employee_update(request, pk):
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'Supervisor')):
        messages.error(request, "You don't have permission to update employees.")
        return redirect('timesheets:dashboard')

    employee = get_object_or_404(CustomUser, pk=pk)
    
    # Check if the user has permission to edit this employee
    if not request.user.is_superuser and request.user != employee.supervisor:
        messages.error(request, "You don't have permission to edit this employee.")
        return redirect('accounts:employee_list')

    if request.method == 'POST':
        form = EmployeeForm(request.POST, instance=employee)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Get the old role before saving
                    old_role = employee.role
                    
                    employee = form.save()
                    
                    # Handle supervisor group assignment
                    supervisor_group, _ = Group.objects.get_or_create(name='Supervisor')
                    
                    # Handle role change
                    if old_role != employee.role:
                        if employee.role == 'Supervisor':
                            employee.groups.add(supervisor_group)
                            # Remove any supervisor assignment
                            employee.supervisor = None
                            employee.save()
                        else:
                            employee.groups.remove(supervisor_group)
                    
                    messages.success(request, f"Employee {employee.get_full_name()} updated successfully.")
                    return redirect('accounts:employee_list')
            except Exception as e:
                messages.error(request, f"Error updating employee: {str(e)}")
    else:
        form = EmployeeForm(instance=employee)
        
    context = {
        'view_title': f'Update Employee: {employee.get_full_name()}',  # Changed title to reflect update action
        'form': form, 
        'action': 'Update',
        'employee': employee,
        'is_supervisor': request.user.role == 'Supervisor' if hasattr(request.user, 'role') else False,
        'is_superuser': request.user.is_superuser
    }
    
    return render(request, 'accounts/employee_form.html', context)

@login_required
def employee_delete(request, pk):
    employee = get_object_or_404(CustomUser, pk=pk)
    if request.method == 'POST':
        employee.delete()
        messages.success(request, f"Employee {employee.get_full_name()} deleted successfully.")
        return redirect('accounts:employee_list')
    return render(request, 'accounts/employee_confirm_delete.html', {'employee': employee})


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.contrib.auth.models import Group
from django.utils import timezone
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Max
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta

from .models import RegistrationInvitation
from .forms import (
    CustomUserCreationForm,
    CustomAuthenticationForm,
    CustomPasswordChangeForm,
    EmployeeForm,
)

CustomUser = get_user_model()

# Helper function for sending invitation emails
def send_invitation_email(invitation, request):
    """Send invitation email to the new employee"""
    registration_url = request.build_absolute_uri(
        reverse('accounts:complete_registration', args=[str(invitation.token)])
    )
    
    context = {
        'invitation': invitation,
        'registration_url': registration_url,
    }
    
    # Render email templates
    html_message = render_to_string('registration/invitation_email.html', context)
    plain_message = render_to_string('registration/invitation_email.txt', context)
    
    try:
        # Send email
        send_mail(
            subject='Complete Your TimeSheet App Registration',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[invitation.email],
            html_message=html_message,
        )
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

@login_required
def employee_create(request):
    """
    View for creating new employees and sending registration invitations.
    """
    print("Method:", request.method)  # Debug print
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'Supervisor')):
        messages.error(request, "You don't have permission to create employees.")
        return redirect('timesheets:dashboard')

    if request.method == 'POST':
        print("POST data:", request.POST)  # Debug print
        form = EmployeeForm(request.POST)
        print("Form is valid:", form.is_valid())  # Debug print
        
        if not form.is_valid():
            print("Form errors:", form.errors)  # Debug print
            messages.error(request, "Please correct the form errors.")
            return render(request, 'accounts/employee_form.html', {
                'form': form,
                'action': 'Create',
                'view_title': 'Add New Employee',
                'is_supervisor': request.user.role == 'Supervisor' if hasattr(request.user, 'role') else False,
                'is_superuser': request.user.is_superuser
            })
            
        try:
            with transaction.atomic():
                email = form.cleaned_data['email']
                force_create = request.POST.get('force_create') == 'true'
                
                # Check for existing invitation if not forcing creation
                if not force_create:
                    existing_invitation = RegistrationInvitation.objects.filter(
                        email=email, 
                        used=False
                    ).first()
                    
                    if existing_invitation and not existing_invitation.is_expired:
                        # If still valid and not forcing creation, show resend option
                        messages.warning(
                            request,
                            f"An active invitation already exists for {email}. Would you like to resend it?"
                        )
                        context = {
                            'form': form,
                            'action': 'Create',
                            'view_title': 'Add New Employee',
                            'is_supervisor': request.user.role == 'Supervisor' if hasattr(request.user, 'role') else False,
                            'is_superuser': request.user.is_superuser,
                            'existing_invitation': existing_invitation
                        }
                        return render(request, 'accounts/employee_form.html', context)
                
                # Delete any existing invitations if forcing creation or expired
                RegistrationInvitation.objects.filter(email=email).delete()
                
                print("Creating invitation...")  # Debug print
                # Create invitation
                invitation = RegistrationInvitation.objects.create(
                    email=email,
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    role=form.cleaned_data['role'],
                    supervisor=form.cleaned_data['supervisor'],
                    distance_office=form.cleaned_data.get('distance_office'),
                    time_office=form.cleaned_data.get('time_office'),
                    invited_by=request.user
                )
                print(f"Invitation created: {invitation}")  # Debug print
                
                # Send invitation email if requested
                if form.cleaned_data.get('send_invitation', True):
                    print("Sending invitation email...")  # Debug print
                    email_sent = send_invitation_email(invitation, request)
                    if email_sent:
                        print("Email sent successfully")  # Debug print
                        messages.success(
                            request, 
                            f"Employee added successfully. An invitation has been sent to {invitation.email}"
                        )
                    else:
                        print("Email sending failed")  # Debug print
                        messages.warning(
                            request,
                            f"Employee added but there was an error sending the invitation email to {invitation.email}"
                        )
                else:
                    messages.success(request, "Employee added successfully.")
                
                return redirect('accounts:employee_list')
                
        except Exception as e:
            print(f"Error creating employee: {str(e)}")  # Debug print
            messages.error(request, "Error creating employee. Please try again.")
            return render(request, 'accounts/employee_form.html', {
                'form': form,
                'action': 'Create',
                'view_title': 'Add New Employee',
                'is_supervisor': request.user.role == 'Supervisor' if hasattr(request.user, 'role') else False,
                'is_superuser': request.user.is_superuser
            })
    else:
        form = EmployeeForm()
        
    return render(request, 'accounts/employee_form.html', {
        'form': form,
        'action': 'Create',
        'view_title': 'Add New Employee',
        'is_supervisor': request.user.role == 'Supervisor' if hasattr(request.user, 'role') else False,
        'is_superuser': request.user.is_superuser
    })
    
def complete_registration(request, token):
    """Handle the completion of registration by the invited employee"""
    invitation = get_object_or_404(RegistrationInvitation, token=token)
    
    # Check if invitation is still valid
    if not invitation.is_valid:
        if invitation.used:
            messages.error(request, "This invitation has already been used.")
        else:
            messages.error(request, "This invitation has expired.")
        return redirect('accounts:login')
    
    if request.method == 'POST':
        # Validate form data
        username = request.POST.get('username')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        
        # Get additional information
        distance_office = request.POST.get('distance_office')
        time_office = request.POST.get('time_office')
        
        errors = []
        
        # Basic validation
        if not username:
            errors.append("Username is required.")
        elif CustomUser.objects.filter(username=username).exists():
            errors.append("This username is already taken.")
            
        if not password:
            errors.append("Password is required.")
        elif password != password_confirm:
            errors.append("Passwords do not match.")
        else:
            try:
                validate_password(password)
            except ValidationError as e:
                errors.extend(e.messages)

        # Validate distance and time if provided
        try:
            if distance_office:
                distance_office = float(distance_office)
                if distance_office < 0:
                    errors.append("Distance to office cannot be negative.")
        except ValueError:
            errors.append("Invalid distance value.")

        try:
            if time_office:
                time_office = int(time_office)
                if time_office < 0:
                    errors.append("Travel time to office cannot be negative.")
        except ValueError:
            errors.append("Invalid time value.")
        
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            try:
                with transaction.atomic():
                    # Create the user with additional information
                    user = CustomUser.objects.create_user(
                        username=username,
                        email=invitation.email,
                        password=password,
                        first_name=invitation.first_name,
                        last_name=invitation.last_name,
                        role=invitation.role,
                        supervisor=invitation.supervisor,
                        distance_office=distance_office if distance_office else invitation.distance_office,
                        time_office=time_office if time_office else invitation.time_office
                    )
                    
                    # Mark invitation as used
                    invitation.used = True
                    invitation.save()
                    
                    # Add success message
                    messages.success(request, "Registration completed successfully! Please log in.")
                    
                    # Redirect to login page
                    return redirect('accounts:login')
                    
            except Exception as e:
                messages.error(request, f"Error completing registration: {str(e)}")
    
    return render(request, 'registration/complete_registration.html', {
        'invitation': invitation
    })
    
# views.py

@login_required
def manage_invitations(request):
    """View for managing pending invitations"""
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'Supervisor')):
        messages.error(request, "You don't have permission to view this page.")
        return redirect('timesheets:dashboard')

    # Get pending invitations
    if request.user.is_superuser:
        pending_invitations = RegistrationInvitation.objects.filter(
            used=False
        ).select_related('invited_by', 'supervisor').order_by('-created_at')
    else:
        pending_invitations = RegistrationInvitation.objects.filter(
            used=False,
            invited_by=request.user
        ).select_related('invited_by', 'supervisor').order_by('-created_at')

    context = {
        'view_title': 'Manage Invitations',
        'pending_invitations': pending_invitations,
        'is_supervisor': request.user.role == 'Supervisor' if hasattr(request.user, 'role') else False,
        'is_superuser': request.user.is_superuser
    }
    
    return render(request, 'accounts/manage_invitations.html', context)

@login_required
def resend_invitation(request, invitation_id):
    """Handle resending an invitation"""
    if not request.method == 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
        
    if not (request.user.is_superuser or request.user.role == 'Supervisor'):
        return JsonResponse({'success': False, 'error': 'Permission denied'})

    try:
        invitation = RegistrationInvitation.objects.get(id=invitation_id, used=False)
        
        # Check permission
        if not request.user.is_superuser and invitation.invited_by != request.user:
            return JsonResponse({'success': False, 'error': 'Permission denied'})

        # Reset expiration date
        invitation.expires_at = timezone.now() + timedelta(days=7)
        invitation.save()

        # Resend email
        if send_invitation_email(invitation, request):
            messages.success(request, f"Invitation resent to {invitation.email}")
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'Failed to send email'})

    except RegistrationInvitation.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Invitation not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def cancel_invitation(request, invitation_id):
    """Handle canceling an invitation"""
    if not request.method == 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
        
    if not (request.user.is_superuser or request.user.role == 'Supervisor'):
        return JsonResponse({'success': False, 'error': 'Permission denied'})

    try:
        invitation = RegistrationInvitation.objects.get(id=invitation_id, used=False)
        
        # Check permission
        if not request.user.is_superuser and invitation.invited_by != request.user:
            return JsonResponse({'success': False, 'error': 'Permission denied'})

        # Delete the invitation
        invitation.delete()
        messages.success(request, f"Invitation for {invitation.email} has been cancelled.")
        return JsonResponse({'success': True})

    except RegistrationInvitation.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Invitation not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

from django.contrib.auth.views import (
    PasswordResetView, 
    PasswordResetDoneView,
    PasswordResetConfirmView, 
    PasswordResetCompleteView
)
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin

class CustomPasswordResetView(SuccessMessageMixin, PasswordResetView):
    template_name = 'accounts/password_reset_form.html'
    email_template_name = 'accounts/password_reset_email.html'
    subject_template_name = 'accounts/password_reset_subject.txt'
    success_url = reverse_lazy('accounts:password_reset_done')
    success_message = "We've emailed you instructions for setting your password."
    
class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'accounts/password_reset_done.html'

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:password_reset_complete')
    
class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'accounts/password_reset_complete.html'

