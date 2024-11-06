# Generated by Django 5.1 on 2024-11-05 10:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_customuser_distance_office_customuser_time_office'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='role',
            field=models.CharField(choices=[('Field Technician', 'Field Technician'), ('Lab Technician', 'Lab Technician'), ('Office Support', 'Office Support'), ('Operations Support', 'Operations Support'), ('Supervisor', 'Supervisor')], default='Field Technician', max_length=50),
        ),
    ]
