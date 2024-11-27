# Python standard library imports
from datetime import datetime, timedelta
import decimal
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
from django.db import IntegrityError, transaction, OperationalError, connection  # Changed this line
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
from .decorators import regular_user_required

from .decorators import (
    regular_user_required, 
    supervisor_required, 
    superuser_required,
    supervisor_or_superuser_required
)

# Add at the top with other imports
from contextlib import contextmanager

@contextmanager
def handle_connection():
    """Context manager to handle database connections properly"""
    try:
        yield
    except OperationalError as e:  # Now uses the correct import
        logger.error(f"Database connection error: {e}")
        connection.close()
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise
    finally:
        connection.close()

def cache_per_user(timeout=300):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Create a cache key based on the user and request parameters
            cache_key = f"timesheet_list_{request.user.id}_{request.GET.urlencode()}"
            response = cache.get(cache_key)
            
            if response is None:
                response = view_func(request, *args, *kwargs)
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
    # Initialize role flags
    is_superuser = request.user.is_superuser
    is_supervisor = hasattr(request.user, 'role') and request.user.role == 'Supervisor'

    # Get time entry with select_related and prefetch_related for optimization
    time_entry = get_object_or_404(
        TimeEntry.objects.select_related(
            'user',
            'approval'
        ).prefetch_related(
            'jobs',
            'jobs__labor_code',
            'approval__history'
        ),
        pk=pk
    )

    # Check if user has permission to view this time entry
    if not (is_superuser or 
            (is_supervisor and time_entry.user.supervisor == request.user) or 
            time_entry.user == request.user):
        messages.error(request, "You don't have permission to view this time entry.")
        return redirect('timesheets:time_entry_list')

    # Get the approval history if it exists
    approval_history = None
    if hasattr(time_entry, 'approval'):
        approval_history = time_entry.approval.history.all().order_by('-reviewed_at')

    # Build context
    context = {
        'view_title': f'Timesheet Entry - {time_entry.date}',
        'time_entry': time_entry,
        'approval_history': approval_history,
        'is_superuser': is_superuser,
        'is_supervisor': is_supervisor,
        'can_edit': (
            time_entry.user == request.user and 
            not time_entry.is_approved
        ),
        'can_approve': (
            (is_supervisor or is_superuser) and 
            time_entry.is_pending_approval
        ),
        'can_submit': (
            time_entry.user == request.user and 
            time_entry.can_submit_for_approval
        )
    }

    # Get next and previous entries
    if is_superuser:
        next_entry = TimeEntry.objects.filter(id__gt=pk).order_by('id').first()
        prev_entry = TimeEntry.objects.filter(id__lt=pk).order_by('-id').first()
    elif is_supervisor:
        next_entry = TimeEntry.objects.filter(
            user__supervisor=request.user,
            id__gt=pk
        ).order_by('id').first()
        prev_entry = TimeEntry.objects.filter(
            user__supervisor=request.user,
            id__lt=pk
        ).order_by('-id').first()
    else:
        next_entry = TimeEntry.objects.filter(
            user=request.user,
            id__gt=pk
        ).order_by('id').first()
        prev_entry = TimeEntry.objects.filter(
            user=request.user,
            id__lt=pk
        ).order_by('-id').first()

    # Add to existing context
    context.update({
        'next_entry': next_entry,
        'prev_entry': prev_entry,
    })

    return render(request, 'timesheets/time_entry_detail.html', context)

@login_required
def time_entry_list(request):
    with handle_connection():
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
@regular_user_required
def time_entry_create(request):
    with handle_connection():
        JobFormSet = formset_factory(JobForm, extra=1, can_delete=True)
        
        if request.method == 'POST':
            form = TimeEntryForm(request.POST, request.FILES)  # Add request.FILES here
            formset = JobFormSet(request.POST, prefix='jobs')  # Add prefix to match template
            
            print("POST data:", request.POST)
            print(f"Form is valid: {form.is_valid()}")
            print(f"Formset is valid: {formset.is_valid()}")
            
            logger.debug(f"POST data: {request.POST}")
            logger.debug(f"Form is valid: {form.is_valid()}")
            logger.debug(f"Formset is valid: {formset.is_valid()}")
            
            if form.is_valid() and formset.is_valid():
                try:
                    with transaction.atomic():
                        time_entry = form.save(commit=False)
                        time_entry.user = request.user
                        
                        # Handle file upload
                        if 'attachment' in request.FILES:
                            time_entry.attachment = request.FILES['attachment']
                            time_entry.attachment_name = request.FILES['attachment'].name
                            
                        time_entry.save()
                        
                        logger.debug(f"Number of forms in formset: {len(formset)}")
                        
                        for job_form in formset:
                            logger.debug(f"Job form cleaned data: {job_form.cleaned_data}")
                            if job_form.cleaned_data and not job_form.cleaned_data.get('DELETE', False):
                                job = job_form.save(commit=False)
                                job.time_entry = time_entry
                                job.save()
                                logger.debug(f"Saved job: {job}")
                        
                        if not time_entry.jobs.exists():
                            raise ValueError("At least one job must be present.")
                        
                        messages.success(request, "Time entry created successfully.")
                        return redirect('timesheets:time_entry_detail', pk=time_entry.pk)
                except Exception as e:
                    logger.error(f"Error creating time entry: {str(e)}")
                    messages.error(request, f"Error creating time entry: {str(e)}")
            else:
                logger.error(f"Form errors: {form.errors}")
                logger.error(f"Formset errors: {formset.errors}")
                messages.error(request, "Please correct the errors below.")
        else:
            form = TimeEntryForm()
            formset = JobFormSet(prefix='jobs')  # Add prefix to match template
            
        context = {
            'view_title': 'Create Time Entry',
            'form': form,
            'job_formset': formset
        }
        return render(request, 'timesheets/time_entry_form.html', context)
    
