from timesheets.models import TimeEntry, Job, TimeEntryApproval, ApprovalNotification

def clear_timesheet_data():
    """Clear all timesheet related data from the database"""
    try:
        print('Deleting notifications...')
        ApprovalNotification.objects.all().delete()
        
        print('Deleting time entry approvals...')
        TimeEntryApproval.objects.all().delete()
        
        print('Deleting jobs...')
        Job.objects.all().delete()
        
        print('Deleting time entries...')
        TimeEntry.objects.all().delete()
        
        print('Successfully cleared all time entries and related data')
        
    except Exception as e:
        print(f'Error occurred: {str(e)}')