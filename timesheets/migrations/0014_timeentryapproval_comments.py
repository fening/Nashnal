# Generated by Django 5.1 on 2024-11-27 20:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('timesheets', '0013_timeentry_attachment_timeentry_attachment_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='timeentryapproval',
            name='comments',
            field=models.TextField(blank=True, null=True),
        ),
    ]