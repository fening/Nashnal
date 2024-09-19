# Generated by Django 5.1 on 2024-09-14 17:35

import datetime
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='JobDetails',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('job_number', models.CharField(editable=False, max_length=50, unique=True)),
                ('job_description', models.CharField(max_length=255)),
                ('distance_office', models.DecimalField(decimal_places=2, help_text='Distance in miles', max_digits=8)),
                ('time_office', models.IntegerField(help_text='Travel time to office in minutes (e.g. 90 for 1 hour 30 minutes)')),
            ],
            options={
                'verbose_name_plural': 'Job Details',
            },
        ),
        migrations.CreateModel(
            name='LaborCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('laborcode', models.CharField(max_length=10, unique=True)),
                ('labor_code_description', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='TimeEntry',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('date', models.DateField(default=datetime.datetime.today)),
                ('start_location', models.CharField(choices=[('Home', 'Home'), ('Office', 'Office')], default='Home', max_length=10)),
                ('end_location', models.CharField(choices=[('Home', 'Home'), ('Office', 'Office')], default='Home', max_length=10)),
                ('initial_mileage', models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True)),
                ('final_mileage', models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True)),
                ('activity_start_mileage', models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True)),
                ('activity_end_mileage', models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True)),
                ('total_miles', models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True)),
                ('travel_miles_subtract', models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True)),
                ('miles_to_be_paid', models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True)),
                ('initial_leave_time', models.TimeField(blank=True, null=True)),
                ('final_arrive_time', models.TimeField(blank=True, null=True)),
                ('start_time', models.TimeField(blank=True, null=True)),
                ('end_time', models.TimeField(blank=True, null=True)),
                ('hours_on_site', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('hours_for_the_day', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('travel_time_subtract', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('hours_to_be_paid', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('company_vehicle_used', models.BooleanField(choices=[(True, 'Company Vehicle'), (False, 'Personal Vehicle')], default=False, verbose_name='Vehicle Used')),
                ('comments', models.TextField(blank=True, help_text='Any additional notes or comments for this time entry.', null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Job',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('activity_start_mileage', models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True)),
                ('activity_arrive_time', models.TimeField()),
                ('activity_leave_time', models.TimeField()),
                ('activity_end_mileage', models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True)),
                ('job_number', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='timesheets.jobdetails', verbose_name='Job Number')),
                ('labor_code', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='timesheets.laborcode')),
                ('time_entry', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='jobs', to='timesheets.timeentry')),
            ],
        ),
    ]
