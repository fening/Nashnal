# Generated by Django 5.1 on 2024-09-14 17:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('timesheets', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='laborcode',
            name='labor_code_description',
            field=models.CharField(max_length=255),
        ),
    ]
