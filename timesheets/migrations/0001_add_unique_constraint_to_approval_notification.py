from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('timesheets', '0001_initial'),  # Replace with your last migration name
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='approvalnotification',
            unique_together={('time_entry_approval', 'notification_type', 'recipient')},
        ),
    ]