@login_required
@regular_user_required
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
        form = TimeEntryForm(request.POST, request.FILES, instance=time_entry)  # Add request.FILES here
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
                return redirect('timesheets:time_entry_detail', pk=time_entry.pk)
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
@regular_user_required
def time_entry_delete(request, pk):
    time_entry = get_object_or_404(TimeEntry, pk=pk)
    if request.method == 'POST':
        time_entry.delete()
        return redirect('timesheets:time_entry_list')
    
    return render(request, 'timesheets/time_entry_confirm_delete.html', {'time_entry': time_entry})

@login_required
@supervisor_or_superuser_required
def supervisor_dashboard(request):
    """
    View for supervisor dashboard showing team members, pending approvals, and recent activity
    """
    # Allow both superusers and supervisors to access
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'Supervisor')):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('timesheets:dashboard')

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
@supervisor_or_superuser_required
def team_timesheets(request):
    """View for supervisors and superusers to see team timesheets"""
    # Allow both superusers and supervisors to access
    if not (request.user.is_superuser or (hasattr(request.user, 'role') or request.user.role == 'Supervisor')):
        messages.error(request, "You don't have permission to view this page.")
        return redirect('timesheets:dashboard')

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

from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import logging
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from .models import TimeEntry, TimeEntryApproval

logger = logging.getLogger(__name__)
User = get_user_model()

