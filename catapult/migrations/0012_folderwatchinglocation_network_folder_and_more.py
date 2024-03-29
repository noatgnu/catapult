# Generated by Django 5.0.2 on 2024-02-21 10:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catapult', '0011_alter_analysis_options_alter_analysis_analysis_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='folderwatchinglocation',
            name='network_folder',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='analysis',
            name='commands',
            field=models.TextField(blank=True, default='--min-fr-mz 200 --max-fr-mz 1800 --cut K*,R* --missed-cleavages 2 --min-pep-len 7 --max-pep-len 30 --min-pr-mz 300 --max-pr-mz 1800 --min-pr-charge 1 --max-pr-charge 4 --unimod4 --var-mods 1 --var-mod UniMod:35,15.994915,M --mass-acc 20 --mass-acc-ms1 20 --individual-mass-acc --individual-windows --reanalyse --smart-profiling --peak-center --no-ifs-removal', null=True),
        ),
    ]
