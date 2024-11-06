# Python standard library imports
from datetime import datetime, timedelta
from decimal import Decimal
import json
import logging

# Django core imports
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import (Count,F,Max,Prefetch,Q,Sum,ExpressionWrapper,fields,)
from django.db.models.functions import ExtractYear, ExtractMonth
from django.forms import inlineformset_factory, formset_factory
from django.http import JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.utils import timezone
from django.utils.functional import cached_property
from django.views.decorators.cache import cache_page

# Third-party imports
from rest_framework import viewsets
from functools import wraps

# Local imports
from .models import (TimeEntry,Job,JobDetails,LaborCode,TimeEntryApproval,)
from .forms import (TimeEntryForm,JobForm,JobDetailsForm,LaborCodeForm,TimeEntryReviewForm,TimeEntryApprovalForm,)
from .formsets import JobFormSet

def cache_per_user(timeout=300):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Create a cache key based on the user and request parameters
            cache_key = f"timesheet_list_{request.user.id}_{request.GET.urlencode()}"
            response = cache.get(cache_key)
            
            if response is None:
                response = view_func(request, *args, **kwargs)
                cache.set(cache_key, response, timeout)
            
            return response
        return _wrapped_view
    return decorator

logger = logging.getLogger(__name__)


User = get_user_model()

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)
    
from rest_framework.views import APIView
from rest_framework.response import Response

from .serializers import TimeEntrySerializer

class TimeEntryViewSet(viewsets.ModelViewSet):
    queryset = TimeEntry.objects.all()
    serializer_class = TimeEntrySerializer
    

@login_required
def time_entry_detail(request, pk):
    time_entry = get_object_or_404(TimeEntry, pk=pk)
    context = {
        'view_title': f'Timesheet Entry - {time_entry.date}',
        'time_entry': time_entry,
    }
    return render(request, 'timesheets/time_entry_detail.html', context)

