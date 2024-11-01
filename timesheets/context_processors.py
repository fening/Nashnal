def notification_context(request):
    """Add notification counts to global template context"""
    if request.user.is_authenticated and hasattr(request.user, 'role') and request.user.role == 'Supervisor':
        try:
            from .models import TimeEntryApproval, ApprovalNotification
            
            unread_notifications = ApprovalNotification.objects.filter(
                recipient=request.user,
                read=False
            ).count()
            
            pending_approvals = TimeEntryApproval.objects.filter(
                time_entry__user__supervisor=request.user,
                status='pending'
            ).count()
            
            recent_notifications = ApprovalNotification.objects.filter(
                recipient=request.user
            ).order_by('-created_at')[:5]
            
            return {
                'unread_notifications_count': unread_notifications,
                'pending_approvals_count': pending_approvals,
                'notifications': recent_notifications
            }
        except:
            # Return empty context if there's any error
            return {
                'unread_notifications_count': 0,
                'pending_approvals_count': 0,
                'notifications': []
            }
    return {
        'unread_notifications_count': 0,
        'pending_approvals_count': 0,
        'notifications': []
    }
    
def page_title(request):
    """Add default page title to context"""
    return {
        'view_title': 'Dashboard'  # Default title
    }