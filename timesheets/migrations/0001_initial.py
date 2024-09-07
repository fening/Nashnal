# Generated by Django 5.1 on 2024-08-20 18:46

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
            name='ClientJob',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('job_number', models.CharField(max_length=255)),
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
                ('activity_arrive_time', models.TimeField(blank=True, null=True)),
                ('activity_leave_time', models.TimeField(blank=True, null=True)),
                ('hours_on_site', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('hours_for_the_day', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('travel_time_subtract', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('hours_to_be_paid', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
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
                ('labor_code', models.CharField(choices=[('1', 'Project Manager/P.E.'), ('2', 'Senior Engineer/P.E.'), ('3', 'Project Engineer'), ('4', 'Laboratory Manager'), ('5', 'Laboratory Technician'), ('6', 'Field Engineer'), ('7', 'Field Technician Level I'), ('8', 'Field Technician Level II'), ('9', 'CWI'), ('10', 'Report/ Documentation Preparation'), ('11', 'Report/ Document Quality Review'), ('12', 'Concrete/ Sample Collection Pick-Up'), ('13', 'Concrete Lab'), ('14', 'Concrete Coring'), ('15', 'Windsor Probe/Pin'), ('16', 'Schmidt Hammer'), ('17', 'Ground Penetrating Radar'), ('18', 'Floor Flatness'), ('19', 'CAD Drawing'), ('20', 'Administration'), ('21', 'Marketing'), ('22', 'Clerical Support'), ('23', 'Training'), ('24', 'School'), ('25', 'Moisture Content'), ('26', 'Particle Size Analysis'), ('27', 'Hydrometer'), ('28', 'Atterberg Limits'), ('29', 'Specific Gravity'), ('30', 'Organic Content'), ('31', 'Unit Weight'), ('32', 'Density, Soil Particle'), ('33', 'Fractional Organic Carbon'), ('34', 'Hydraulic Conductivity'), ('35', 'Standard Proctor 4" Mold'), ('36', 'Standard Proctor 6" Mold'), ('37', 'Modified Proctor 4" Mold'), ('38', 'Modified Proctor 6" Mold'), ('39', 'Unconsolidated Triaxle Shear Test'), ('40', 'Consolidated Triaxle Shear Test'), ('41', 'Unconfined Compression'), ('42', 'One Dimensional Consolidation'), ('43', 'Asphalt Extraction Test'), ('44', 'Gyratory Compaction'), ('45', 'Asphalt Bulk Specific Gravity'), ('46', 'Asphalt Apparent Specific Gravity'), ('47', 'pH'), ('48', 'Other')], max_length=2)),
                ('description', models.TextField()),
                ('time_entry', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='jobs', to='timesheets.timeentry')),
            ],
        ),
    ]