@login_required
def user_summary_report(request):
    # Initialize context at the beginning
    context = {
        'view_title': 'Summary Report',
        'is_superuser': request.user.is_superuser,
        'is_supervisor': hasattr(request.user, 'role') and request.user.role == 'Supervisor',
    }
    
    # Initialize context variables for user permissions
    is_superuser = request.user.is_superuser
    is_supervisor = hasattr(request.user, 'role') and request.user.role == 'Supervisor'
    
    # Determine the available users based on permissions
    if is_superuser:
        all_users = User.objects.all().order_by('first_name', 'last_name')
    elif is_supervisor:
        all_users = User.objects.filter(supervisor=request.user).order_by('first_name', 'last_name')
    else:
        all_users = None

    # Get the selected user with proper validation
    selected_user_id = request.GET.get('user')
    if selected_user_id:
        if is_superuser:
            selected_user = User.objects.filter(id=selected_user_id).first()
        elif is_supervisor:
            selected_user = User.objects.filter(
                id=selected_user_id,
                supervisor=request.user
            ).first()
        else:
            selected_user = None
    else:
        selected_user = request.user

    # Default to current user if no valid selection
    if not selected_user:
        selected_user = request.user

    # Get and validate date range
    try:
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if start_date and end_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            # Get current week's Monday and Sunday
            today = timezone.now().date()
            start_date = today - timedelta(days=today.weekday())  # Monday
            end_date = start_date + timedelta(days=6)  # Sunday

        # Validate date range isn't too large
        if (end_date - start_date).days > 366:  # Max one year
            messages.warning(request, "Date range limited to one year maximum.")
            end_date = start_date + timedelta(days=365)

    except ValueError as e:
        logger.error(f"Date parsing error: {str(e)}")
        # Get current week's Monday and Sunday as fallback
        today = timezone.now().date()
        start_date = today - timedelta(days=today.weekday())  # Monday
        end_date = start_date + timedelta(days=6)  # Sunday

    # Generate date range
    date_range = []
    current_date = start_date
    while current_date <= end_date:
        date_range.append(current_date)
        current_date += timedelta(days=1)

    # Initialize data structures with Decimal for precise calculations
    weekly_hours = {}
    daily_totals = {date: Decimal('0.00') for date in date_range}
    daily_rt = {date: Decimal('0.00') for date in date_range}
    daily_ot = {date: Decimal('0.00') for date in date_range}
    
    total_rt_hours = Decimal('0.00')
    total_ot_hours = Decimal('0.00')
    
    # Get time entries with optimized queries
    time_entries = TimeEntry.objects.filter(
        user=selected_user,
        date__range=[start_date, end_date]
    ).prefetch_related(
        'jobs',
        'jobs__labor_code',
        'approval'
    ).select_related('user')

    # Process time entries
    for entry in time_entries:
        entry_date = entry.date
        
        try:
            if entry.hours_to_be_paid:
                # Convert the hours value to Decimal
                entry_hours = Decimal(str(entry.hours_to_be_paid))
                
                # Calculate RT and OT for this day
                rt_hours = min(Decimal('8.00'), entry_hours)
                ot_hours = max(Decimal('0.00'), entry_hours - Decimal('8.00'))
                
                # Update daily totals
                daily_rt[entry_date] += rt_hours
                daily_ot[entry_date] += ot_hours
                
                # Update running totals
                total_rt_hours += rt_hours
                total_ot_hours += ot_hours

                # Process jobs for this entry
                jobs_for_entry = entry.jobs.all()
                job_count = len(jobs_for_entry)
                
                if job_count > 0:
                    # Calculate hours per job
                    hours_per_job = (entry_hours / Decimal(str(job_count))).quantize(
                        Decimal('0.01'),
                        rounding=ROUND_HALF_UP
                    )
                    
                    # Distribute hours to labor codes
                    for job in jobs_for_entry:
                        labor_code = job.labor_code.laborcode
                        
                        # Initialize labor code data if needed
                        if labor_code not in weekly_hours:
                            weekly_hours[labor_code] = {
                                "description": job.job_description,
                                "labor_code_description": job.labor_code.labor_code_description,
                                "job": job.job_number,
                                "hours": {date: Decimal('0.00') for date in date_range},
                                "total": Decimal('0.00')
                            }
                        
                        # Update hours for this labor code
                        weekly_hours[labor_code]["hours"][entry_date] += hours_per_job
                        weekly_hours[labor_code]["total"] += hours_per_job

        except (ValueError, TypeError, decimal.InvalidOperation) as e:
            logger.error(f"Error processing entry {entry.id}: {str(e)}")
            continue

    # Round all daily totals
    for date in date_range:
        daily_rt[date] = daily_rt[date].quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        daily_ot[date] = daily_ot[date].quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    # Round final totals
    total_rt_hours = total_rt_hours.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    total_ot_hours = total_ot_hours.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    # Calculate weekly totals
    total_hours = total_rt_hours + total_ot_hours
    
    # Calculate weekly regular and overtime hours
    total_regular_hours = min(total_hours, Decimal('40.00'))
    total_overtime_hours = max(Decimal('0.00'), total_hours - Decimal('40.00'))
    total_double_time_hours = Decimal('0.00')  # Implement double time logic if needed

    # Round all totals
    total_regular_hours = total_regular_hours.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    total_overtime_hours = total_overtime_hours.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    total_double_time_hours = total_double_time_hours.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    grand_total_hours = (total_regular_hours + total_overtime_hours + total_double_time_hours).quantize(
        Decimal('0.01'),
        rounding=ROUND_HALF_UP
    )

    # Calculate miles and vehicle allowance
    total_miles_to_be_paid = sum(entry.miles_to_be_paid or 0 for entry in time_entries)
    vehicle_allowance = total_miles_to_be_paid * Decimal('0.55')  # Assuming $0.55 per mile

    # Get attachments
    attachments = []
    for entry in time_entries:
        if entry.attachment and entry.attachment_name:
            attachments.append({
                'date': entry.date,
                'name': entry.attachment_name,
                'url': entry.get_attachment_url(),
                'entry_id': entry.id
            })

    # Add new data to context
    context.update({
        'total_miles_to_be_paid': total_miles_to_be_paid,
        'vehicle_allowance': vehicle_allowance,
        'attachments': attachments,
    })

    # Consolidate all context updates into a single update
    context.update({
        'all_users': all_users,
        'selected_user': selected_user,
        'start_date': start_date,
        'end_date': end_date,
        'date_range': date_range,
        'weekly_hours': weekly_hours,
        'daily_rt': daily_rt,
        'daily_ot': daily_ot,
        'total_rt_hours': total_rt_hours,
        'total_ot_hours': total_ot_hours,
        'total_regular_hours': total_regular_hours,
        'total_overtime_hours': total_overtime_hours,
        'total_double_time_hours': total_double_time_hours,
        'grand_total_hours': grand_total_hours,
        'is_superuser': is_superuser,
        'is_supervisor': is_supervisor,
    })

    return render(request, 'timesheets/summary_report.html', context)

