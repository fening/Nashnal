# Generated by Django 5.1 on 2024-11-26 11:13

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('timesheets', '0012_jobdetails_client_number_jobdetails_project_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='timeentry',
            name='attachment',
            field=models.FileField(blank=True, help_text='Allowed file types: PDF, DOC, DOCX, JPG, PNG', null=True, upload_to='timesheet_attachments/%Y/%m/%d/', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'])]),
        ),
        migrations.AddField(
            model_name='timeentry',
            name='attachment_name',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
