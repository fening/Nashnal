from django.db import models
from datetime import datetime, timedelta
from django.conf import settings

class ClientJob(models.Model):
    name = models.CharField(max_length=255)
    job_number = models.CharField(max_length=255)
    
class TimeEntry(models.Model):
    LOCATION_CHOICES = [
        ('Home', 'Home'),
        ('Office', 'Office'),
    ]
    
    id = models.AutoField(primary_key=True)
    # client_job = models.ForeignKey(ClientJob, on_delete=models.CASCADE)
    
    date = models.DateField(default=datetime.today)  # New field for date
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    start_location = models.CharField(max_length=10, choices=LOCATION_CHOICES, default='Home')
    end_location = models.CharField(max_length=10, choices=LOCATION_CHOICES, default='Home')
    
    # Mileage fields
    initial_mileage = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    final_mileage = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    activity_start_mileage = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    activity_end_mileage = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    
    # Calculated fields for mileage
    total_miles = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    travel_miles_subtract = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    miles_to_be_paid = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)

    # Time fields
    initial_leave_time = models.TimeField(null=True, blank=True)
    final_arrive_time = models.TimeField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    activity_arrive_time = models.TimeField(null=True, blank=True)
    activity_leave_time = models.TimeField(null=True, blank=True)

    # Calculated fields
    hours_on_site = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    hours_for_the_day = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    travel_time_subtract = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    hours_to_be_paid = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    def calculate_hours(self):
        if self.start_time and self.end_time:
            work_duration = datetime.combine(datetime.min, self.end_time) - datetime.combine(datetime.min, self.start_time)
            print("Work Duration (Hours on Site):", work_duration.total_seconds() / 3600)
            self.hours_on_site = round(work_duration.total_seconds() / 3600 - 0.5, 2)  # Subtract 30 minutes for lunch

        if self.initial_leave_time and self.final_arrive_time:
            total_duration = datetime.combine(datetime.min, self.final_arrive_time) - datetime.combine(datetime.min, self.initial_leave_time)
            print("Total Duration (Hours for the Day):", total_duration.total_seconds() / 3600)
            self.hours_for_the_day = round(total_duration.total_seconds() / 3600, 2)
        
        if self.jobs.exists():
            travel_time_subtract = 0

            # Calculate the time from initial_leave_time to the first job's arrival
            first_job_arrival_time = self.jobs.first().activity_arrive_time
            if self.initial_leave_time and first_job_arrival_time:
                travel_to_first_job = datetime.combine(datetime.min, first_job_arrival_time) - datetime.combine(datetime.min, self.initial_leave_time)
                travel_time_subtract += travel_to_first_job.total_seconds() / 3600  # Convert to hours

            # Calculate the time between jobs
            job_times = list(self.jobs.values_list('activity_arrive_time', 'activity_leave_time'))
            
            for i in range(1, len(job_times)):
                previous_leave_time = job_times[i-1][1]
                current_arrive_time = job_times[i][0]
                
                travel_gap = datetime.combine(datetime.min, current_arrive_time) - datetime.combine(datetime.min, previous_leave_time)
                travel_time_subtract += travel_gap.total_seconds() / 3600  # Convert to hours

            # Calculate the time from the last job to final_arrive_time
            last_job_leave_time = self.jobs.last().activity_leave_time
            if self.final_arrive_time and last_job_leave_time:
                travel_from_last_job = datetime.combine(datetime.min, self.final_arrive_time) - datetime.combine(datetime.min, last_job_leave_time)
                travel_time_subtract += travel_from_last_job.total_seconds() / 3600  # Convert to hours

            print("Total Travel Time (subtract):", travel_time_subtract)
            self.travel_time_subtract = round(travel_time_subtract, 2)
        
        if self.hours_for_the_day and self.travel_time_subtract:
            self.hours_to_be_paid = round(self.hours_for_the_day - self.travel_time_subtract, 2)

    def calculate_mileage(self):
        """Aggregate mileage from all related jobs."""
        if self.initial_mileage is not None and self.final_mileage is not None:
            self.total_miles = self.final_mileage - self.initial_mileage

            if self.jobs.exists():
                miles_to_be_paid = 0
                
                for job in self.jobs.all():
                    job_miles = job.calculate_job_miles()
                    if job_miles is not None:
                        miles_to_be_paid += job_miles

                self.travel_miles_subtract = self.total_miles - miles_to_be_paid
                self.miles_to_be_paid = miles_to_be_paid

    def save(self, *args, **kwargs):
        # Save the instance first to generate a primary key
        if not self.pk:
            super(TimeEntry, self).save(*args, **kwargs)
        if self.jobs.exists():
            # Get the last job related to this time entry
            last_job = self.jobs.last()
            # Set the activity_end_mileage to the last job's activity_end_mileage
            self.activity_end_mileage = last_job.activity_end_mileage
        # Now that the instance has a primary key, calculate hours and mileage
        self.calculate_hours()
        self.calculate_mileage()

        # Save the instance again with updated calculated fields
        super(TimeEntry, self).save(*args, **kwargs)
        
    def calculate_total_hours(self):
        if self.start_time and self.end_time:
            work_duration = datetime.combine(datetime.min, self.end_time) - datetime.combine(datetime.min, self.start_time)
            total_hours = work_duration.total_seconds() / 3600  # Convert to hours
            return round(total_hours, 2)
        return 0  # Return 0 if start_time or end_time is not provided