@login_required
@regular_user_required
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
            return redirect('timesheets:time_entry_detail', pk=time_entry.pk)
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
    with handle_connection():
        # Initialize permission flags
        is_superuser = request.user.is_superuser
        is_supervisor = hasattr(request.user, 'role') and request.user.role == 'Supervisor'
        
        # Get and validate selected user
        selected_user_id = request.GET.get('user_id')
        if selected_user_id:
            try:
                selected_user_id = int(selected_user_id)
            except ValueError:
                selected_user_id = None
        
        # Get date range from request or default to current month
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if not start_date or not end_date:
            today = timezone.now().date()
            start_date = today.replace(day=1)
            end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        else:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                today = timezone.now().date()
                start_date = today.replace(day=1)
                end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        # Get team members based on role
        if is_superuser:
            team_members = User.objects.all().select_related('supervisor')
            all_users = team_members
        elif is_supervisor:
            team_members = User.objects.filter(supervisor=request.user).select_related('supervisor')
            all_users = team_members
        else:
            team_members = None
            all_users = None

        # Get the selected user
        if selected_user_id:
            if is_superuser:
                selected_user = User.objects.filter(id=selected_user_id).first()
            elif is_supervisor:
                selected_user = User.objects.filter(
                    id=selected_user_id,
                    supervisor=request.user
                ).first()
            else:
                selected_user = request.user
        else:
            selected_user = request.user

        # Calculate team statistics
        if is_superuser or is_supervisor:
            users_to_track = team_members
            
            team_stats = {
                'total_members': team_members.count(),
                'active_members': team_members.filter(is_active=True).count(),
                'pending_approvals': TimeEntryApproval.objects.filter(
                    time_entry__user__in=users_to_track,
                    status__in=['pending_first', 'pending_second']
                ).count(),
                'total_approved': TimeEntryApproval.objects.filter(
                    time_entry__user__in=users_to_track,
                    status='approved'
                ).count(),
                'total_hours': TimeEntry.objects.filter(
                    user__in=users_to_track,
                    date__range=[start_date, end_date]
                ).aggregate(
                    total_hours=Sum('hours_to_be_paid')
                )['total_hours'] or 0
            }

            # Get pending approvals
            if is_superuser:
                pending_approvals = TimeEntryApproval.objects.filter(
                    status__in=['pending_first', 'pending_second']
                )
            else:
                pending_approvals = TimeEntryApproval.objects.filter(
                    time_entry__user__in=team_members,
                    status__in=['pending_first', 'pending_second']
                )
            
            pending_approvals = pending_approvals.select_related(
                'time_entry',
                'time_entry__user'
            ).order_by('-submitted_at')
        else:
            team_stats = None
            pending_approvals = None

        # Calculate individual statistics for the selected user
        user_entries = TimeEntry.objects.filter(
            user=selected_user,
            date__range=[start_date, end_date]
        )

        total_hours = user_entries.aggregate(Sum('hours_to_be_paid'))['hours_to_be_paid__sum'] or 0
        total_jobs = Job.objects.filter(time_entry__in=user_entries).count()
        avg_daily_hours = user_entries.aggregate(Avg('hours_to_be_paid'))['hours_to_be_paid__avg'] or 0
        total_mileage = user_entries.aggregate(Sum('miles_to_be_paid'))['miles_to_be_paid__sum'] or 0

        # Get recent entries
        recent_entries = user_entries.prefetch_related('jobs').order_by('-date')[:5]

        # Calculate trends
        previous_start_date = start_date - timedelta(days=(end_date - start_date).days + 1)
        previous_entries = TimeEntry.objects.filter(
            user=selected_user,
            date__range=[previous_start_date, start_date - timedelta(days=1)]
        )

        previous_hours = previous_entries.aggregate(Sum('hours_to_be_paid'))['hours_to_be_paid__sum'] or 1
        previous_jobs = Job.objects.filter(time_entry__in=previous_entries).count() or 1
        previous_daily_hours = previous_entries.aggregate(Avg('hours_to_be_paid'))['hours_to_be_paid__avg'] or 1

        hours_trend = ((total_hours - previous_hours) / previous_hours * 100) if previous_hours != 0 else 0
        jobs_trend = ((total_jobs - previous_jobs) / previous_jobs * 100) if previous_jobs != 0 else 0
        daily_hours_trend = ((avg_daily_hours - previous_daily_hours) / previous_daily_hours * 100) if previous_daily_hours != 0 else 0

        # Rest of your context data...
        # [Previous context building code remains the same]

        # Prepare data for charts
        labor_code_data = []
        daily_hours_data = []

        # Get time entries for the selected user and date range
        user_entries = TimeEntry.objects.filter(
            user=selected_user,
            date__range=[start_date, end_date]
        ).prefetch_related(
            'jobs',
            'jobs__labor_code'
        )

        # Calculate Labor Code Distribution
        labor_code_hours = {}
        for entry in user_entries:
            for job in entry.jobs.all():
                labor_code = job.labor_code
                if labor_code.laborcode not in labor_code_hours:
                    labor_code_hours[labor_code.laborcode] = {
                        'labor_code__laborcode': labor_code.laborcode,
                        'labor_code__labor_code_description': labor_code.labor_code_description,
                        'count': 0
                    }
                # Add the hours for this entry to the labor code total
                if entry.hours_to_be_paid:
                    labor_code_hours[labor_code.laborcode]['count'] += float(entry.hours_to_be_paid)

        # Convert dictionary to list for the template
        labor_code_data = list(labor_code_hours.values())

        # Calculate Daily Hours
        daily_hours = {}
        current_date = start_date
        while current_date <= end_date:
            daily_hours[current_date] = {
                'date': current_date.strftime('%Y-%m-%d'),
                'hours': 0
            }
            current_date += timedelta(days=1)

        for entry in user_entries:
            if entry.date in daily_hours and entry.hours_to_be_paid:
                daily_hours[entry.date]['hours'] += float(entry.hours_to_be_paid)

        # Convert dictionary to list for the template
        daily_hours_data = list(daily_hours.values())

        # Create context dictionary at the beginning
        context = {
            'view_title': 'Dashboard',
            'selected_user': selected_user,
            'total_hours': 0,
            'total_jobs': 0,
            'avg_daily_hours': 0,
            'total_mileage': 0,
            'hours_trend': 0,
            'jobs_trend': 0,
            'daily_hours_trend': 0,
            'start_date': start_date,
            'end_date': end_date,
            'all_users': all_users,
            'team_members': team_members,
            'team_stats': team_stats,
            'pending_approvals': pending_approvals,
            'is_admin': is_superuser,
            'is_supervisor': is_supervisor,
        }

        # Update context with calculated values
        context.update({
            'total_hours': round(total_hours, 2),
            'total_jobs': total_jobs,
            'avg_daily_hours': round(avg_daily_hours, 2),
            'total_mileage': round(total_mileage, 2),
            'hours_trend': round(hours_trend, 2),
            'jobs_trend': round(jobs_trend, 2),
            'daily_hours_trend': round(daily_hours_trend, 2),
            'recent_entries': recent_entries,
        })

        # Update context with chart data
        context.update({
            'labor_code_data': json.dumps(labor_code_data, cls=DecimalEncoder),
            'daily_hours_data': json.dumps(daily_hours_data, cls=DecimalEncoder),
        })

        # Debug logging
        logger.debug(f"Labor code data: {labor_code_data}")
        logger.debug(f"Daily hours data: {daily_hours_data}")

        return render(request, 'timesheets/dashboard.html', context)



