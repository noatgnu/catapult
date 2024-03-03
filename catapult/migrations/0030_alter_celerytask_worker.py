# Generated by Django 5.0.2 on 2024-03-02 19:43

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catapult', '0029_celerytask_worker'),
    ]

    operations = [
        migrations.AlterField(
            model_name='celerytask',
            name='worker',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tasks', to='catapult.celeryworker'),
        ),
    ]