@login_required
@cache_per_user(timeout=300)
def time_entry_list(request):
    # Initialize role flags
    is_superuser = request.user.is_superuser
    is_supervisor = hasattr(request.user, 'role') and request.user.role == 'Supervisor'
    
    # Get pagination parameters
    page_number = request.GET.get('page', 1)
    entries_per_page = 25

    # Base queryset with optimized joins
    queryset = TimeEntry.objects.select_related(
        'user',
        'approval'
    ).prefetch_related(
        Prefetch(
            'jobs',
            queryset=Job.objects.order_by('activity_arrive_time')
        )
    )

    # Filter queryset based on user role
    if is_superuser:
        # Superusers can see all time entries
        pass  # No additional filtering
    elif is_supervisor:
        # Supervisors can see their team members' time entries
        team_member_ids = User.objects.filter(supervisor=request.user).values_list('id', flat=True)
        queryset = queryset.filter(user__in=team_member_ids)
    else:
        # Regular users can only see their own time entries
        queryset = queryset.filter(user=request.user)

    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        queryset = queryset.filter(
            Q(user__username__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(jobs__job_number__job_description__icontains=search_query) |
            Q(jobs__labor_code__labor_code_description__icontains=search_query) |
            Q(approval__status__icontains=search_query) |
            Q(date__icontains=search_query) |
            Q(hours_for_the_day__icontains=search_query) |
            Q(total_miles__icontains=search_query)
        ).distinct()

    # Sorting functionality
    sort_by = request.GET.get('sort_by', '-date')
    valid_sort_fields = {
        'date': 'date',
        '-date': '-date',
        'start_time': 'start_time',
        '-start_time': '-start_time',
        'end_time': 'end_time',
        '-end_time': '-end_time',
        'hours_for_the_day': 'hours_for_the_day',
        '-hours_for_the_day': '-hours_for_the_day',
        'total_miles': 'total_miles',
        '-total_miles': '-total_miles',
        'miles_to_be_paid': 'miles_to_be_paid',
        '-miles_to_be_paid': '-miles_to_be_paid',
        'hours_to_be_paid': 'hours_to_be_paid',
        '-hours_to_be_paid': '-hours_to_be_paid',
    }
    
    if is_superuser or is_supervisor:
        valid_sort_fields.update({
            'user': 'user__username',
            '-user': '-user__username'
        })

    sort_field = valid_sort_fields.get(sort_by, '-date')
    queryset = queryset.order_by(sort_field)

    # Create paginator
    paginator = Paginator(queryset, entries_per_page)
    try:
        page_obj = paginator.page(page_number)
    except:
        page_obj = paginator.page(1)

    # If supervisor, include list of team members for filtering
    all_users = None
    if is_superuser:
        all_users = User.objects.all().order_by('first_name', 'last_name')
    elif is_supervisor:
        all_users = User.objects.filter(supervisor=request.user).order_by('first_name', 'last_name')

    context = {
        'view_title': 'Time Entries',
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_by': sort_by,
        'valid_sort_fields': valid_sort_fields.keys(),
        'entries_per_page': entries_per_page,
        'total_entries': paginator.count,
        'start_index': page_obj.start_index(),
        'end_index': page_obj.end_index(),
        'is_superuser': is_superuser,
        'is_supervisor': is_supervisor,
        'all_users': all_users,
        'selected_user_id': request.GET.get('user'),
    }

    return render(request, 'timesheets/time_entry_list.html', context)

@login_required
def time_entry_create(request):
    JobFormSet = formset_factory(JobForm, extra=1, can_delete=True)
    
    if request.method == 'POST':
        form = TimeEntryForm(request.POST)
        formset = JobFormSet(request.POST)
        
        print(f"Form is valid: {form.is_valid()}")
        print(f"Formset is valid: {formset.is_valid()}")
        
        if form.is_valid() and formset.is_valid():
            time_entry = form.save(commit=False)
            time_entry.user = request.user
            time_entry.save()
            
            print(f"Number of forms in formset: {len(formset)}")
            
            for job_form in formset:
                print(f"Job form cleaned data: {job_form.cleaned_data}")
                if job_form.cleaned_data and not job_form.cleaned_data.get('DELETE', False):
                    job = job_form.save(commit=False)
                    job.time_entry = time_entry
                    job.save()
                    print(f"Saved job: {job}")
            
            return redirect('time_entry_detail', pk=time_entry.pk)
        else:
            print(f"Form errors: {form.errors}")
            print(f"Formset errors: {formset.errors}")
    else:
        form = TimeEntryForm()
        formset = JobFormSet()
        
    context = {
        'view_title': 'Create Time Entry',
        'form': form,
        'job_formset': formset
    }
    return render(request, 'timesheets/time_entry_form.html', context)
    
@login_required
def time_entry_edit(request, pk):
    time_entry = get_object_or_404(TimeEntry, pk=pk)

    JobFormSet = inlineformset_factory(
        TimeEntry,
        Job,
        form=JobForm,
        extra=0,
        can_delete=True,
        min_num=1,
        validate_min=True
    )

    if request.method == 'POST':
        form = TimeEntryForm(request.POST, instance=time_entry)
        formset = JobFormSet(request.POST, instance=time_entry, prefix='jobs')

        print("POST data:", request.POST)
        print(f"Form is valid: {form.is_valid()}")
        print(f"Formset is valid: {formset.is_valid()}")
        
        logger.debug(f"POST data: {request.POST}")
        logger.debug(f"Form is valid: {form.is_valid()}")
        logger.debug(f"Formset is valid: {formset.is_valid()}")

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    time_entry = form.save()
                    instances = formset.save(commit=False)
                    for instance in instances:
                        instance.time_entry = time_entry
                        instance.save()
                    formset.save_m2m()
                    
                    # Delete the removed instances
                    for obj in formset.deleted_objects:
                        obj.delete()

                    if time_entry.jobs.count() == 0:
                        raise ValueError("At least one job must be present.")

                messages.success(request, "Time entry updated successfully.")
                return redirect('time_entry_detail', pk=time_entry.pk)
            except ValueError as e:
                messages.error(request, str(e))
            except Exception as e:
                logger.exception("Error saving time entry")
                messages.error(request, f"An error occurred while saving: {str(e)}")
        else:
            logger.error(f"Form errors: {form.errors}")
            logger.error(f"Formset errors: {formset.errors}")
            messages.error(request, "Please correct the errors below.")
    else:
        form = TimeEntryForm(instance=time_entry)
        formset = JobFormSet(instance=time_entry, prefix='jobs')  

    context = {
        'view_title': 'Edit Time Entry',
        'form': form,
        'job_formset': formset,
        'edit': True
    }
    return render(request, 'timesheets/time_entry_form.html', context)


@login_required
def time_entry_delete(request, pk):
    time_entry = get_object_or_404(TimeEntry, pk=pk)
    if request.method == 'POST':
        time_entry.delete()
        return redirect('time_entry_list')
    
    return render(request, 'timesheets/time_entry_confirm_delete.html', {'time_entry': time_entry})

@login_required
def supervisor_dashboard(request):
    """
    View for supervisor dashboard showing team members, pending approvals, and recent activity
    """
    # Allow both superusers and supervisors to access
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'Supervisor')):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')

    # Get supervisor's team members with caching
    cache_key = f'team_members_{request.user.id}'
    team_members = cache.get(cache_key)
    if team_members is None:
        if request.user.is_superuser:
            # Superuser can see all users
            team_members = CustomUser.objects.all()
        else:
            # Regular supervisor sees their team members
            team_members = CustomUser.objects.filter(supervisor=request.user)
        team_members = team_members.filter(is_active=True).select_related('supervisor').order_by('first_name', 'last_name')
        cache.set(cache_key, team_members, 300)  # Cache for 5 minutes

    # Get pending approvals with related data
    if request.user.is_superuser:
        # Superuser sees all pending approvals
        pending_approvals = TimeEntryApproval.objects.filter(status='pending')
    else:
        # Regular supervisor sees their team's pending approvals
        pending_approvals = TimeEntryApproval.objects.filter(
            time_entry__user__supervisor=request.user,
            status='pending'
        )

    # Get recent approved/rejected entries
    if request.user.is_superuser:
        # Superuser sees all recent reviews
        recent_reviews = TimeEntryApproval.objects.filter(
            status__in=['approved', 'rejected']
        )
    else:
        # Regular supervisor sees their team's recent reviews
        recent_reviews = TimeEntryApproval.objects.filter(
            time_entry__user__supervisor=request.user,
            status__in=['approved', 'rejected']
        )
    recent_reviews = recent_reviews.select_related(
        'time_entry',
        'time_entry__user',
        'reviewed_by'
    ).order_by('-reviewed_at')[:5]

    # Calculate team statistics
    if request.user.is_superuser:
        # Calculate stats for all users
        total_hours_this_month = TimeEntry.objects.filter(
            date__month=timezone.now().month,
            date__year=timezone.now().year
        )
    else:
        # Calculate stats for supervisor's team only
        total_hours_this_month = TimeEntry.objects.filter(
            user__in=team_members,
            date__month=timezone.now().month,
            date__year=timezone.now().year
        )
    total_hours = total_hours_this_month.aggregate(total_hours=Sum('hours_to_be_paid'))['total_hours'] or 0

    team_stats = {
        'total_members': team_members.count(),
        'active_members': team_members.filter(is_active=True).count(),
        'pending_approvals': pending_approvals.count(),
        'total_approved': TimeEntryApproval.objects.filter(
            time_entry__user__in=team_members,
            status='approved'
        ).count(),
        'total_hours_this_month': round(total_hours, 2)
    }

    context = {
        'view_title': 'Supervisor Dashboard',
        'team_members': team_members,
        'pending_approvals': pending_approvals,
        'recent_reviews': recent_reviews,
        'team_stats': team_stats,
        'is_supervisor': True,
    }

    return render(request, 'timesheets/supervisor_dashboard.html', context)



