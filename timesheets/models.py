# The above classes define models for job details, time entries, labor codes, and jobs with methods to
# calculate hours, mileage, and perform related calculations.
from django.db import models
from datetime import datetime, timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms import IntegerField
from django.utils.functional import cached_property
from django.urls import reverse
from django.core.validators import FileExtensionValidator
import os

class JobDetails(models.Model):
    job_number = models.CharField(max_length=50, unique=True, editable=False)
    project_number = models.CharField(max_length=50, blank=True, null=True)  # New field
    client_number = models.CharField(max_length=50, blank=True, null=True)   # New field
    job_description = models.CharField(max_length=255)  # Add max_length for CharField
    distance_office = models.DecimalField(max_digits=8, decimal_places=2, help_text="Distance in miles")
    time_office = models.IntegerField(help_text="Travel time to office in minutes (e.g. 90 for 1 hour 30 minutes)")

    def save(self, *args, **kwargs):
        if not self.job_number:  # Only set job_number if it's not already set
            last_job = JobDetails.objects.order_by('-id').first()
            if last_job and last_job.job_number.startswith('JOB-'):
                try:
                    last_number = int(last_job.job_number.split('-')[-1])
                    new_number = last_number + 1
                except ValueError:
                    new_number = 1  # Reset to 1 if the format is incorrect
            else:
                new_number = 1  # If no valid last job or first entry
            self.job_number = f'JOB-{new_number:04d}'  # Format as 'JOB-XXXX'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.job_number}"

    class Meta:
        verbose_name_plural = "Job Details"
    
