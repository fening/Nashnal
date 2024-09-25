from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Max
from .forms import CustomPasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .forms import CustomPasswordChangeForm

CustomUser = get_user_model()

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                max_id = CustomUser.objects.aggregate(Max('id'))['id__max'] or 0
                user.id = max_id + 1  # Explicitly set the ID
                print(f"Attempting to create user with ID: {user.id}")
                user.save()
                print(f"New user created with ID: {user.id}")
                login(request, user)
                messages.success(request, f"Account created successfully! Welcome, {user.username}.")
                
                if user.role == 'Supervisor':
                    return redirect('supervisor_dashboard')
                else:
                    return redirect('dashboard')
            except IntegrityError as e:
                print(f"IntegrityError: {e}")
                messages.error(request, "An error occurred while creating your account. Please try again.")
        else:
            print(f"Form errors: {form.errors}")
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
    employees = CustomUser.objects.all().order_by('last_name', 'first_name')
    return render(request, 'accounts/employee_list.html', {'employees': employees})