CustomUser = get_user_model()
@login_required
def team_timesheets(request):
    """View for supervisors and superusers to see team timesheets"""
    # Allow both superusers and supervisors to access
    if not (request.user.is_superuser or (hasattr(request.user, 'role') or request.user.role == 'Supervisor')):
        messages.error(request, "You don't have permission to view this page.")
        return redirect('dashboard')

    # Get all team members based on role
    if request.user.is_superuser:
        team_members = CustomUser.objects.all().order_by('first_name', 'last_name')
    else:
        team_members = CustomUser.objects.filter(supervisor=request.user).order_by('first_name', 'last_name')

    # Get date range from request or default to current month
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if not start_date or not end_date:
        today = timezone.now().date()
        start_date = today.replace(day=1)  # First day of current month
        end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)  # Last day of current month
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    # Get selected team member if any
    selected_member_id = request.GET.get('member')
    if selected_member_id:
        timesheets = TimeEntry.objects.filter(
            user_id=selected_member_id,
            date__range=[start_date, end_date]
        )
    else:
        # Get all timesheets for the date range
        if request.user.is_superuser:
            timesheets = TimeEntry.objects.filter(date__range=[start_date, end_date])
        else:
            timesheets = TimeEntry.objects.filter(
                user__in=team_members,
                date__range=[start_date, end_date]
            )

    # Add select_related and prefetch_related for optimization
    timesheets = timesheets.select_related('user').prefetch_related('jobs').order_by('-date')

    # Calculate statistics
    stats = {
        'total_entries': timesheets.count(),
        'total_hours': timesheets.aggregate(Sum('hours_to_be_paid'))['hours_to_be_paid__sum'] or 0,
        'total_members': team_members.count(),
        'pending_approvals': TimeEntryApproval.objects.filter(
            time_entry__user__in=team_members,
            status='pending'
        ).count(),
    }

    context = {
        'view_title': 'Team Timesheets',
        'team_members': team_members,
        'timesheets': timesheets,
        'stats': stats,
        'start_date': start_date,
        'end_date': end_date,
        'selected_member_id': selected_member_id,
        'is_superuser': request.user.is_superuser
    }

    return render(request, 'timesheets/team_timesheets.html', context)