class TimeEntry(models.Model):
    LOCATION_CHOICES = [
        ('Home', 'Home'),
        ('Office', 'Office'),
    ]
    
    VEHICLE_CHOICES = [
        (True, 'Company Vehicle'),
        (False, 'Personal Vehicle'),
    ]
    
    id = models.AutoField(primary_key=True)

    
    date = models.DateField(default=datetime.today)  # New field for date
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    start_location = models.CharField(max_length=10, choices=LOCATION_CHOICES, default='Home')
    end_location = models.CharField(max_length=10, choices=LOCATION_CHOICES, default='Home')
    
    # Mileage fields
    initial_mileage = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    final_mileage = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    activity_start_mileage = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    activity_end_mileage = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    
    # Calculated fields for mileage
    total_miles = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    travel_miles_subtract = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    miles_to_be_paid = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)

    # Time fields
    initial_leave_time = models.TimeField(null=True, blank=True)
    final_arrive_time = models.TimeField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    # Calculated fields
    hours_on_site = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    hours_for_the_day = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    travel_time_subtract = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    hours_to_be_paid = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    company_vehicle_used = models.BooleanField(choices=VEHICLE_CHOICES,default=False, verbose_name="Vehicle Used")
    comments = models.TextField(blank=True, null=True, help_text="Any additional notes or comments for this time entry.")
    
    # Add these new fields
    attachment = models.FileField(
        upload_to='timesheet_attachments/%Y/%m/%d/',
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png']
            )
        ],
        help_text="Allowed file types: PDF, DOC, DOCX, JPG, PNG"
    )
    attachment_name = models.CharField(max_length=255, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'date'], name='timesheet_user_date_idx'),
            models.Index(fields=['date'], name='timesheet_date_only_idx'),
            models.Index(fields=['start_time'], name='timesheet_start_time_idx'),
            models.Index(fields=['end_time'], name='timesheet_end_time_idx'),
            models.Index(fields=['hours_for_the_day'], name='timesheet_hours_day_idx'),
            models.Index(fields=['total_miles'], name='timesheet_total_miles_idx'),
            models.Index(fields=['miles_to_be_paid'], name='timesheet_paid_miles_idx'),
            models.Index(fields=['hours_to_be_paid'], name='timesheet_paid_hours_idx'),
            models.Index(fields=['start_location'], name='timesheet_start_loc_idx'),
            models.Index(fields=['end_location'], name='timesheet_end_loc_idx'),
            # Composite index for common search and sort patterns
            models.Index(fields=['user', 'date', 'start_time'], name='timesheet_user_date_time_idx'),
        ]
        ordering = ['-date', '-start_time']
        
    def calculate_hours(self):
        lunch_break = 0.5  # 30 minutes lunch break in hours

        if self.initial_leave_time and self.final_arrive_time:
            total_duration = datetime.combine(datetime.min, self.final_arrive_time) - datetime.combine(datetime.min, self.initial_leave_time)
            self.hours_for_the_day = round(total_duration.total_seconds() / 3600, 2)

        if self.jobs.exists():
            first_job = self.jobs.order_by('activity_arrive_time').first()
            last_job = self.jobs.order_by('-activity_leave_time').first()

            if first_job and last_job:
                self.start_time = first_job.activity_arrive_time
                self.end_time = last_job.activity_leave_time

                # Calculate on-site hours and subtract lunch break
                work_duration = datetime.combine(datetime.min, self.end_time) - datetime.combine(datetime.min, self.start_time)
                self.hours_on_site = round(work_duration.total_seconds() / 3600 - lunch_break, 2)

            unpaid_travel_time = 0

            # Calculate unpaid travel time for the first leg
            if self.initial_leave_time and first_job.activity_arrive_time:
                travel_time_first_leg = (datetime.combine(datetime.min, first_job.activity_arrive_time) - datetime.combine(datetime.min, self.initial_leave_time)).total_seconds() / 3600
                time_home_to_office = (self.user.time_office or 0) / 60  # Convert minutes to hours, use 0 if None

                if self.start_location == 'Home':
                    # Unpaid time is the shorter of actual travel time or home-to-office time
                    unpaid_travel_time_first_leg = min(travel_time_first_leg, time_home_to_office)
                else:  # Start from Office
                    unpaid_travel_time_first_leg = 0  # All travel time is paid

                unpaid_travel_time += unpaid_travel_time_first_leg

            # Travel time between jobs is paid (unchanged)

            # Calculate unpaid travel time for the last leg
            if last_job.activity_leave_time and self.final_arrive_time:
                travel_time_last_leg = (datetime.combine(datetime.min, self.final_arrive_time) - datetime.combine(datetime.min, last_job.activity_leave_time)).total_seconds() / 3600
                time_home_to_office = (self.user.time_office or 0) / 60  # Convert minutes to hours, use 0 if None

                if self.end_location == 'Home':
                    # Unpaid time is the shorter of actual travel time or home-to-office time
                    unpaid_travel_time_last_leg = min(travel_time_last_leg, time_home_to_office)
                else:  # End at Office
                    unpaid_travel_time_last_leg = 0  # All travel time is paid

                unpaid_travel_time += unpaid_travel_time_last_leg

            self.travel_time_subtract = round(unpaid_travel_time, 2)

        if self.hours_for_the_day is not None and self.travel_time_subtract is not None:
            self.hours_to_be_paid = round(self.hours_for_the_day - self.travel_time_subtract - lunch_break, 2)

    def calculate_mileage(self):
        if self.initial_mileage is not None and self.final_mileage is not None:
            self.total_miles = self.final_mileage - self.initial_mileage

            if self.company_vehicle_used:
                # If company vehicle is used, set both travel_miles_subtract and miles_to_be_paid to 0
                self.travel_miles_subtract = 0
                self.miles_to_be_paid = 0
            else:
                travel_miles_subtract = 0

                if self.jobs.exists():
                    first_job = self.jobs.order_by('activity_arrive_time').first()
                    last_job = self.jobs.order_by('-activity_leave_time').first()

                    # First Leg Calculation
                    if first_job.activity_start_mileage is not None:
                        miles_traveled_first_leg = first_job.activity_start_mileage - self.initial_mileage
                        miles_home_to_office = self.user.distance_office or 0  # Use 0 if distance_office is None

                        if self.start_location == 'Home':
                            # Subtract the shorter of actual miles or home-to-office miles
                            unpaid_miles_first_leg = min(miles_traveled_first_leg, miles_home_to_office)
                        else:  # Start from Office
                            unpaid_miles_first_leg = 0

                        travel_miles_subtract += unpaid_miles_first_leg

                    # Last Leg Calculation
                    if last_job.activity_end_mileage is not None:
                        miles_traveled_last_leg = self.final_mileage - last_job.activity_end_mileage
                        miles_home_to_office = self.user.distance_office or 0  # Use 0 if distance_office is None

                        if self.end_location == 'Home':
                            # Subtract the shorter of actual miles or home-to-office miles
                            unpaid_miles_last_leg = min(miles_traveled_last_leg, miles_home_to_office)
                        else:  # End at Office
                            unpaid_miles_last_leg = 0

                        travel_miles_subtract += unpaid_miles_last_leg

                self.travel_miles_subtract = round(travel_miles_subtract, 2)
                self.miles_to_be_paid = round(self.total_miles - self.travel_miles_subtract, 2)
            
    def save(self, *args, **kwargs):
        if self.attachment and not self.attachment_name:
            self.attachment_name = self.attachment.name
        super().save(*args, **kwargs)
        
        if self.jobs.exists():
            first_job = self.jobs.order_by('activity_arrive_time').first()
            last_job = self.jobs.order_by('-activity_leave_time').last()
            
            if first_job and last_job:
                self.start_time = first_job.activity_arrive_time
                self.end_time = last_job.activity_leave_time
                self.activity_end_mileage = last_job.activity_end_mileage

        # Perform calculations
        self.calculate_hours()
        self.calculate_mileage()

        # Save again with calculated fields
        super().save(*args, **kwargs)

    def calculate_total_hours(self):
        if self.start_time and self.end_time:
            work_duration = datetime.combine(datetime.min, self.end_time) - datetime.combine(datetime.min, self.start_time)
            total_hours = work_duration.total_seconds() / 3600
            return round(total_hours, 2)
        return 0
    
    @property
    def travel_time_first_leg(self):
        if self.initial_leave_time and self.jobs.exists():
            first_job = self.jobs.order_by('activity_arrive_time').first()
            if first_job.activity_arrive_time:
                delta = datetime.combine(datetime.min, first_job.activity_arrive_time) - datetime.combine(datetime.min, self.initial_leave_time)
                return round(delta.total_seconds() / 3600, 2)  # in hours
        return 0

    @property
    def travel_time_last_leg(self):
        if self.final_arrive_time and self.jobs.exists():
            last_job = self.jobs.order_by('-activity_leave_time').first()
            if last_job.activity_leave_time:
                delta = datetime.combine(datetime.min, self.final_arrive_time) - datetime.combine(datetime.min, last_job.activity_leave_time)
                return round(delta.total_seconds() / 3600, 2)  # in hours
        return 0

    @property
    def standard_time_home_to_office(self):
        return round((self.user.time_office or 0) / 60, 2)  # Convert minutes to hours

    @property
    def time_to_subtract_first_leg(self):
        if self.start_location == 'Home':
            return round(min(self.travel_time_first_leg, self.standard_time_home_to_office), 2)
        return 0

    @property
    def time_to_subtract_last_leg(self):
        if self.end_location == 'Home':
            return round(min(self.travel_time_last_leg, self.standard_time_home_to_office), 2)
        return 0

    @property
    def miles_traveled_first_leg(self):
        if self.initial_mileage is not None and self.jobs.exists():
            first_job = self.jobs.order_by('activity_arrive_time').first()
            if first_job.activity_start_mileage is not None:
                return round(first_job.activity_start_mileage - self.initial_mileage, 2)
        return 0

    @property
    def miles_traveled_last_leg(self):
        if self.final_mileage is not None and self.jobs.exists():
            last_job = self.jobs.order_by('-activity_leave_time').first()
            if last_job.activity_end_mileage is not None:
                return round(self.final_mileage - last_job.activity_end_mileage, 2)
        return 0

    @property
    def standard_distance_home_to_office(self):
        return round(self.user.distance_office or 0, 2)

    @property
    def miles_to_subtract_first_leg(self):
        if self.start_location == 'Home':
            return round(min(self.miles_traveled_first_leg, self.standard_distance_home_to_office), 2)
        return 0

    @property
    def miles_to_subtract_last_leg(self):
        if self.end_location == 'Home':
            return round(min(self.miles_traveled_last_leg, self.standard_distance_home_to_office), 2)
        return 0
    
    @property
    def approval_status(self):
        try:
            return self.approval.status
        except TimeEntryApproval.DoesNotExist:
            return None

    @property
    def can_submit_for_approval(self):
        return (
            self.approval_status is None or 
            self.approval_status == 'rejected'
        )

    @property
    def is_pending_approval(self):
        return self.approval_status == 'pending'

    @property
    def is_approved(self):
        return self.approval_status == 'approved'

    @property
    def is_rejected(self):
        return self.approval_status == 'rejected'
    
    @cached_property
    def total_job_count(self):
        return self.jobs.count()

    @cached_property
    def first_job(self):
        return self.jobs.order_by('activity_arrive_time').first()

    @cached_property
    def last_job(self):
        return self.jobs.order_by('-activity_leave_time').first()
    
    def get_attachment_url(self):
        if self.attachment:
            return self.attachment.url
        return None

    def get_attachment_filename(self):
        if self.attachment:
            return os.path.basename(self.attachment.name)
        return None

