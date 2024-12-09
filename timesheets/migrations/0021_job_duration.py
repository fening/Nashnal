# Generated by Django 5.1 on 2024-12-06 20:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('timesheets', '0020_ratesettings_created_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='duration',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
    ]