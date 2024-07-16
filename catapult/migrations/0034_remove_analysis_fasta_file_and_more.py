# Generated by Django 5.0.6 on 2024-07-12 11:14

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catapult', '0033_remove_catapultrunconfig_analysis_analysis_config_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name='analysis',
            name='fasta_file',
        ),
        migrations.RemoveField(
            model_name='analysis',
            name='spectral_library',
        ),
        migrations.AddField(
            model_name='catapultrunconfig',
            name='fasta_ready',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='catapultrunconfig',
            name='fasta_required',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='catapultrunconfig',
            name='spectral_library_ready',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='catapultrunconfig',
            name='spectral_library_required',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='FastaFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('file_path', models.TextField()),
                ('size', models.BigIntegerField()),
                ('ready', models.BooleanField(default=False)),
                ('config', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='fasta', to='catapult.catapultrunconfig')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='SpectralLibrary',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('file_path', models.TextField()),
                ('size', models.BigIntegerField()),
                ('ready', models.BooleanField(default=False)),
                ('config', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='spectral_library', to='catapult.catapultrunconfig')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['id'],
            },
        ),
    ]