class LaborCode(models.Model):
    laborcode = models.IntegerField(unique=True)
    labor_code_description = models.CharField(max_length=255)

    def __str__(self):
        return str(self.laborcode)
    
class Job(models.Model):
    time_entry = models.ForeignKey(TimeEntry, related_name='jobs', on_delete=models.CASCADE)
    job_number = models.ForeignKey(JobDetails, on_delete=models.CASCADE, verbose_name="Job Number")
    activity_start_mileage = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    activity_arrive_time = models.TimeField()
    activity_leave_time = models.TimeField()
    activity_end_mileage = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    labor_code =  models.ForeignKey(LaborCode, on_delete=models.CASCADE)
    
    class Meta:
        indexes = [
            # Primary access patterns
            models.Index(fields=['time_entry', 'activity_arrive_time'], name='job_timeentry_arrive_idx'),
            models.Index(fields=['time_entry', 'activity_leave_time'], name='job_timeentry_leave_idx'),
            
            # Individual field indexes for common queries
            models.Index(fields=['job_number'], name='job_number_idx'),
            models.Index(fields=['labor_code'], name='job_labor_code_idx'),
            
            # Composite indexes for efficient sorting and filtering
            models.Index(fields=['time_entry', 'job_number', 'activity_arrive_time'], 
                        name='job_entry_num_time_idx'),
        ]
        ordering = ['activity_arrive_time']  # Default ordering
        
    @property
    def labor_code_description(self):
        return self.labor_code.labor_code_description
    
    @property
    def job_description(self):
        return self.job_number.job_description
    
    def calculate_job_miles(self):
        if self.activity_start_mileage is not None and self.activity_end_mileage is not None:
            return self.activity_end_mileage - self.activity_start_mileage
        return None

    def save(self, *args, **kwargs):
        if self.job_number and not self.job_description:
            self.job_description = self.client_job_description
        super().save(*args, **kwargs)
        if self.time_entry:
            self.time_entry.save()  # Trigger recalculation in TimeEntry

