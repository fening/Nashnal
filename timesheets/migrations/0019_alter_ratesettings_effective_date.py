# Generated by Django 5.1 on 2024-12-03 19:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('timesheets', '0018_ratesettings'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ratesettings',
            name='effective_date',
            field=models.DateField(help_text='Date these rates become effective'),
        ),
    ]