@login_required
def user_summary_report(request):
    # Initialize context variables for user permissions
    is_superuser = request.user.is_superuser
    is_supervisor = hasattr(request.user, 'role') and request.user.role == 'Supervisor'
    
    # Determine the available users based on permissions
    if is_superuser:
        # Superusers can see all users
        all_users = User.objects.all().order_by('first_name', 'last_name')
    elif is_supervisor:
        # Supervisors can only see their team members
        all_users = User.objects.filter(supervisor=request.user).order_by('first_name', 'last_name')
    else:
        all_users = None

    # Get the selected user
    selected_user_id = request.GET.get('user')
    if selected_user_id:
        if is_superuser:
            selected_user = User.objects.filter(id=selected_user_id).first()
        elif is_supervisor:
            # Ensure supervisor can only access their team members
            selected_user = User.objects.filter(
                id=selected_user_id,
                supervisor=request.user
            ).first()
        else:
            selected_user = None
    else:
        selected_user = request.user

    # If no valid selection, default to current user
    if not selected_user:
        selected_user = request.user

    # Get the selected week or default to the current week
    week_start = request.GET.get('week_start')
    if week_start:
        try:
            week_start = timezone.datetime.strptime(week_start, '%Y-%m-%d').date()
        except ValueError:
            week_start = None
    
    if not week_start:
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())  # Monday

    week_end = week_start + timedelta(days=6)  # Sunday

    # Filter time entries for the selected user and week with related job data
    time_entries = TimeEntry.objects.filter(
        user=selected_user, 
        date__range=[week_start, week_end]
    ).prefetch_related('jobs', 'jobs__labor_code', 'approval').select_related('user')

    # Calculate weekly hours per labor code and day
    weekly_hours = {}
    daily_totals = {day: 0.00 for day in ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']}
    total_hours_for_week = 0.00

    # Process time entries and jobs
    for entry in time_entries:
        for job in entry.jobs.all():
            day_of_week = entry.date.strftime('%A')
            if job.labor_code.laborcode not in weekly_hours:
                weekly_hours[job.labor_code.laborcode] = {
                    "description": job.job_description,
                    "labor_code_description": job.labor_code_description,
                    "hours": {day: 0.00 for day in ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']}
                }

            # Calculate hours for this job
            if entry.hours_to_be_paid:
                job_hours = float(entry.hours_to_be_paid)
                weekly_hours[job.labor_code.laborcode]["hours"][day_of_week] += job_hours
                daily_totals[day_of_week] += job_hours
                total_hours_for_week += job_hours

    # Calculate regular and overtime hours
    total_regular_hours = min(total_hours_for_week, 40.00)
    total_overtime_hours = max(0.00, total_hours_for_week - 40.00)
    total_double_time_hours = 0.00  # Logic for double time if needed
    grand_total_hours = total_hours_for_week

    # Check for pending approvals
    pending_approvals = TimeEntryApproval.objects.filter(
        time_entry__user=selected_user,
        time_entry__date__range=[week_start, week_end],
        status='pending'
    ).exists()

    context = {
        'view_title': 'Summary Report',
        'time_entries': time_entries,
        'weekly_hours': weekly_hours,
        'total_regular_hours': total_regular_hours,
        'total_overtime_hours': total_overtime_hours,
        'total_double_time_hours': total_double_time_hours,
        'grand_total_hours': grand_total_hours,
        'daily_totals': daily_totals,
        'all_users': all_users,
        'selected_user': selected_user,
        'week_start': week_start,
        'week_end': week_end,
        'is_superuser': is_superuser,
        'is_supervisor': is_supervisor,
        'pending_approvals': pending_approvals,
    }

    return render(request, 'timesheets/summary_report.html', context)

@login_required
def add_job_to_time_entry(request):
    today = timezone.now().date()
    
    # Get all TimeEntries for today for the current user
    time_entries = TimeEntry.objects.filter(user=request.user, date=today).order_by('-id')
    
    if time_entries.exists():
        time_entry = time_entries.first()  # Get the most recent entry
        created = False
    else:
        # If no TimeEntry exists for today, create a new one
        time_entry = TimeEntry.objects.create(
            user=request.user,
            date=today,
            start_time=timezone.now().time(),
            end_time=timezone.now().time(),
            initial_leave_time=timezone.now().time(),
            final_arrive_time=timezone.now().time(),
        )
        created = True
        messages.info(request, "A new Time Entry has been created for today.")
    
    JobFormSet = inlineformset_factory(
        TimeEntry, 
        Job, 
        form=JobForm, 
        extra=1, 
        can_delete=True,  # Allow job deletion
        min_num=1,  # Ensure at least one job form is always present
        validate_min=True
    )

    if request.method == 'POST':
        formset = JobFormSet(request.POST, instance=time_entry)
        if formset.is_valid():
            instances = formset.save(commit=False)
            for instance in instances:
                instance.time_entry = time_entry
                instance.save()
            formset.save_m2m()  # Save many-to-many relationships if any
            time_entry.save()  # This will trigger the recalculation of hours and mileage
            messages.success(request, "Jobs have been successfully added/updated.")
            return redirect('time_entry_detail', pk=time_entry.pk)
        else:
            messages.error(request, "There was an error in your form. Please check and try again.")
    else:
        formset = JobFormSet(instance=time_entry)

    return render(request, 'timesheets/add_job.html', {
        'formset': formset,
        'time_entry': time_entry,
        'created': created,
    })
    
import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Avg
from django.utils import timezone
from datetime import datetime, timedelta
import logging

# Initialize logger
logger = logging.getLogger(__name__)

@login_required
def dashboard(request):
    # Initialize permission flags
    is_superuser = request.user.is_superuser
    is_supervisor = hasattr(request.user, 'role') and request.user.role == 'Supervisor'
    
    # Get date range from request, default to current week if not provided
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not start_date or not end_date:
        today = timezone.now().date()
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
        logger.debug(f"No date range provided. Using default: {start_date} to {end_date}")
    else:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            logger.debug(f"Received date range: {start_date} to {end_date}")
        except ValueError:
            logger.error(f"Invalid date format: start_date={start_date}, end_date={end_date}")
            today = timezone.now().date()
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)
            logger.debug(f"Using default date range due to error: {start_date} to {end_date}")

    # Determine available users based on permissions
    if is_superuser:
        all_users = User.objects.all().order_by('first_name', 'last_name')
        logger.debug(f"User is superuser. Total users: {all_users.count()}")
    elif is_supervisor:
        # Get supervisor's team members
        all_users = User.objects.filter(
            supervisor=request.user,
            is_active=True
        ).select_related('supervisor').order_by('first_name', 'last_name')
        logger.debug(f"User is supervisor. Team members: {all_users.count()}")
    else:
        all_users = None
        logger.debug("User is neither superuser nor supervisor.")

    # Get and validate selected user
    selected_user_id = request.GET.get('user_id')  # Changed from 'user' to 'user_id'
    logger.debug(f"Selected user_id from GET: {selected_user_id}")
    if selected_user_id:
        try:
            selected_user_id = int(selected_user_id)
            logger.debug(f"Parsed user_id as integer: {selected_user_id}")
        except ValueError:
            logger.error(f"Invalid user_id value: {selected_user_id}")
            selected_user_id = None

    if selected_user_id:
        if is_superuser:
            selected_user = User.objects.filter(id=selected_user_id).first()
            logger.debug(f"Superuser selected user: {selected_user}")
        elif is_supervisor:
            selected_user = User.objects.filter(
                id=selected_user_id,
                supervisor=request.user
            ).first()
            logger.debug(f"Supervisor selected user: {selected_user}")
        else:
            selected_user = None
            logger.debug("User is neither superuser nor supervisor. Selected user set to None.")
    else:
        selected_user = request.user
        logger.debug(f"No user_id provided or invalid. Defaulting to current user: {selected_user}")

    # Default to current user if no valid selection
    if not selected_user:
        selected_user = request.user
        logger.debug("Selected user was None. Defaulting to current user.")

    logger.debug(f"Final selected user: {selected_user}")

    # Get time entries for selected user
    entries = TimeEntry.objects.filter(
        user=selected_user,
        date__range=[start_date, end_date]
    )
    logger.debug(f"Time entries found: {entries.count()}")

    # Calculate statistics
    total_hours = entries.aggregate(Sum('hours_for_the_day'))['hours_for_the_day__sum'] or 0
    total_entries = entries.count()
    recent_entries = entries.order_by('-date')[:5]
    logger.debug(f"Total hours: {total_hours}, Total entries: {total_entries}")

    # Calculate labor code distribution
    labor_code_data = list(Job.objects.filter(
        time_entry__user=selected_user,
        time_entry__date__range=[start_date, end_date]
    ).values('labor_code__laborcode', 'labor_code__labor_code_description').annotate(
        count=Sum('time_entry__hours_for_the_day')
    ))
    logger.debug(f"Labor code data: {labor_code_data}")

    # Calculate daily hours
    daily_hours_data = list(entries.values('date')
        .annotate(hours=Sum('hours_for_the_day'))
        .order_by('date'))
    logger.debug(f"Daily hours data: {daily_hours_data}")

    # Initialize additional context variables
    hours_trend = 0
    jobs_trend = 0
    avg_daily_hours = 0
    daily_hours_trend = 0
    total_jobs = 0
    mileage_efficiency = 0
    total_mileage = 0
    unread_notifications_count = 0
    recent_notifications = None
    pending_approvals = None
    team_members = None
    approved_entries = 0

    # Get team statistics and additional data for supervisors
    if is_supervisor:
        pending_approvals = TimeEntryApproval.objects.filter(
            time_entry__user__supervisor=request.user,
            status='pending'
        )
        approved_entries = TimeEntryApproval.objects.filter(
            time_entry__user__supervisor=request.user,
            status='approved'
        ).count()
        total_mileage = TimeEntry.objects.filter(
            user__in=all_users,
            date__range=[start_date, end_date]
        ).aggregate(Sum('miles_to_be_paid'))['miles_to_be_paid__sum'] or 0
        team_members = all_users
        unread_notifications_count = ApprovalNotification.objects.filter(
            recipient=request.user,
            read=False
        ).count()
        recent_notifications = ApprovalNotification.objects.filter(
            recipient=request.user
        ).order_by('-created_at')[:5]
        logger.debug(f"Supervisor team stats: Total Members={all_users.count()}, Active Members={all_users.filter(is_active=True).count()}, Pending Approvals={pending_approvals.count()}, Total Approved={approved_entries}")

        team_stats = {
            'total_members': all_users.count(),
            'active_members': all_users.filter(is_active=True).count(),
            'pending_approvals': pending_approvals.count(),
            'total_hours': TimeEntry.objects.filter(
                user__in=all_users,
                date__range=[start_date, end_date]
            ).aggregate(Sum('hours_for_the_day'))['hours_for_the_day__sum'] or 0,
            'total_approved': approved_entries,
        }
    else:
        team_stats = None

    # Calculate trends and additional stats for regular users and supervisors viewing a team member
    if (not is_supervisor and not is_superuser) or (is_supervisor and selected_user != request.user):
        # Define the previous period (e.g., previous week)
        previous_start_date = start_date - timedelta(days=7)
        previous_end_date = end_date - timedelta(days=7)

        # Hours Trend
        last_period_hours = TimeEntry.objects.filter(
            user=selected_user,
            date__range=[previous_start_date, previous_end_date]
        ).aggregate(Sum('hours_for_the_day'))['hours_for_the_day__sum'] or 0
        hours_trend = ((total_hours - last_period_hours) / last_period_hours * 100) if last_period_hours else 100
        logger.debug(f"Hours trend: {hours_trend}% (Current: {total_hours}, Previous: {last_period_hours})")

        # Jobs Trend
        total_jobs = Job.objects.filter(
            time_entry__user=selected_user,
            time_entry__date__range=[start_date, end_date]
        ).count()
        last_period_jobs = Job.objects.filter(
            time_entry__user=selected_user,
            time_entry__date__range=[previous_start_date, previous_end_date]
        ).count()
        jobs_trend = ((total_jobs - last_period_jobs) / last_period_jobs * 100) if last_period_jobs else 100
        logger.debug(f"Jobs trend: {jobs_trend}% (Current: {total_jobs}, Previous: {last_period_jobs})")

        # Average Daily Hours
        avg_daily_hours = entries.aggregate(Avg('hours_for_the_day'))['hours_for_the_day__avg'] or 0
        logger.debug(f"Average daily hours: {avg_daily_hours}")

        # Daily Hours Trend
        last_period_avg_daily_hours = TimeEntry.objects.filter(
            user=selected_user,
            date__range=[previous_start_date, previous_end_date]
        ).aggregate(Avg('hours_for_the_day'))['hours_for_the_day__avg'] or 0
        daily_hours_trend = ((avg_daily_hours - last_period_avg_daily_hours) / last_period_avg_daily_hours * 100) if last_period_avg_daily_hours else 100
        logger.debug(f"Daily hours trend: {daily_hours_trend}% (Current: {avg_daily_hours}, Previous: {last_period_avg_daily_hours})")

        # Mileage Statistics
        total_mileage = TimeEntry.objects.filter(
            user=selected_user,
            date__range=[start_date, end_date]
        ).aggregate(Sum('miles_to_be_paid'))['miles_to_be_paid__sum'] or 0
        target_mileage = 100  # Example target, adjust as needed
        mileage_efficiency = (total_mileage / target_mileage * 100) if target_mileage else 0
        logger.debug(f"Total mileage: {total_mileage}, Mileage efficiency: {mileage_efficiency}%")

        # Recent Notifications
        recent_notifications = ApprovalNotification.objects.filter(
            recipient=selected_user
        ).order_by('-created_at')[:5]
        logger.debug(f"Recent notifications count: {recent_notifications.count()}")

    context = {
        'view_title': 'Dashboard',
        'selected_user': selected_user,
        'total_hours': round(total_hours, 2),
        'total_entries': total_entries,
        'recent_entries': recent_entries,
        'labor_code_data': json.dumps(labor_code_data, cls=DecimalEncoder),
        'daily_hours_data': json.dumps(daily_hours_data, cls=DecimalEncoder, default=str),
        'start_date': start_date,
        'end_date': end_date,
        'all_users': all_users,
        'team_stats': team_stats,
        'is_admin': is_superuser,
        'is_supervisor': is_supervisor,
        # Supervisor specific
        'pending_approvals': pending_approvals if is_supervisor else None,
        'team_members': team_members if is_supervisor else None,
        'unread_notifications_count': unread_notifications_count if is_supervisor else 0,
        'recent_notifications': recent_notifications if is_supervisor else None,
        # Regular user and supervisor viewing a team member
        'hours_trend': round(hours_trend, 2),
        'jobs_trend': round(jobs_trend, 2),
        'avg_daily_hours': round(avg_daily_hours, 2),
        'daily_hours_trend': round(daily_hours_trend, 2),
        'total_jobs': total_jobs,
        'mileage_efficiency': round(mileage_efficiency, 2),
        'total_mileage': round(total_mileage, 2),
    }

    logger.debug("Context data prepared for template.")

    return render(request, 'timesheets/dashboard.html', context)



@login_required
def job_details_create_or_edit(request, pk=None):
    if pk:
        job = get_object_or_404(JobDetails, pk=pk)
    else:
        job = None

    if request.method == 'POST':
        form = JobDetailsForm(request.POST, instance=job)
        if form.is_valid():
            new_job = form.save()
            messages.success(request, 'Job details saved successfully.')
            if pk:
                return redirect('job_details_edit', pk=new_job.pk)  # Redirect to edit the same job
            else:
                return redirect('job_details_create')  # Redirect to the create page
    else:
        form = JobDetailsForm(instance=job)
    
    jobs = JobDetails.objects.all().order_by('-job_number')
    context = {
        'view_title': 'Create Job details',
        'form': form,
        'jobs': jobs,
        'job': job
    }
    return render(request, 'timesheets/job_details_form.html', context)

@login_required
def job_details_delete(request, pk):
    job = get_object_or_404(JobDetails, pk=pk)
    job.delete()
    messages.success(request, 'Job details deleted successfully.')
    return redirect('job_details_create')  # Redirect back to the job create page after deletion

@login_required
def get_job_details(request, job_id):
    try:
        job_detail = JobDetails.objects.get(pk=job_id)
        return JsonResponse({
            'success': True,
            'distance': float(job_detail.distance_office),
            'travel_time': str(job_detail.time_office)
        })
    except JobDetails.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Job not found'})
    
    
@login_required
def create_and_list_laborcode(request):
    if request.method == 'POST':
        form = LaborCodeForm(request.POST)
        if form.is_valid():
            # Automatically generate the next laborcode
            max_code = LaborCode.objects.aggregate(Max('laborcode'))['laborcode__max']
            if max_code is not None:
                next_code = max_code + 1
            else:
                next_code = 1  # Start from 1 if no labor codes exist

            # Save the new labor code with the incremented value
            new_laborcode = form.save(commit=False)
            new_laborcode.laborcode = next_code  # Assign the next laborcode (integer)
            new_laborcode.save()

            return redirect('create_and_list_laborcode')
    else:
        form = LaborCodeForm()

    # Get all labor codes for listing
    laborcodes = LaborCode.objects.all()

    context = {
        'view_title': 'Labor Codes',
        'form': form,
        'laborcodes': laborcodes
    }
    return render(request, 'timesheets/create_and_list_laborcode.html', context)
    
    
# get_job_number view
def get_job_number(request, job_id):
    try:
        job_detail = JobDetails.objects.get(pk=job_id)
        return JsonResponse({'success': True, 'job_number': job_detail.job_number})
    except JobDetails.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Job not found'})


def get_labor_code(request, description_id):
    try:
        labor_code = LaborCode.objects.get(id=description_id)
        return JsonResponse({'success': True, 'labor_code': labor_code.laborcode})
    except LaborCode.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Labor code description not found'})
    
# Add to views.py

from django.utils import timezone
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import PermissionDenied

@login_required
def submit_for_approval(request, pk):
    """Submit a time entry for supervisor approval"""
    time_entry = get_object_or_404(TimeEntry, pk=pk)
    
    # Check if user owns this time entry
    if time_entry.user != request.user:
        raise PermissionDenied
        
    # Check if time entry can be submitted
    if not time_entry.can_submit_for_approval:
        messages.error(request, 'This time entry cannot be submitted for approval.')
        return redirect('time_entry_detail', pk=pk)
    
    if request.method == 'POST':
        form = TimeEntryApprovalForm(request.POST)
        if form.is_valid():
            approval = form.save(commit=False)
            approval.time_entry = time_entry
            approval.save()
            
            messages.success(request, 'Time entry submitted for approval.')
            return redirect('time_entry_detail', pk=pk)
    else:
        form = TimeEntryApprovalForm()
    
    context = {
        'view_title': 'Submit for Approval',
        'form': form,
        'time_entry': time_entry
    }
    return render(request, 'timesheets/submit_for_approval.html', context)

@login_required
@permission_required('timesheets.can_approve_timesheet', raise_exception=True)
def review_time_entry(request, pk):
    """Handle time entry review process"""
    time_entry = get_object_or_404(TimeEntry, pk=pk)
    approval = time_entry.approval
    
    if not approval:
        messages.error(request, "This time entry hasn't been submitted for approval.")
        return redirect('time_entry_detail', pk=pk)
    
    # Check if user can approve this time entry
    if not approval.can_approve(request.user):
        messages.error(request, "You don't have permission to review this time entry.")
        return redirect('pending_approvals')
    
    if request.method == 'POST':
        form = TimeEntryReviewForm(request.POST)
        if form.is_valid():
            review_action = form.cleaned_data['review_action']
            comments = form.cleaned_data['comments']
            
            try:
                with transaction.atomic():
                    if approval.status == TimeEntryApproval.PENDING_FIRST:
                        if review_action == 'approve':
                            approval.status = TimeEntryApproval.PENDING_SECOND
                            approval.first_reviewed_by = request.user
                            approval.first_reviewed_at = timezone.now()
                            approval.first_reviewer_comments = comments
                            approval.create_notifications('first_approve', reviewer=request.user, comments=comments)
                            messages.success(request, "First approval completed. Time entry sent to supervisor for final approval.")
                        else:
                            approval.status = TimeEntryApproval.REJECTED
                            approval.first_reviewed_by = request.user
                            approval.first_reviewed_at = timezone.now()
                            approval.first_reviewer_comments = comments
                            approval.create_notifications('reject', reviewer=request.user, comments=comments)
                            messages.warning(request, "Time entry rejected.")
                    
                    elif approval.status == TimeEntryApproval.PENDING_SECOND:
                        if review_action == 'approve':
                            approval.status = TimeEntryApproval.APPROVED
                            approval.second_reviewed_by = request.user
                            approval.second_reviewed_at = timezone.now()
                            approval.second_reviewer_comments = comments
                            approval.create_notifications('final_approve', reviewer=request.user, comments=comments)
                            messages.success(request, "Time entry fully approved.")
                        else:
                            approval.status = TimeEntryApproval.REJECTED
                            approval.second_reviewed_by = request.user
                            approval.second_reviewed_at = timezone.now()
                            approval.second_reviewer_comments = comments
                            approval.create_notifications('reject', reviewer=request.user, comments=comments)
                            messages.warning(request, "Time entry rejected.")
                    
                    approval.save()
                    return redirect('pending_approvals')
                    
            except Exception as e:
                messages.error(request, f"Error processing approval: {str(e)}")
                logger.error(f"Error processing approval: {str(e)}")
    else:
        form = TimeEntryReviewForm()
    
    context = {
        'time_entry': time_entry,
        'approval': approval,
        'form': form,
        'view_title': 'Review Time Entry',
        'is_first_approval': approval.status == TimeEntryApproval.PENDING_FIRST,
        'is_second_approval': approval.status == TimeEntryApproval.PENDING_SECOND,
        'is_supervisor': request.user.role == 'Supervisor' if hasattr(request.user, 'role') else False,
        'is_superuser': request.user.is_superuser,
    }
    
    return render(request, 'timesheets/review_time_entry.html', context)


@login_required
def pending_approvals(request):
    """View for managing pending time entry approvals"""
    
    # Check if user has permission to view approvals
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'Supervisor')):
        messages.error(request, "You don't have permission to view this page.")
        return redirect('dashboard')

    # Initialize context
    context = {
        'view_title': 'Pending Time Entry Approvals',
        'is_supervisor': request.user.role == 'Supervisor' if hasattr(request.user, 'role') else False,
        'is_superuser': request.user.is_superuser,
        'pending_approvals': []  # Initialize empty list
    }

    try:
        # Get pending approvals based on user role
        if request.user.is_superuser:
            # Superuser (Nida) sees entries pending first approval
            context['pending_approvals'] = TimeEntryApproval.objects.filter(
                status=TimeEntryApproval.PENDING_FIRST
            ).select_related(
                'time_entry',
                'time_entry__user',
                'first_reviewed_by',
                'second_reviewed_by'
            ).order_by('-submitted_at')
        
        elif request.user.role == 'Supervisor':
            # Supervisors see entries pending second approval for their team
            context['pending_approvals'] = TimeEntryApproval.objects.filter(
                status=TimeEntryApproval.PENDING_SECOND,
                time_entry__user__supervisor=request.user,
                first_reviewed_by__isnull=False  # Ensure first approval is done
            ).select_related(
                'time_entry',
                'time_entry__user',
                'first_reviewed_by',
                'second_reviewed_by'
            ).order_by('-submitted_at')

    except Exception as e:
        messages.error(request, f"An error occurred while fetching approvals: {str(e)}")
        context['pending_approvals'] = []

    # Always return a response
    return render(request, 'timesheets/pending_approvals.html', context)