@login_required
@supervisor_or_superuser_required
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
                return redirect('timesheets:job_details_edit', pk=new_job.pk)  # Redirect to edit the same job
            else:
                return redirect('timesheets:job_details_create')  # Redirect to the create page
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
@supervisor_or_superuser_required
def job_details_delete(request, pk):
    job = get_object_or_404(JobDetails, pk=pk)
    job.delete()
    messages.success(request, 'Job details deleted successfully.')
    return redirect('timesheets:job_details_create')  # Redirect back to the job create page after deletion

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
@supervisor_or_superuser_required
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

            return redirect('timesheets:create_and_list_laborcode')
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
from django.views.decorators.http import require_POST

@login_required
@regular_user_required
def submit_for_approval(request, pk):
    """Submit a time entry for supervisor approval"""
    time_entry = get_object_or_404(TimeEntry, pk=pk)
    
    # Check if user owns this time entry
    if time_entry.user != request.user:
        raise PermissionDenied
        
    # Check if time entry can be submitted
    if not time_entry.can_submit_for_approval:
        messages.error(request, 'This time entry cannot be submitted for approval.')
        return redirect('timesheets:time_entry_detail', pk=pk)
    
    if request.method == 'POST':
        form = TimeEntryApprovalForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Try to get existing approval or create new one
                    approval, created = TimeEntryApproval.objects.get_or_create(
                        time_entry=time_entry,
                        defaults={
                            'status': TimeEntryApproval.PENDING_FIRST,
                            'submitted_at': timezone.now()
                        }
                    )
                    
                    if not created:
                        # Reset the approval state for resubmission
                        approval.status = TimeEntryApproval.PENDING_FIRST
                        approval.submitted_at = timezone.now()
                        approval.first_reviewed_by = None
                        approval.first_reviewed_at = None
                        approval.first_reviewer_comments = ''
                        approval.second_reviewed_by = None
                        approval.second_reviewed_at = None
                        approval.second_reviewer_comments = ''
                        
                    # Update any additional fields from the form
                    form_data = form.cleaned_data
                    for field, value in form_data.items():
                        setattr(approval, field, value)
                        
                    approval.save()
                    
                    messages.success(request, 'Time entry submitted for approval.')
                    return redirect('timesheets:time_entry_detail', pk=pk)
                    
            except Exception as e:
                messages.error(request, f'Error submitting for approval: {str(e)}')
                return redirect('timesheets:time_entry_detail', pk=pk)
    else:
        form = TimeEntryApprovalForm()
    
    context = {
        'view_title': 'Submit for Approval',
        'form': form,
        'time_entry': time_entry,
        'is_resubmission': hasattr(time_entry, 'approval')
    }
    return render(request, 'timesheets/submit_for_approval.html', context)

