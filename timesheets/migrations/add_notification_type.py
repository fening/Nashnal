from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('timesheets', '0007_alter_approvalnotification_options_and_more'),  # Replace with your actual last migration name
    ]

    operations = [
        migrations.AddField(
            model_name='approvalnotification',
            name='notification_type',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('submission', 'Timesheet Submitted'),
                    ('first_approval', 'First Approval'),
                    ('approval', 'Timesheet Approved'),
                    ('rejection', 'Timesheet Rejected'),
                    ('review_needed', 'Review Needed'),
                ],
                default='submission',
            ),
        ),
    ]
