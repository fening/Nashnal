from django.urls import path
from . import views

urlpatterns = [
    # Home page
    path('', views.home, name='home'),
    
    # Time Entry CRUD
    path('entries/', views.time_entry_list, name='time_entry_list'),  # List of time entries
    path('new/', views.time_entry_create, name='time_entry_create'),  # Create a new time entry
    path('<int:pk>/', views.time_entry_detail, name='time_entry_detail'),  # View time entry details
    path('edit/<int:pk>/', views.time_entry_edit, name='time_entry_edit'),  # Edit a time entry
    path('delete/<int:pk>/', views.time_entry_delete, name='time_entry_delete'),  # Delete a time entry
    
    # User summary report
    path('summary/', views.user_summary_report, name='user_summary_report'),  # User weekly summary report
    
    # Add jobs to a time entry
    path('add-job/', views.add_job_to_time_entry, name='add_job_to_time_entry'),  # Add job to time entry
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),  # Admin or user dashboard
    
    # Job details CRUD
    path('job-details/create/', views.job_details_create_or_edit, name='job_details_create'),  # Create job details
    path('job-details/edit/<int:pk>/', views.job_details_create_or_edit, name='job_details_edit'),  # Edit job details
    path('job-details/delete/<int:pk>/', views.job_details_delete, name='job_details_delete'),  # Delete job details
    
    # Fetching job details
    path('get-job-details/<int:job_id>/', views.get_job_details, name='get_job_details'),
    
    # Labor codes
    path('laborcodes/', views.create_and_list_laborcode, name='create_and_list_laborcode'),  # Create and list labor codes
    
    # Fetch job number and labor code based on description or ID
    path('get-job-number/<int:job_id>/', views.get_job_number, name='get_job_number'),
    path('get-labor-code/<int:description_id>/', views.get_labor_code, name='get_labor_code'),  # Fetch labor code by description ID
    

]