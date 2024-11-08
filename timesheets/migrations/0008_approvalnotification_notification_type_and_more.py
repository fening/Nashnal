# Generated by Django 5.1 on 2024-11-06 15:02

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('timesheets', '0007_alter_approvalnotification_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='approvalnotification',
            name='notification_type',
            field=models.CharField(choices=[('submission', 'Timesheet Submitted'), ('first_approval', 'First Approval'), ('approval', 'Timesheet Approved'), ('rejection', 'Timesheet Rejected'), ('review_needed', 'Review Needed')], default='submission', max_length=20),
        ),
        migrations.AlterField(
            model_name='approvalnotification',
            name='time_entry_approval',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='timesheets.timeentryapproval'),
            preserve_default=False,
        ),
    ]