@login_required
@supervisor_or_superuser_required
def review_time_entry(request, pk):
    """Handle time entry review process"""
    time_entry = get_object_or_404(TimeEntry, pk=pk)
    approval = time_entry.approval
    
    if not approval:
        messages.error(request, "This time entry hasn't been submitted for approval.")
        return redirect('timesheets:time_entry_detail', pk=pk)
    
    if not approval.can_approve(request.user):
        messages.error(request, "You don't have permission to review this time entry.")
        return redirect('timesheets:pending_approvals')
    
    if request.method == 'POST':
        form = TimeEntryReviewForm(request.POST)
        if form.is_valid():
            review_action = form.cleaned_data['review_action']
            comments = form.cleaned_data['comments']
            
            try:
                with transaction.atomic():
                    current_status = approval.status
                    new_status = None

                    # Handle transitions based on current status and review action
                    if current_status in [TimeEntryApproval.PENDING_FIRST, TimeEntryApproval.REJECTED]:
                        if review_action == 'approve':
                            new_status = TimeEntryApproval.PENDING_SECOND
                            approval.first_reviewed_by = request.user
                            approval.first_reviewed_at = timezone.now()
                            approval.first_reviewer_comments = comments
                            approval.add_to_history(
                                new_status,
                                request.user,
                                comments,
                                is_first=True
                            )
                            approval.create_notifications('first_approve', reviewer=request.user, comments=comments)
                            messages.success(request, "First approval completed. Time entry sent to supervisor for final approval.")
                        else:  # reject
                            new_status = TimeEntryApproval.REJECTED
                            approval.first_reviewed_by = request.user
                            approval.first_reviewed_at = timezone.now()
                            approval.first_reviewer_comments = comments
                            approval.add_to_history(
                                new_status,
                                request.user,
                                comments,
                                is_first=True
                            )
                            approval.create_notifications('reject', reviewer=request.user, comments=comments)
                            messages.warning(request, "Time entry rejected.")
                    
                    elif current_status == TimeEntryApproval.PENDING_SECOND:
                        if review_action == 'approve':
                            new_status = TimeEntryApproval.APPROVED
                            approval.second_reviewed_by = request.user
                            approval.second_reviewed_at = timezone.now()
                            approval.second_reviewer_comments = comments
                            approval.add_to_history(
                                new_status,
                                request.user,
                                comments,
                                is_second=True
                            )
                            approval.create_notifications('final_approve', reviewer=request.user, comments=comments)
                            messages.success(request, "Time entry fully approved.")
                        else:  # reject
                            new_status = TimeEntryApproval.REJECTED
                            approval.second_reviewed_by = request.user
                            approval.second_reviewed_at = timezone.now()
                            approval.second_reviewer_comments = comments
                            approval.add_to_history(
                                new_status,
                                request.user,
                                comments,
                                is_second=True
                            )
                            approval.create_notifications('reject', reviewer=request.user, comments=comments)
                            messages.warning(request, "Time entry rejected.")
                    
                    if new_status is None:
                        raise ValueError(f"Invalid status transition from {current_status}")
                        
                    approval.status = new_status
                    approval.save()
                    
                    return redirect('timesheets:pending_approvals')
                    
            except Exception as e:
                messages.error(request, f"Error processing approval: {str(e)}")
                logger.error(f"Error processing approval: {str(e)}", exc_info=True)
    else:
        form = TimeEntryReviewForm()
    
    context = {
        'time_entry': time_entry,
        'approval': approval,
        'form': form,
        'approval_history': approval.history.all(),
        'view_title': 'Review Time Entry',
        'is_first_approval': approval.status in [TimeEntryApproval.PENDING_FIRST, TimeEntryApproval.REJECTED],
        'is_second_approval': approval.status == TimeEntryApproval.PENDING_SECOND,
        'is_supervisor': request.user.role == 'Supervisor' if hasattr(request.user, 'role') else False,
        'is_superuser': request.user.is_superuser,
    }
    
    return render(request, 'timesheets/review_time_entry.html', context)

