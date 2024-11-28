from django.db.models import Q
from timesheets.models import ApprovalNotification, TimeEntryApproval

def notification_context(request):
    """Add notification counts and data to global template context"""
    context = {
        'unread_notifications_count': 0,
        'pending_approvals_count': 0,
        'recent_notifications': [],
        'is_superuser': False,
        'is_supervisor': False
    }

    if not request.user.is_authenticated:
        return context

    try:
        user = request.user
        is_superuser = user.is_superuser
        is_supervisor = hasattr(user, 'role') and user.role == 'Supervisor'

        # Get unread notifications with select_related for better performance
        unread_notifications = ApprovalNotification.objects.filter(
            recipient=user,
            read=False
        ).select_related(
            'time_entry_approval',
            'time_entry_approval__time_entry'
        )

        # Get recent UNREAD notifications with all related data
        recent_notifications = unread_notifications.select_related(
            'recipient',
            'time_entry_approval',
            'time_entry_approval__time_entry',
            'time_entry_approval__time_entry__user'
        ).order_by('-created_at')[:5]

        # Get pending approvals based on user role
        if is_superuser:
            pending_approvals = TimeEntryApproval.objects.filter(
                status=TimeEntryApproval.PENDING_FIRST
            )
        elif is_supervisor:
            pending_approvals = TimeEntryApproval.objects.filter(
                status=TimeEntryApproval.PENDING_SECOND,
                time_entry__user__supervisor=user
            )
        else:
            pending_approvals = TimeEntryApproval.objects.filter(
                time_entry__user=user,
                status__in=[TimeEntryApproval.PENDING_FIRST, TimeEntryApproval.PENDING_SECOND]
            )

        context.update({
            'unread_notifications_count': unread_notifications.count(),
            'pending_approvals_count': pending_approvals.count(),
            'recent_notifications': recent_notifications,
            'is_superuser': is_superuser,
            'is_supervisor': is_supervisor,
        })

    except Exception as e:
        print(f"Error in notification context: {str(e)}")
        import traceback
        traceback.print_exc()

    return context


