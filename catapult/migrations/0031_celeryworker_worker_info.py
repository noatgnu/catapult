# Generated by Django 5.0.2 on 2024-03-04 22:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catapult', '0030_alter_celerytask_worker'),
    ]

    operations = [
        migrations.AddField(
            model_name='celeryworker',
            name='worker_info',
            field=models.JSONField(blank=True, null=True),
        ),
    ]