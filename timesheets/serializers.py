from rest_framework import serializers
from .models import JobDetails, TimeEntry, LaborCode, Job

class JobDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobDetails
        fields = ['job_number', 'job_description', 'distance_office', 'time_office']
        read_only_fields = ['job_number']

class LaborCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LaborCode
        fields = ['laborcode', 'labor_code_description']

class JobSerializer(serializers.ModelSerializer):
    job_number = JobDetailsSerializer(read_only=True)
    labor_code = LaborCodeSerializer(read_only=True)
    job_description = serializers.CharField(read_only=True)
    labor_code_description = serializers.CharField(read_only=True)

    class Meta:
        model = Job
        fields = ['id', 'job_number', 'activity_start_mileage', 'activity_arrive_time', 
                  'activity_leave_time', 'activity_end_mileage', 'labor_code', 
                  'job_description', 'labor_code_description']

class TimeEntrySerializer(serializers.ModelSerializer):
    jobs = JobSerializer(many=True, read_only=True)
    miles_traveled_first_leg = serializers.DecimalField(max_digits=7, decimal_places=2, read_only=True)
    distance_office_to_first_job = serializers.DecimalField(max_digits=7, decimal_places=2, read_only=True)
    miles_to_pay_first_leg = serializers.DecimalField(max_digits=7, decimal_places=2, read_only=True)
    miles_traveled_last_leg = serializers.DecimalField(max_digits=7, decimal_places=2, read_only=True)
    distance_last_job_to_office = serializers.DecimalField(max_digits=7, decimal_places=2, read_only=True)
    miles_to_pay_last_leg = serializers.DecimalField(max_digits=7, decimal_places=2, read_only=True)
    travel_time_first_leg = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    time_office_to_first_job = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    unpaid_travel_time_first_leg = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    travel_time_last_leg = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    time_last_job_to_office = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    unpaid_travel_time_last_leg = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    total_unpaid_travel_time = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)

    class Meta:
        model = TimeEntry
        fields = ['id', 'date', 'user', 'start_location', 'end_location', 'initial_mileage', 
                  'final_mileage', 'activity_start_mileage', 'activity_end_mileage', 
                  'total_miles', 'travel_miles_subtract', 'miles_to_be_paid', 
                  'initial_leave_time', 'final_arrive_time', 'start_time', 'end_time', 
                  'hours_on_site', 'hours_for_the_day', 'travel_time_subtract', 
                  'hours_to_be_paid', 'company_vehicle_used', 'comments', 'jobs',
                  'miles_traveled_first_leg', 'distance_office_to_first_job', 
                  'miles_to_pay_first_leg', 'miles_traveled_last_leg', 
                  'distance_last_job_to_office', 'miles_to_pay_last_leg',
                  'travel_time_first_leg', 'time_office_to_first_job', 
                  'unpaid_travel_time_first_leg', 'travel_time_last_leg', 
                  'time_last_job_to_office', 'unpaid_travel_time_last_leg',
                  'total_unpaid_travel_time']
        read_only_fields = ['total_miles', 'travel_miles_subtract', 'miles_to_be_paid', 
                            'hours_on_site', 'hours_for_the_day', 'travel_time_subtract', 
                            'hours_to_be_paid']