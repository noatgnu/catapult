import os

from celery.result import AsyncResult
from django.test import TestCase

# Create your tests here.
from celery.exceptions import Retry
from glob import glob
from unittest.mock import patch, Mock

from catapult.tasks import run_analysis, run_quant
from catapult.models import Experiment, FolderWatchingLocation, Analysis, File
from django.test.utils import override_settings


class TestRunAnalysis(TestCase):

    def test_run_analysis(self):
        experiment = Experiment.objects.create(experiment_name="D:/watch_folder/MRC-Astral", vendor=".raw", sample_count=3)
        folder_watching_location = FolderWatchingLocation.objects.create(folder_path="D:/watch_folder")
        for f in glob("D:/watch_folder/**/*.raw"):
            if f.endswith(".raw"):
                file_path = f.replace(folder_watching_location.folder_path, "")
                File.objects.create(
                    folder_watching_location=folder_watching_location,
                    file_path=file_path,
                    experiment=experiment,
                    size=os.stat(f).st_size,
                    ready_for_processing=True
                )
        analysis = Analysis.objects.create(
            experiment=experiment,
            analysis_type="diann-spectral",
            analysis_name="test analysis",
            output_folder=r"D:\MRC-Astral-Output",
            spectral_library=r"D:\watch_folder\MRC-Astral\20230102_UniprotSwissProt_Human_Cano+Iso - Ox+Ac.predicted.speclib",
            fasta_file=r"D:\watch_folder\MRC-Astral\20230102_UniprotSwissProt_Human_Cano+Iso.fasta")
        task = run_analysis.delay(analysis.id)
