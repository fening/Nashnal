from django.shortcuts import redirect, render, get_object_or_404
from .models import TimeEntry, Job
from .forms import TimeEntryForm, JobForm
from .formsets import JobFormSet
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.db.models import Sum, F, ExpressionWrapper, fields,Count
from django.utils import timezone
from datetime import timedelta
from django.forms import inlineformset_factory, formset_factory
from django.contrib.auth.models import User
import logging
from datetime import datetime, timedelta
import json
from decimal import Decimal

logger = logging.getLogger(__name__)


User = get_user_model()

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

@login_required
def home(request):
    if request.user.is_superuser:
        time_entries = TimeEntry.objects.all()
    else:
        time_entries = TimeEntry.objects.filter(user=request.user)
    return render(request, 'timesheets/home.html',{'time_entries': time_entries})

@login_required
def time_entry_detail(request, pk):
    time_entry = get_object_or_404(TimeEntry, pk=pk)
    return render(request, 'timesheets/time_entry_detail.html', {'time_entry': time_entry})

@login_required
def time_entry_list(request):
    # For admin, show all time entries; for regular users, show only their own
    if request.user.is_superuser:
        time_entries = TimeEntry.objects.all()
    else:
        time_entries = TimeEntry.objects.filter(user=request.user)

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        time_entries = time_entries.filter(
            Q(user__username__icontains=search_query) |
            Q(date__icontains=search_query) |
            Q(start_time__icontains=search_query) |
            Q(end_time__icontains=search_query) |
            Q(jobs__labor_code__icontains=search_query) |
            Q(jobs__description__icontains=search_query) |
            Q(jobs__activity_start_mileage__icontains=search_query) |
            Q(jobs__activity_end_mileage__icontains=search_query) |
            Q(hours_for_the_day__icontains=search_query) |
            Q(total_miles__icontains=search_query)
        ).distinct()

    # Sorting functionality
    sort_by = request.GET.get('sort_by', 'date')  # Default sort by date
    valid_sort_fields = ['date', 'start_time', 'end_time', 'hours_for_the_day', 'total_miles']
    if request.user.is_superuser:
        valid_sort_fields.append('user__username')
    
    if sort_by in valid_sort_fields:
        time_entries = time_entries.order_by(sort_by)
    else:
        sort_by = 'date'  # Default to date if an invalid sort option is provided
        time_entries = time_entries.order_by(sort_by)

    context = {
        'time_entries': time_entries,
        'search_query': search_query,
        'sort_by': sort_by
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
            
            return redirect('time_entry_list')
        else:
            print(f"Form errors: {form.errors}")
            print(f"Formset errors: {formset.errors}")
    else:
        form = TimeEntryForm()
        formset = JobFormSet()
    
    return render(request, 'timesheets/time_entry_form.html', {'form': form, 'job_formset': formset})
    
@login_required
def time_entry_edit(request, pk):
    time_entry = get_object_or_404(TimeEntry, pk=pk)
    
    JobFormSet = inlineformset_factory(
        TimeEntry, 
        Job, 
        form=JobForm, 
        extra=1, 
        can_delete=True
    )

    if request.method == 'POST':
        form = TimeEntryForm(request.POST, instance=time_entry)
        formset = JobFormSet(request.POST, instance=time_entry)

        if form.is_valid() and formset.is_valid():
            time_entry = form.save(commit=False)
            time_entry.user = request.user  # Ensure the user is set
            time_entry.save()

            # Save formset
            instances = formset.save(commit=False)
            for instance in instances:
                instance.time_entry = time_entry
                instance.save()
            
            # Handle deletions
            for obj in formset.deleted_objects:
                obj.delete()

            return redirect('time_entry_list')
        else:
            print(f"Form errors: {form.errors}")
            print(f"Formset errors: {formset.errors}")
    else:
        form = TimeEntryForm(instance=time_entry)
        formset = JobFormSet(instance=time_entry)

    return render(request, 'timesheets/time_entry_form.html', {
        'form': form,
        'job_formset': formset,
        'edit': True
    })

@login_required
def time_entry_delete(request, pk):
    time_entry = get_object_or_404(TimeEntry, pk=pk)
    if request.method == 'POST':
        time_entry.delete()
        return redirect('time_entry_list')
    
    return render(request, 'timesheets/time_entry_confirm_delete.html', {'time_entry': time_entry})



@login_required
def user_summary_report(request):
    # Determine the selected user (for admin)
    if request.user.is_superuser:
        selected_user_id = request.GET.get('user')
        selected_user = User.objects.filter(id=selected_user_id).first() if selected_user_id else request.user
        users = User.objects.all()
    else:
        selected_user = request.user
        users = None  # No dropdown for non-admin users

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

    # Filter time entries for the selected user and week
    time_entries = TimeEntry.objects.filter(user=selected_user, date__range=[week_start, week_end]).prefetch_related('jobs')

    # Calculate weekly hours per labor code and day
    weekly_hours = {}
    daily_totals = {day: 0.00 for day in ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']}
    total_hours_for_week = 0.00  # To track the total hours worked in the week

    for entry in time_entries:
        for job in entry.jobs.all():
            day_of_week = entry.date.strftime('%A')
            if job.labor_code not in weekly_hours:
                weekly_hours[job.labor_code] = {
                    "description": job.description,
                    "labor_code_description": job.labor_code_description,
                    "hours": {day: 0.00 for day in ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']}
                }
            try:
                hours_worked = float(entry.hours_to_be_paid or 0)
            except (ValueError, TypeError):
                hours_worked = 0.00
            weekly_hours[job.labor_code]["hours"][day_of_week] += hours_worked
            daily_totals[day_of_week] += hours_worked
            total_hours_for_week += hours_worked

    # Calculate regular and overtime hours
    total_regular_hours = min(total_hours_for_week, 40.00)
    total_overtime_hours = max(0.00, total_hours_for_week - 40.00)
    total_double_time_hours = 0.00  # Example logic, adjust as needed
    grand_total_hours = total_hours_for_week  # Grand total includes all hours worked

    context = {
        'time_entries': time_entries,
        'weekly_hours': weekly_hours,
        'total_regular_hours': total_regular_hours,
        'total_overtime_hours': total_overtime_hours,
        'total_double_time_hours': total_double_time_hours,
        'grand_total_hours': grand_total_hours,
        'daily_totals': daily_totals,
        'users': users,
        'selected_user': selected_user,
        'week_start': week_start,
        'week_end': week_end,
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
    
    JobFormSet = inlineformset_factory(
        TimeEntry, 
        Job, 
        form=JobForm, 
        extra=1, 
        can_delete=False
    )

    if request.method == 'POST':
        formset = JobFormSet(request.POST, instance=time_entry)
        if formset.is_valid():
            instances = formset.save(commit=False)
            for instance in instances:
                instance.time_entry = time_entry
                instance.save()
            time_entry.save()  # This will trigger the recalculation of hours and mileage
            return redirect('time_entry_list')
    else:
        formset = JobFormSet(instance=time_entry)

    return render(request, 'timesheets/add_job.html', {
        'formset': formset,
        'time_entry': time_entry,
        'created': created,
    })
    
@login_required
def dashboard(request):
    # Get date range from request, default to current week if not provided
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not start_date or not end_date:
        today = timezone.now().date()
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
    else:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            logger.error(f"Invalid date format: start_date={start_date}, end_date={end_date}")
            # Fall back to current week if date parsing fails
            today = timezone.now().date()
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)

    logger.info(f"Date range: {start_date} to {end_date}")

    if request.user.is_superuser:
        selected_user_id = request.GET.get('user_id')
        if selected_user_id:
            selected_user = User.objects.get(id=selected_user_id)
        else:
            selected_user = request.user

        all_users = User.objects.all()
        user_stats = []
        for user in all_users:
            user_entries = TimeEntry.objects.filter(
                user=user,
                date__range=[start_date, end_date]
            )
            total_hours = user_entries.aggregate(Sum('hours_for_the_day'))['hours_for_the_day__sum'] or 0
            total_entries = user_entries.count()
            user_stats.append({
                'user': user,
                'total_hours': round(total_hours, 2),
                'total_entries': total_entries
            })
    else:
        selected_user = request.user
        user_stats = None
        all_users = None

    entries = TimeEntry.objects.filter(
        user=selected_user,
        date__range=[start_date, end_date]
    )
    
    total_hours = entries.aggregate(Sum('hours_for_the_day'))['hours_for_the_day__sum'] or 0
    total_entries = entries.count()
    recent_entries = entries.order_by('-date')[:5]
    
    labor_code_data = list(Job.objects.filter(
        time_entry__user=selected_user,
        time_entry__date__range=[start_date, end_date]
    ).values('labor_code').annotate(count=Sum('time_entry__hours_for_the_day')))
    
    daily_hours_data = list(entries.values('date').annotate(hours=Sum('hours_for_the_day')).order_by('date'))

    # Log the data being sent to the template
    logger.info(f"Labor Code Data: {json.dumps(labor_code_data, cls=DecimalEncoder)}")
    logger.info(f"Daily Hours Data: {json.dumps(daily_hours_data, cls=DecimalEncoder, default=str)}")

    context = {
        'selected_user': selected_user,
        'total_hours': round(total_hours, 2),
        'total_entries': total_entries,
        'recent_entries': recent_entries,
        'labor_code_data': json.dumps(labor_code_data, cls=DecimalEncoder),
        'daily_hours_data': json.dumps(daily_hours_data, cls=DecimalEncoder, default=str),
        'start_date': start_date,
        'end_date': end_date,
        'user_stats': user_stats,
        'all_users': all_users,
        'is_admin': request.user.is_superuser
    }
    
    return render(request, 'timesheets/dashboard.html', context)