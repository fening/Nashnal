from django.urls import path, include
from . import views
from .views import TimeEntryViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'time-entries', TimeEntryViewSet)

app_name = 'timesheets'

urlpatterns = [
    # Dashboard and Main Views
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('team-timesheets/', views.team_timesheets, name='team_timesheets'),
    path('supervisor-dashboard/', views.supervisor_dashboard, name='supervisor_dashboard'),

    # Time Entry CRUD
    path('time-entry/create/', views.time_entry_create, name='time_entry_create'),
    path('time-entry/<int:pk>/', views.time_entry_detail, name='time_entry_detail'),
    path('time-entry/<int:pk>/edit/', views.time_entry_edit, name='time_entry_edit'),
    path('time-entry/<int:pk>/delete/', views.time_entry_delete, name='time_entry_delete'),
    path('time-entry/list/', views.time_entry_list, name='time_entry_list'),
    path('time-entry/add-job/', views.add_job_to_time_entry, name='add_job_to_time_entry'),

    # Job Details Management
    path('job-details/create/', views.job_details_create_or_edit, name='job_details_create'),
    path('job-details/<int:pk>/edit/', views.job_details_create_or_edit, name='job_details_edit'),
    path('job-details/<int:pk>/delete/', views.job_details_delete, name='job_details_delete'),
    path('job-details/<int:job_id>/get/', views.get_job_details, name='get_job_details'),
    path('job-number/<int:job_id>/get/', views.get_job_number, name='get_job_number'),
    
    # Add new patterns to match the client requests
    path('time-entry/get-job-details/<int:job_id>/', views.get_job_details, name='get_job_details_for_entry'),
    path('time-entry/get-job-number/<int:job_id>/', views.get_job_number, name='get_job_number_for_entry'),

    # Labor Code Management
    path('labor-codes/', views.create_and_list_laborcode, name='create_and_list_laborcode'),
    path('labor-code/<int:description_id>/get/', views.get_labor_code, name='get_labor_code'),
    # Add this new URL pattern
    path('time-entry/get-labor-code/<int:description_id>/', views.get_labor_code, name='get_labor_code_for_entry'),

    # Reports and Summaries
    path('summary-report/', views.user_summary_report, name='user_summary_report'),

    # Approval System - reorganized and expanded
    path('time-entry/approvals/', include([
        path('pending/', views.pending_approvals, name='pending_approvals'),
        path('history/', views.approval_history, name='approval_history'),
        path('submit/<int:pk>/', views.submit_for_approval, name='submit_for_approval'),
        path('review/<int:pk>/', views.review_time_entry, name='review_time_entry'),
    ])),

    # Notifications
    path('notifications/', views.all_notifications, name='all_notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/clear-all/', views.clear_all_notifications, name='clear_all_notifications'),
    path('notifications/<int:notification_id>/delete/', views.delete_notification, name='delete_notification'),
    path('notifications/<int:notification_id>/handle/', views.notification_link_handler, name='notification_link_handler'),
]

# Add DRF router URLs
urlpatterns += router.urls