# Generated by Django 5.0.2 on 2024-02-21 23:01

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('catapult', '0018_uploadedfile'),
    ]

    operations = [
        migrations.DeleteModel(
            name='UserAPIKey',
        ),
    ]