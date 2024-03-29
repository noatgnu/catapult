# Generated by Django 5.0.2 on 2024-02-18 19:12

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Experiment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('experiment_name', models.CharField(db_index=True, max_length=100, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('processing_status', models.BooleanField(default=False)),
                ('completed', models.BooleanField(default=False)),
                ('vendor', models.CharField(choices=[('.wiff', 'AB Sciex (.wiff)'), ('.raw', 'Thermo Fisher (.raw)'), ('.d', 'Bruker (.d)'), ('.mzML', 'Generic (.mzML)'), ('.dia', 'DIA-NN (.dia)')], max_length=5)),
            ],
            options={
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='FolderWatchingLocation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('folder_path', models.TextField(db_index=True, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='File',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file_path', models.TextField(db_index=True, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_processed', models.BooleanField(default=False)),
                ('ready_for_processing', models.BooleanField(default=False)),
                ('experiment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='catapult.experiment')),
                ('folder_watching_location', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='catapult.folderwatchinglocation')),
            ],
            options={
                'ordering': ['id'],
            },
        ),
    ]
