from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # Home view
    path('entries/', views.time_entry_list, name='time_entry_list'),  # List of time entries
    path('new/', views.time_entry_create, name='time_entry_create'),
    path('<int:pk>/', views.time_entry_detail, name='time_entry_detail'),
    path('edit/<int:pk>/', views.time_entry_edit, name='time_entry_edit'),
    path('delete/<int:pk>/', views.time_entry_delete, name='time_entry_delete'),
    path('summary/', views.user_summary_report, name='user_summary_report'),
    path('add-job/', views.add_job_to_time_entry, name='add_job_to_time_entry'),
]