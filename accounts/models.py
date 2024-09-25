from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    TECHNICIAN = 'Technician'
    SUPERVISOR = 'Supervisor'
    ROLE_CHOICES = [
        (TECHNICIAN, 'Technician'),
        (SUPERVISOR, 'Supervisor'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=TECHNICIAN)
    supervisor = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='supervisees')
    distance_office = models.DecimalField(max_digits=8, decimal_places=2, help_text="Distance in miles", null=True, blank=True)
    time_office = models.IntegerField(help_text="Travel time to office in minutes (e.g. 90 for 1 hour 30 minutes)", null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"  # Display full name