@login_required
def approval_history(request):
    """View approval history"""
    # Handle superuser case first
    if request.user.is_superuser:
        # Superusers can see all approvals
        approvals = TimeEntryApproval.objects.all().exclude(
            status='pending'
        ).select_related(
            'time_entry',
            'time_entry__user',
            'first_reviewed_by',
            'second_reviewed_by'
        ).order_by('-submitted_at')
    elif hasattr(request.user, 'role') and request.user.role == 'Supervisor':
        # Get all approvals for supervisees
        approvals = TimeEntryApproval.objects.filter(
            time_entry__user__supervisor=request.user
        ).exclude(
            status='pending'
        ).select_related(
            'time_entry',
            'time_entry__user',
            'first_reviewed_by',
            'second_reviewed_by'
        ).order_by('-submitted_at')
    else:
        # Get user's own approval history
        approvals = TimeEntryApproval.objects.filter(
            time_entry__user=request.user
        ).exclude(
            status='pending'
        ).select_related(
            'time_entry',
            'first_reviewed_by',
            'second_reviewed_by'
        ).order_by('-submitted_at')
    
    context = {
        'view_title': 'Approval History',
        'approvals': approvals
    }
    return render(request, 'timesheets/approval_history.html', context)

from .models import ApprovalNotification

@login_required
def mark_notification_read(request, notification_id):
    """Mark a single notification as read"""
    notification = get_object_or_404(ApprovalNotification, id=notification_id, recipient=request.user)
    notification.mark_as_read()
    return JsonResponse({'status': 'success'})

