from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from .models import TimeEntryApproval, ApprovalNotification, TimeEntry

User = get_user_model()

@receiver(post_save, sender=TimeEntryApproval)
def create_approval_notifications(sender, instance, created, **kwargs):
    """Create notifications when TimeEntryApproval status changes"""
    if created:
        # Notify superusers of new submission
        superusers = User.objects.filter(is_superuser=True)
        for superuser in superusers:
            ApprovalNotification.objects.create(
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
                ApprovalNotification.objects.create(
                    recipient=supervisor,
                    message=f"Timesheet from {instance.time_entry.user.get_full_name()} needs your review",
                    notification_type='review_needed',
                    time_entry_approval=instance
                )
        elif instance.status in [TimeEntryApproval.APPROVED, TimeEntryApproval.REJECTED]:
            # Notify employee
            ApprovalNotification.objects.create(
                recipient=instance.time_entry.user,
                message=f"Your timesheet for {instance.time_entry.date} has been {'approved' if instance.status == TimeEntryApproval.APPROVED else 'rejected'}",
                notification_type='approval' if instance.status == TimeEntryApproval.APPROVED else 'rejection',
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