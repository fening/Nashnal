from django.contrib import admin
from .models import TimeEntry, Job

@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'start_location', 'end_location', 'hours_to_be_paid')
    list_filter = ('user', 'date')
    search_fields = ('user__username', 'user__email')

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('time_entry', 'activity_arrive_time', 'activity_leave_time', 'labor_code')
    list_filter = ('time_entry__user',)
    search_fields = ('time_entry__user__username', 'time_entry__user__email')