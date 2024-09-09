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

    def __str__(self):
        return f"{self.first_name} {self.last_name}"  # Display full name