# models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class ApprovalNotification(models.Model):
    NOTIFICATION_TYPES = (
        ('submission', 'Timesheet Submitted'),
        ('first_approval', 'First Approval'),
        ('approval', 'Timesheet Approved'),
        ('rejection', 'Timesheet Rejected'),
        ('review_needed', 'Review Needed'),
    )
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    notification_type = models.CharField(
        max_length=20, 
        choices=NOTIFICATION_TYPES,
        default='submission'  # Adding default here
    )
    read = models.BooleanField(default=False)
    time_entry_approval = models.ForeignKey('TimeEntryApproval', on_delete=models.CASCADE, related_name='notifications')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def mark_as_read(self):
        self.read = True
        self.save()

    @property
    def get_target_url(self):
        """Returns the URL where this notification should redirect to"""
        if self.time_entry_approval and self.time_entry_approval.time_entry:
            time_entry = self.time_entry_approval.time_entry
            
            # Different URLs based on notification type
            if self.notification_type == 'submission':
                if self.recipient.is_superuser:
                    return reverse('timesheets:review_time_entry', kwargs={'pk': time_entry.pk})
            elif self.notification_type == 'review_needed':
                return reverse('timesheets:review_time_entry', kwargs={'pk': time_entry.pk})
            elif self.notification_type in ['approval', 'rejection', 'first_approval']:
                return reverse('timesheets:time_entry_detail', kwargs={'pk': time_entry.pk})
                
        # Default to dashboard if no specific URL is found
        return reverse('timesheets:dashboard')

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class TimeEntryApproval(models.Model):
    # Status Constants
    PENDING_FIRST = 'pending_first'
    PENDING_SECOND = 'pending_second'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    
    STATUS_CHOICES = [
        (PENDING_FIRST, 'Pending First Approval'),
        (PENDING_SECOND, 'Pending Second Approval'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
    ]
    
    # Core Fields
    time_entry = models.OneToOneField('TimeEntry', on_delete=models.CASCADE, related_name='approval')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING_FIRST)
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    # Review Fields - First Level
    first_reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='first_reviews')
    first_reviewed_at = models.DateTimeField(null=True, blank=True)
    first_reviewer_comments = models.TextField(blank=True, null=True)
    
    # Review Fields - Second Level
    second_reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='second_reviews')
    second_reviewed_at = models.DateTimeField(null=True, blank=True)
    second_reviewer_comments = models.TextField(blank=True, null=True)
    
    # Additional Fields
    submitter_comments = models.TextField(blank=True, null=True)
    
    def can_approve(self, user):
        """Check if the user can approve this time entry"""
        if self.status == self.PENDING_FIRST:
            return user.is_superuser
        elif self.status == self.PENDING_SECOND:
            return hasattr(user, 'role') and user.role == 'Supervisor'
        return False
    
    def create_notifications(self, action, reviewer=None, comments=None):
        """Create notifications for all relevant parties based on the approval action."""
        time_entry = self.time_entry
        employee = time_entry.user
        superusers = User.objects.filter(is_superuser=True)
        
        # Check for existing notifications to prevent duplicates
        existing_notification = ApprovalNotification.objects.filter(
            time_entry_approval=self,
            notification_type=action
        ).first()
        
        if existing_notification:
            return  # Skip if notification already exists

        if action == 'submit':
            message = f"{employee.get_full_name()} submitted a timesheet for {time_entry.date}"
            # Only notify superusers who haven't received this notification yet
            for superuser in superusers:
                ApprovalNotification.objects.get_or_create(
                    recipient=superuser,
                    time_entry_approval=self,
                    notification_type='submission',
                    defaults={'message': message}
                )

        elif action == 'first_approve':
            supervisor = employee.supervisor
            message = f"Your timesheet for {time_entry.date} passed first approval by {reviewer.get_full_name()}"
            
            # Notify employee
            ApprovalNotification.objects.get_or_create(
                recipient=employee,
                time_entry_approval=self,
                notification_type='first_approval',
                defaults={'message': message}
            )
            
            # Notify supervisor if exists
            if supervisor:
                supervisor_message = f"Timesheet from {employee.get_full_name()} needs your review"
                ApprovalNotification.objects.get_or_create(
                    recipient=supervisor,
                    time_entry_approval=self,
                    notification_type='review_needed',
                    defaults={'message': supervisor_message}
                )

        elif action == 'final_approve':
            message = f"Your timesheet for {time_entry.date} has been approved by {reviewer.get_full_name()}"
            # Notify employee
            ApprovalNotification.objects.get_or_create(
                recipient=employee,
                time_entry_approval=self,
                notification_type='approval',
                defaults={'message': message}
            )
            
            # Notify superusers (except reviewer)
            for superuser in superusers:
                if superuser != reviewer:
                    superuser_message = f"Timesheet from {employee.get_full_name()} for {time_entry.date} has been approved"
                    ApprovalNotification.objects.get_or_create(
                        recipient=superuser,
                        time_entry_approval=self,
                        notification_type='approval',
                        defaults={'message': superuser_message}
                    )

        elif action == 'reject':
            message = f"Your timesheet for {time_entry.date} was rejected by {reviewer.get_full_name()}"
            if comments:
                message += f"\nComments: {comments}"
            
            # Notify employee
            ApprovalNotification.objects.get_or_create(
                recipient=employee,
                time_entry_approval=self,
                notification_type='rejection',
                defaults={'message': message}
            )

    def add_to_history(self, status, reviewer, comments, is_first=False, is_second=False):
        """Add a new entry to the approval history"""
        return TimeEntryApprovalHistory.objects.create(
            time_entry_approval=self,
            status=status,
            reviewed_by=reviewer,
            comments=comments,
            is_first_review=is_first,
            is_second_review=is_second
        )

    @property
    def current_status(self):
        """Get the latest status from history"""
        latest = self.history.first()
        return latest.status if latest else self.PENDING_FIRST

    @property
    def latest_first_review(self):
        """Get the latest first review from history"""
        return self.history.filter(is_first_review=True).first()

    @property
    def latest_second_review(self):
        """Get the latest second review from history"""
        return self.history.filter(is_second_review=True).first()


class TimeEntryApprovalHistory(models.Model):
    time_entry_approval = models.ForeignKey(TimeEntryApproval, on_delete=models.CASCADE, related_name='history')
    status = models.CharField(max_length=20, choices=TimeEntryApproval.STATUS_CHOICES)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    reviewed_at = models.DateTimeField(auto_now_add=True)
    comments = models.TextField(blank=True, null=True)
    is_first_review = models.BooleanField(default=False)
    is_second_review = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-reviewed_at']
        verbose_name_plural = "Time Entry Approval Histories"

    def __str__(self):
        return f"{self.time_entry_approval.time_entry} - {self.status} at {self.reviewed_at}"