@login_required
@supervisor_or_superuser_required
def pending_approvals(request):
    """View for managing pending time entry approvals"""
    
    # Initialize context
    context = {
        'view_title': 'Pending Time Entry Approvals',
        'is_supervisor': hasattr(request.user, 'role') and request.user.role == 'Supervisor',
        'is_superuser': request.user.is_superuser,
        'pending_approvals': []
    }

    if not (request.user.is_superuser or context['is_supervisor']):
        messages.error(request, "You don't have permission to view this page.")
        return redirect('timesheets:dashboard')  # Add namespace here

    try:
        base_queryset = TimeEntryApproval.objects.select_related(
            'time_entry',
            'time_entry__user',
            'first_reviewed_by',
            'second_reviewed_by'
        ).order_by('-submitted_at')

        if request.user.is_superuser:
            # Superusers see all entries pending first approval
            context['pending_approvals'] = base_queryset.filter(
                Q(status=TimeEntryApproval.PENDING_FIRST) |
                Q(status='pending_first')
            )
        else:
            # Supervisors see:
            # 1. Entries pending second approval for their team (after first approval)
            # 2. Entries that have been first-approved and are waiting for their review
            context['pending_approvals'] = base_queryset.filter(
                Q(time_entry__user__supervisor=request.user) &
                (
                    # Include entries pending second approval
                    (Q(status=TimeEntryApproval.PENDING_SECOND) | Q(status='pending_second')) |
                    # Include entries that were just approved by superuser and need supervisor review
                    (
                        Q(first_reviewed_by__isnull=False) & 
                        Q(second_reviewed_by__isnull=True) &
                        (Q(status=TimeEntryApproval.PENDING_SECOND) | Q(status='pending_second'))
                    )
                )
            )

        # Add debug logging
        logger.debug(f"User role: {'Superuser' if request.user.is_superuser else 'Supervisor'}")
        logger.debug(f"Query results count: {context['pending_approvals'].count()}")
        logger.debug(f"Query SQL: {context['pending_approvals'].query}")

    except Exception as e:
        logger.error(f"Error in pending_approvals view: {str(e)}", exc_info=True)
        messages.error(request, f"An error occurred while fetching approvals: {str(e)}")
        context['pending_approvals'] = []

    return render(request, 'timesheets/pending_approvals.html', context)

@login_required
def approval_history(request):
    """View approval history including past rejections"""
    
    # Base queryset with all necessary relations
    base_queryset = TimeEntryApproval.objects.select_related(
        'time_entry',
        'time_entry__user',
        'first_reviewed_by',
        'second_reviewed_by'
    ).order_by('-submitted_at')

    # Filter based on user role
    if request.user.is_superuser:
        # Superusers can see all approvals
        approvals = base_queryset.all()
    elif hasattr(request.user, 'role') and request.user.role == 'Supervisor':
        # Get all approvals for supervisees, including historical ones
        approvals = base_queryset.filter(
            time_entry__user__supervisor=request.user
        )
    else:
        # Get user's own approval history, including past rejections
        approvals = base_queryset.filter(
            time_entry__user=request.user
        )
    
    # Add search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        approvals = approvals.filter(
            Q(time_entry__user__first_name__icontains=search_query) |
            Q(time_entry__user__last_name__icontains=search_query) |
            Q(status__icontains=search_query) |
            Q(first_reviewer_comments__icontains=search_query) |
            Q(second_reviewer_comments__icontains=search_query)
        )

    # Add pagination
    paginator = Paginator(approvals, 20)  # Show 20 entries per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'view_title': 'Approval History',
        'approvals': page_obj,
        'search_query': search_query,
        'is_paginated': page_obj.has_other_pages()
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
    return redirect(request.META.get('HTTP_REFERER', 'timesheets:dashboard'))

@login_required
def all_notifications(request):
    """View for displaying all notifications with filtering and pagination"""
    notifications = ApprovalNotification.objects.filter(
        recipient=request.user
    ).select_related(
        'recipient',
        'time_entry_approval',
        'time_entry_approval__time_entry'
    ).order_by('-created_at')
    
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

@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """Mark a single notification as read"""
    notification = get_object_or_404(ApprovalNotification, id=notification_id, recipient=request.user)
    notification.mark_as_read()
    return JsonResponse({'status': 'success'})

@login_required
@require_POST
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    ApprovalNotification.objects.filter(recipient=request.user, read=False).update(read=True)
    return redirect(request.META.get('HTTP_REFERER', 'timesheets:dashboard'))

@login_required
@require_POST
def clear_all_notifications(request):
    """Delete all notifications for the current user"""
    ApprovalNotification.objects.filter(recipient=request.user).delete()
    messages.success(request, "All notifications have been cleared.")
    return redirect(request.META.get('HTTP_REFERER', 'timesheets:dashboard'))

