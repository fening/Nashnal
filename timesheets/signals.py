from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from .models import TimeEntryApproval

User = get_user_model()

@receiver(post_save, sender=User)
def setup_supervisor_permissions(sender, instance, created, **kwargs):
    """
    Signal handler to set up supervisor permissions when a user is created or updated
    """
    if instance.role == 'Supervisor':
        try:
            # Get or create the supervisor group
            supervisor_group, _ = Group.objects.get_or_create(name='Supervisor')
            
            # Get content type for TimeEntryApproval
            content_type = ContentType.objects.get_for_model(TimeEntryApproval)
            
            # Define permissions
            permissions = [
                ('can_approve_timesheet', 'Can approve timesheet entries'),
                ('can_reject_timesheet', 'Can reject timesheet entries'),
                ('can_view_team_timesheets', 'Can view team timesheets'),
            ]
            
            # Create and add permissions to group
            for codename, name in permissions:
                permission, _ = Permission.objects.get_or_create(
                    codename=codename,
                    name=name,
                    content_type=content_type,
                )
                supervisor_group.permissions.add(permission)
            
            # Add user to supervisor group if not already added
            if not instance.groups.filter(name='Supervisor').exists():
                supervisor_group.user_set.add(instance)
                
        except Exception as e:
            print(f"Error setting up supervisor permissions: {e}")