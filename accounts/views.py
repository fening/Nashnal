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
                    return redirect('dashboard')
                    
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
        form = CustomAuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'accounts/login.html', {'form': form, 'error': 'Invalid credentials'})
    else:
        form = CustomAuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})

@login_required
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return redirect('login')
    else:
        return render(request, 'accounts/logout.html')
    
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
    # Check permissions
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'Supervisor')):
        messages.error(request, "You don't have permission to view this page.")
        return redirect('dashboard')

    # Set appropriate view title based on user role
    if request.user.is_superuser:
        view_title = "Employee Management - All Employees"
    else:
        view_title = "Employee Management - My Team"

    # Query for employees based on user role
    if request.user.is_superuser:
        # For superusers (admins), show all employees including supervisors
        employees = CustomUser.objects.filter(
            is_superuser=False  # Exclude other superusers
        ).order_by('role', 'last_name', 'first_name')  # Sort by role first, then name
    elif request.user.role == 'Supervisor':
        # For supervisors, only show their supervisees
        employees = CustomUser.objects.filter(
            supervisor=request.user,
            is_superuser=False,
        ).order_by('last_name', 'first_name')
    else:
        employees = CustomUser.objects.none()

    # Calculate statistics
    total_employees = employees.count()
    active_employees = employees.filter(is_active=True).count()
    technicians = employees.filter(role='Technician').count()
    supervisors = employees.filter(role='Supervisor').count()

    # Group employees by role for better organization
    if request.user.is_superuser:
        supervisors_list = employees.filter(role='Supervisor')
        technicians_list = employees.filter(role='Technician')
        
        employees = list(supervisors_list) + list(technicians_list)  # Combine lists with supervisors first

    context = {
        'view_title': view_title,  # Added view title to context
        'employees': employees,
        'stats': {
            'total': total_employees,
            'active': active_employees,
            'technicians': technicians,
            'supervisors': supervisors
        },
        'is_supervisor': request.user.role == 'Supervisor' if hasattr(request.user, 'role') else False,
        'is_superuser': request.user.is_superuser
    }
    
    return render(request, 'accounts/employee_list.html', context)



@login_required
def employee_create(request):
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'Supervisor')):
        messages.error(request, "You don't have permission to create employees.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    employee = form.save()
                    
                    # Handle supervisor group assignment
                    supervisor_group, _ = Group.objects.get_or_create(name='Supervisor')
                    
                    # Remove from supervisor group if not a supervisor
                    if employee.role != 'Supervisor' and supervisor_group in employee.groups.all():
                        employee.groups.remove(supervisor_group)
                    
                    # Add to supervisor group if is a supervisor
                    if employee.role == 'Supervisor':
                        employee.groups.add(supervisor_group)
                        # Remove any supervisor assignment as supervisors can't have supervisors
                        employee.supervisor = None
                        employee.save()
                    
                    messages.success(request, f"Employee {employee.get_full_name()} created successfully.")
                    return redirect('employee_list')
            except Exception as e:
                messages.error(request, f"Error creating employee: {str(e)}")
    else:
        form = EmployeeForm()
    context = { 
        'view_title': 'Employee Management',      
        'form': form, 
        'action': 'Create',
        'is_supervisor': request.user.role == 'Supervisor' if hasattr(request.user, 'role') else False,
        'is_superuser': request.user.is_superuser}
    return render(request, 'accounts/employee_form.html', context)

@login_required
def employee_update(request, pk):
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'Supervisor')):
        messages.error(request, "You don't have permission to update employees.")
        return redirect('dashboard')

    employee = get_object_or_404(CustomUser, pk=pk)
    
    # Check if the user has permission to edit this employee
    if not request.user.is_superuser and request.user != employee.supervisor:
        messages.error(request, "You don't have permission to edit this employee.")
        return redirect('employee_list')

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
                    return redirect('employee_list')
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
        return redirect('employee_list')
    return render(request, 'accounts/employee_confirm_delete.html', {'employee': employee})