class Job(models.Model):
    LABOR_CODE_CHOICES = [
        ('1', 'Project Manager/P.E.'),
        ('2', 'Senior Engineer/P.E.'),
        ('3', 'Project Engineer'),
        ('4', 'Laboratory Manager'),
        ('5', 'Laboratory Technician'),
        ('6', 'Field Engineer'),
        ('7', 'Field Technician Level I'),
        ('8', 'Field Technician Level II'),
        ('9', 'CWI'),
        ('10', 'Report/ Documentation Preparation'),
        ('11', 'Report/ Document Quality Review'),
        ('12', 'Concrete/ Sample Collection Pick-Up'),
        ('13', 'Concrete Lab'),
        ('14', 'Concrete Coring'),
        ('15', 'Windsor Probe/Pin'),
        ('16', 'Schmidt Hammer'),
        ('17', 'Ground Penetrating Radar'),
        ('18', 'Floor Flatness'),
        ('19', 'CAD Drawing'),
        ('20', 'Administration'),
        ('21', 'Marketing'),
        ('22', 'Clerical Support'),
        ('23', 'Training'),
        ('24', 'School'),
        ('25', 'Moisture Content'),
        ('26', 'Particle Size Analysis'),
        ('27', 'Hydrometer'),
        ('28', 'Atterberg Limits'),
        ('29', 'Specific Gravity'),
        ('30', 'Organic Content'),
        ('31', 'Unit Weight'),
        ('32', 'Density, Soil Particle'),
        ('33', 'Fractional Organic Carbon'),
        ('34', 'Hydraulic Conductivity'),
        ('35', 'Standard Proctor 4" Mold'),
        ('36', 'Standard Proctor 6" Mold'),
        ('37', 'Modified Proctor 4" Mold'),
        ('38', 'Modified Proctor 6" Mold'),
        ('39', 'Unconsolidated Triaxle Shear Test'),
        ('40', 'Consolidated Triaxle Shear Test'),
        ('41', 'Unconfined Compression'),
        ('42', 'One Dimensional Consolidation'),
        ('43', 'Asphalt Extraction Test'),
        ('44', 'Gyratory Compaction'),
        ('45', 'Asphalt Bulk Specific Gravity'),
        ('46', 'Asphalt Apparent Specific Gravity'),
        ('47', 'pH'),
        ('48', 'Other'),
    ]
    
    time_entry = models.ForeignKey(TimeEntry, related_name='jobs', on_delete=models.CASCADE)
    activity_start_mileage = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    activity_arrive_time = models.TimeField()
    activity_leave_time = models.TimeField()
    activity_end_mileage = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    labor_code = models.CharField(max_length=2, choices=LABOR_CODE_CHOICES)
    description = models.TextField()
    
    @property
    def labor_code_description(self):
        return dict(self.LABOR_CODE_CHOICES).get(self.labor_code, "Unknown Code")
    
    def calculate_job_miles(self):
        if self.activity_start_mileage is not None and self.activity_end_mileage is not None:
            return self.activity_end_mileage - self.activity_start_mileage
        return None
    
    def __str__(self):
        return f"Job at {self.activity_arrive_time} - {self.activity_leave_time}"
