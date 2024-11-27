from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from .models import TimeEntryApproval, ApprovalNotification, TimeEntry
from django.db import IntegrityError

User = get_user_model()

def create_notification_if_not_exists(recipient, message, notification_type, time_entry_approval):
    """Helper function to create notification if it doesn't already exist"""
    try:
        notification, created = ApprovalNotification.objects.get_or_create(
            recipient=recipient,
            time_entry_approval=time_entry_approval,
            notification_type=notification_type,
            defaults={'message': message}
        )
        if not created:
            # Update the message if notification already exists
            notification.message = message
            notification.read = False  # Reset read status
            notification.created_at = timezone.now()  # Update timestamp
            notification.save()
        return notification
    except IntegrityError:
        # Log error or handle as needed
        return None

@receiver(post_save, sender=TimeEntryApproval)
def create_approval_notifications(sender, instance, created, **kwargs):
    """Create notifications when TimeEntryApproval status changes"""
    time_threshold = timezone.now() - timedelta(minutes=1)
    
    if created:
        # Notify superusers of new submission
        superusers = User.objects.filter(is_superuser=True)
        for superuser in superusers:
            create_notification_if_not_exists(
                recipient=superuser,
                message=f"New timesheet submitted by {instance.time_entry.user.get_full_name()} for {instance.time_entry.date}",
                notification_type='submission',
                time_entry_approval=instance
            )
    else:
        # Status change notifications
        if instance.status == TimeEntryApproval.PENDING_SECOND:
            # Notify supervisor
            supervisor = instance.time_entry.user.supervisor
            if supervisor:
                create_notification_if_not_exists(
                    recipient=supervisor,
                    message=f"Timesheet from {instance.time_entry.user.get_full_name()} needs your review",
                    notification_type='review_needed',
                    time_entry_approval=instance
                )
        elif instance.status in [TimeEntryApproval.APPROVED, TimeEntryApproval.REJECTED]:
            status_text = 'approved' if instance.status == TimeEntryApproval.APPROVED else 'rejected'
            notification_type = 'approval' if instance.status == TimeEntryApproval.APPROVED else 'rejection'
            
            message = f"Your timesheet for {instance.time_entry.date} was {status_text}"
            if instance.status == TimeEntryApproval.REJECTED and getattr(instance, 'comments', ''):
                reviewer_name = instance.reviewer.get_full_name() if hasattr(instance, 'reviewer') else 'a reviewer'
                message += f" by {reviewer_name}. Comments: {instance.comments}"
            
            create_notification_if_not_exists(
                recipient=instance.time_entry.user,
                message=message,
                notification_type=notification_type,
                time_entry_approval=instance
            )

@receiver(post_save, sender=User)
def setup_supervisor_permissions(sender, instance, created, **kwargs):
    """Signal handler to set up supervisor permissions when a user is created or updated"""
    if instance.role == 'Supervisor':
        try:
            # Get or create the supervisor group
            supervisor_group, _ = Group.objects.get_or_create(name='Supervisor')
            
            # Get content types for models
            timeentry_ct = ContentType.objects.get_for_model(TimeEntry)
            approval_ct = ContentType.objects.get_for_model(TimeEntryApproval)
            
            # Define permissions for both models
            permissions = [
                ('can_approve_timesheet', 'Can approve timesheet entries', approval_ct),
                ('can_reject_timesheet', 'Can reject timesheet entries', approval_ct),
                ('can_view_team_timesheets', 'Can view team timesheets', timeentry_ct),
                ('can_manage_notifications', 'Can manage notifications', approval_ct),
            ]
            
            # Create and add permissions to group
            for codename, name, content_type in permissions:
                permission, _ = Permission.objects.get_or_create(
                    codename=codename,
                    name=name,
                    content_type=content_type,
                )
                supervisor_group.permissions.add(permission)
            
            # Add user to supervisor group
            if not instance.groups.filter(name='Supervisor').exists():
                supervisor_group.user_set.add(instance)
                
        except Exception as e:
            print(f"Error setting up supervisor permissions: {e}")