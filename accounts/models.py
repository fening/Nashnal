from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    FIELD_TECHNICIAN = 'Field Technician'
    LAB_TECHNICIAN = 'Lab Technician'
    OFFICE_SUPPORT = 'Office Support'
    OPERATIONS_SUPPORT = 'Operations Support'
    SUPERVISOR = 'Supervisor'
    
    ROLE_CHOICES = [
        (FIELD_TECHNICIAN, 'Field Technician'),
        (LAB_TECHNICIAN, 'Lab Technician'),
        (OFFICE_SUPPORT, 'Office Support'),
        (OPERATIONS_SUPPORT, 'Operations Support'),
        (SUPERVISOR, 'Supervisor'),
    ]

    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default=FIELD_TECHNICIAN)
    supervisor = models.ForeignKey('self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='supervisees'
    )
    second_approver = models.ForeignKey('self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='second_approval_employees',
        help_text="Second approver for timesheet entries"
    )
    distance_office = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        help_text="Distance in miles", 
        null=True, 
        blank=True
    )
    time_office = models.IntegerField(
        help_text="Travel time to office in minutes", 
        null=True, 
        blank=True
    )

    def __str__(self):
        return f"{self.get_full_name()} ({self.username})"

    class Meta:
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['role'], name='user_role_idx'),
            models.Index(fields=['supervisor'], name='user_supervisor_idx'),
            models.Index(fields=['second_approver'], name='user_second_approver_idx'),
        ]
        
    def save(self, *args, **kwargs):
        # If user is a Supervisor, they don't need a supervisor
        if self.role == self.SUPERVISOR:
            self.supervisor = None
        super().save(*args, **kwargs)

    @property
    def can_first_approve(self):
        """Check if user can do first approvals"""
        return self.role == self.SUPERVISOR or self.is_superuser

    @property
    def can_second_approve(self):
        """Check if user can do second approvals"""
        return self.has_perm('timesheets.can_second_approve') or self.is_superuser

    @property
    def get_second_approver(self):
        """Get the appropriate second approver"""
        if self.second_approver:
            return self.second_approver
        elif self.supervisor and self.supervisor.supervisor:
            return self.supervisor.supervisor
        return None

    class Meta:
        permissions = [
            ("can_view_all_employees", "Can view all employees"),
            ("can_manage_employees", "Can manage employees"),
        ]
    
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import uuid

User = get_user_model()

class RegistrationInvitation(models.Model):
    email = models.EmailField(unique=True)
    token = models.UUIDField(default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    # Pre-filled employee data
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    role = models.CharField(max_length=50, choices=User.ROLE_CHOICES)
    supervisor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='invited_employees')
    distance_office = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    time_office = models.IntegerField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            # Set expiration to 7 days from creation
            self.expires_at = timezone.now() + timedelta(hours=1)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return not self.used and not self.is_expired

    def __str__(self):
        return f"Invitation for {self.email} ({self.token})"
    
    