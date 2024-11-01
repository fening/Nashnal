# Generated by Django 5.1 on 2024-10-31 19:29

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('timesheets', '0003_timeentryapproval_alter_job_options_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ApprovalNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notification_type', models.CharField(choices=[('submission', 'Timesheet Submission'), ('approval', 'Timesheet Approved'), ('rejection', 'Timesheet Rejected')], max_length=20)),
                ('message', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('read', models.BooleanField(default=False)),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
                ('time_entry', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='timesheets.timeentry')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