@login_required
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    ApprovalNotification.objects.filter(recipient=request.user, read=False).update(read=True)
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

@login_required
def all_notifications(request):
    notifications = ApprovalNotification.objects.filter(
        recipient=request.user
    ).select_related('time_entry').order_by('-created_at')
    
    # Add filtering options
    filter_type = request.GET.get('type', 'all')
    if filter_type == 'unread':
        notifications = notifications.filter(read=False)
    
    # Add search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        notifications = notifications.filter(message__icontains=search_query)
    
    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'view_title': 'All Notifications',
        'notifications': page_obj,
        'unread_count': notifications.filter(read=False).count(),
        'total_count': notifications.count(),
        'filter_type': filter_type,
        'search_query': search_query
    }
    return render(request, 'timesheets/all_notifications.html', context)

# Add this to your context processor or middleware
def notification_context(request):
    """Add notification counts to global template context"""
    if request.user.is_authenticated:  # Remove supervisor role check
        unread_notifications = ApprovalNotification.objects.filter(
            recipient=request.user,
            read=False
        ).count()
        
        # Only show pending approvals count for supervisors
        pending_approvals = 0
        if hasattr(request.user, 'role') and request.user.role == 'Supervisor':
            pending_approvals = TimeEntryApproval.objects.filter(
                time_entry__user__supervisor=request.user,
                status='pending'
            ).count()
        
        recent_notifications = ApprovalNotification.objects.filter(
            recipient=request.user
        ).select_related('time_entry').order_by('-created_at')[:5]
        
        return {
            'unread_notifications_count': unread_notifications,
            'pending_approvals_count': pending_approvals,
            'notifications': recent_notifications
        }
    return {}


from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator

@login_required
@require_POST
def mark_notification_read(request, notification_id):
    try:
        notification = ApprovalNotification.objects.get(id=notification_id, recipient=request.user)
        notification.mark_as_read()
        return JsonResponse({'status': 'success'})
    except ApprovalNotification.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Notification not found'}, status=404)

@login_required
@require_POST
def mark_all_notifications_read(request):
    ApprovalNotification.objects.filter(recipient=request.user, read=False).update(read=True)
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

@login_required
def all_notifications(request):
    notifications = ApprovalNotification.objects.filter(recipient=request.user).order_by('-created_at')
    paginator = Paginator(notifications, 20)  # Show 20 notifications per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'view_title': 'All Notifications',
        'notifications': page_obj,
        'unread_count': notifications.filter(read=False).count()
    }
    return render(request, 'timesheets/all_notifications.html', context)


