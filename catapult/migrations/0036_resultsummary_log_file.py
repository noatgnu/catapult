# Generated by Django 5.0.6 on 2024-07-15 13:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catapult', '0035_analysis_total_files_resultsummary'),
    ]

    operations = [
        migrations.AddField(
            model_name='resultsummary',
            name='log_file',
            field=models.TextField(blank=True, null=True),
        ),
    ]
