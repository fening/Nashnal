# Generated by Django 5.1 on 2024-11-05 19:53

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('timesheets', '0006_alter_timeentryapproval_options_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='approvalnotification',
            options={},
        ),
        migrations.RemoveField(
            model_name='approvalnotification',
            name='notification_type',
        ),
        migrations.RemoveField(
            model_name='approvalnotification',
            name='time_entry',
        ),
        migrations.AddField(
            model_name='approvalnotification',
            name='time_entry_approval',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='timesheets.timeentryapproval'),
        ),
        migrations.AlterField(
            model_name='timeentryapproval',
            name='first_reviewed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='first_reviews', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='timeentryapproval',
            name='first_reviewer_comments',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='timeentryapproval',
            name='second_reviewed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='second_reviews', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='timeentryapproval',
            name='second_reviewer_comments',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='timeentryapproval',
            name='submitter_comments',
            field=models.TextField(blank=True, null=True),
        ),
    ]