@login_required
@require_POST
def delete_notification(request, notification_id):
    """Delete a specific notification"""
    notification = get_object_or_404(ApprovalNotification, id=notification_id, recipient=request.user)
    notification.delete()
    messages.success(request, "Notification deleted.")
    return redirect(request.META.get('HTTP_REFERER', 'timesheets:dashboard'))

# Add this to your context processor or middleware if not already present
def notification_context(request):
    """Add notification counts to global template context"""
    if request.user.is_authenticated:
        unread_notifications = ApprovalNotification.objects.filter(
            recipient=request.user,
            read=False
        ).count()
        
        pending_approvals = 0
        if hasattr(request.user, 'role') and request.user.role == 'Supervisor':
            pending_approvals = TimeEntryApproval.objects.filter(
                time_entry__user__supervisor=request.user,
                status='pending'
            ).count()
        
        recent_notifications = ApprovalNotification.objects.filter(
            recipient=request.user
        ).select_related(
            'recipient',
            'time_entry_approval',
            'time_entry_approval__time_entry'
        ).order_by('-created_at')[:5]
        
        return {
            'unread_notifications_count': unread_notifications,
            'pending_approvals_count': pending_approvals,
            'notifications': recent_notifications
        }
    return {}

from django.shortcuts import redirect, get_object_or_404
from .models import ApprovalNotification

@login_required
def notification_link_handler(request, notification_id):
    notification = get_object_or_404(ApprovalNotification, id=notification_id, recipient=request.user)
    
    # Mark the notification as read
    if not notification.read:
        notification.mark_as_read()
    
    # Redirect to the appropriate URL
    return redirect(notification.get_target_url)

@login_required
def clear_visible_notifications(request):
    if request.method == 'POST':
        # First, get the IDs of the recent notifications
        recent_notification_ids = ApprovalNotification.objects.filter(
            recipient=request.user,
            created_at__gte=timezone.now() - timezone.timedelta(days=7)
        ).order_by('-created_at')[:5].values_list('id', flat=True)
        
        # Then, update those notifications using the IDs
        ApprovalNotification.objects.filter(
            id__in=list(recent_notification_ids)
        ).update(read=True)
        
        messages.success(request, 'Notifications cleared from tray.')
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


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
    return redirect(request.META.get('HTTP_REFERER', 'timesheets:dashboard'))

@login_required
def all_notifications(request):
    """View for displaying all notifications with filtering and pagination"""
    notifications = ApprovalNotification.objects.filter(
        recipient=request.user
    ).select_related(
        'time_entry_approval',
        'time_entry_approval__time_entry'
    ).order_by('-created_at')
    
    # Add pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    notifications = paginator.get_page(page_number)

    context = {
        'view_title': 'Notifications',
        'notifications': notifications,
        'unread_notifications_count': ApprovalNotification.objects.filter(
            recipient=request.user,
            read=False
        ).count()
    }
    return render(request, 'timesheets/all_notifications.html', context)

@login_required
def delete_notification(request, notification_id):
    """Delete a specific notification"""
    notification = get_object_or_404(ApprovalNotification, id=notification_id, recipient=request.user)
    notification.delete()
    return redirect(request.META.get('HTTP_REFERER', 'timesheets:all_notifications'))

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
import json

@login_required
@require_http_methods(["POST"])
def batch_delete(request):
    """Handle batch deletion of time entries"""
    try:
        # Parse JSON data with better error handling
        try:
            data = json.loads(request.body)
            entry_ids = data.get('entry_ids', [])
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid JSON data'
            }, status=400)

        if not entry_ids:
            return JsonResponse({
                'status': 'error',
                'message': 'No entries selected'
            }, status=400)

        # Log the incoming request
        logger.debug(f"Batch delete request for entries: {entry_ids}")

        # Get entries that belong to the user and aren't approved
        deletable_entries = TimeEntry.objects.filter(
            id__in=entry_ids,
            user=request.user
        ).exclude(
            Q(approval__status='approved') | 
            Q(approval__status='pending_first') | 
            Q(approval__status='pending_second')
        )

        # Get count before deletion
        count_to_delete = deletable_entries.count()
        
        if count_to_delete == 0:
            return JsonResponse({
                'status': 'error',
                'message': 'No eligible entries found to delete'
            }, status=404)

        # Perform deletion within transaction
        with transaction.atomic():
            # Delete the time entries - cascade will handle related records
            deletion_result = deletable_entries.delete()
            
            # Log the deletion result
            logger.info(f"Deleted {count_to_delete} entries. Deletion result: {deletion_result}")

            return JsonResponse({
                'status': 'success',
                'message': f'Successfully deleted {count_to_delete} entries',
                'deleted_count': count_to_delete,
                'deleted_ids': list(deletable_entries.values_list('id', flat=True))
            })

    except Exception as e:
        logger.error(f"Error in batch deletion: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': 'Server error occurred during deletion'
        }, status=500)