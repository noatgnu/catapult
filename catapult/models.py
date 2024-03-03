import os
import subprocess
from datetime import datetime

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.models import User
from django.db import models
from rest_framework_api_key.crypto import KeyGenerator
from rest_framework_api_key.models import BaseAPIKeyManager, AbstractAPIKey
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

from django.conf import settings
from catapult_backend.settings import DIANN_PATH, CPU_COUNT, DEFAULT_DIANN_PARAMS, DEFAULT_MSCONVERT_PARAMS, \
    MSCONVERT_PATH


# Create your models here.


class FolderWatchingLocation(models.Model):
    """A data model for storing the folder watching location data with the following column:
    - folder_path: the path of the folder to be watched
    - created_at: the date and time the folder watching location was created
    - updated_at: the date and time the folder watching location was last updated
    """
    folder_path = models.TextField(blank=False, null=False, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    network_folder = models.BooleanField(default=False)
    ignore_term = models.TextField(blank=True, null=True, default="DONOTPROCESS")
    extensions = models.TextField(blank=True, null=True, default=".raw,.wiff,.d,.mzML,.dia")

    class Meta:
        ordering = ["id"]
        app_label = "catapult"

    def __str__(self):
        return f"{self.folder_path}"

    def __repr__(self):
        return f"{self.folder_path}"

    def delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)


class Experiment(models.Model):
    """A data model for storing the experiment data with the following column:
    - experiment_name: the name of the experiment
    - created_at: the date and time the experiment was created
    - updated_at: the date and time the experiment was last updated
    - vendor: choice of the vendor the experiment belongs to
    - sample_count: the number of samples in the experiment
    """
    experiment_name = models.CharField(max_length=200, blank=False, null=False, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    vendor_choices = [
        (".wiff", "AB Sciex (.wiff)"),
        (".raw", "Thermo Fisher (.raw)"),
        (".d", "Bruker (.d)"),
        (".mzML", "Generic (.mzML)"),
        (".dia", "DIA-NN (.dia)"),
    ]
    vendor = models.CharField(max_length=5, choices=vendor_choices, blank=True, null=True)
    sample_count = models.IntegerField(blank=True, null=True)

    class Meta:
        ordering = ["id"]
        app_label = "catapult"

    def __str__(self):
        return f"{self.experiment_name}"

    def __repr__(self):
        return f"{self.experiment_name}"

    def delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)

    def ready_for_processing(self):
        return len(self.files.filter(ready_for_processing=True)) == self.sample_count

    def is_being_processed(self):
        return len(self.analysis.filter(processing=True)) > 0

    def has_at_least_completed_analysis(self):
        return len(self.analysis.filter(completed=True)) > 0

    def windows_only_vendor(self):
        return self.vendor not in [".d", ".mzML", ".dia"]


class File(models.Model):
    """A data model for storing the file data with the following column:
    - file_path: the path of the file
    - created_at: the date and time the file was created
    - updated_at: the date and time the file was last updated
    - folder_watching_location: the folder watching location the file belongs to
    - is_processed: a boolean value indicating if the file has been processed
    - ready_for_processing: a boolean value indicating if the file is ready for processing
    - experiment: the experiment the file belongs to
    - size: the size of the file
    """
    file_path = models.TextField(blank=False, null=False, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    folder_watching_location = models.ForeignKey(FolderWatchingLocation, on_delete=models.CASCADE, related_name="files")
    ready_for_processing = models.BooleanField(default=False)
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE, related_name="files")
    size = models.BigIntegerField(blank=False, null=False)
    processing = models.BooleanField(default=False)

    class Meta:
        ordering = ["id"]
        app_label = "catapult"

    def __str__(self):
        return f"{self.file_path}"

    def __repr__(self):
        return f"{self.file_path}"

    def delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)

    def get_path(self):
        return os.path.join(self.folder_watching_location.folder_path, self.file_path)


class MSConvert(models.Model):
    """
    A data model for storing the msconvert data with the following column:
    - created_at: the date and time the msconvert was created
    - updated_at: the date and time the msconvert was last updated
    - experiment: the experiment the msconvert belongs to
    - input_file: the input file for the msconvert
    - output_folder: the output folder for the msconvert
    - processing: a boolean status of the msconvert indicating if it is being processed
    - completed: a boolean value indicating if the msconvert has been completed
    - log: the log of the msconvert
    - commands: the commands used for the msconvert
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    experiment = models.ForeignKey(Experiment, on_delete=models.SET_NULL, null=True, blank=True, related_name="msconvert")
    file = models.ForeignKey(File, on_delete=models.CASCADE, related_name="msconvert")
    output_folder = models.TextField(blank=False, null=False)
    processing = models.BooleanField(default=False)
    completed = models.BooleanField(default=False)
    log = models.TextField(blank=True, null=True)
    commands = models.TextField(blank=True, null=True)

    def start_msconvert(self, task_id="", hostname=""):
        commands = []
        converted_folder = os.path.join(self.output_folder, "converted")
        os.makedirs(converted_folder, exist_ok=True)
        commands.append(MSCONVERT_PATH)
        commands.append(self.file.get_path())
        commands.append("-o")
        commands.append(converted_folder)
        commands.extend(self.commands.split(" "))
        process = subprocess.Popen(commands, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        channel_layer = get_channel_layer()
        self.processing = True
        self.completed = False
        self.save()
        while process.poll() is None:
            output = process.stdout.readline()
            if output:
                output_line = output.decode("utf-8")
                async_to_sync(channel_layer.group_send)(
                    "analysis_log", {
                        "type": "log_message",
                        "message": {
                            "task_id": task_id,
                            "log": output_line,
                            "hostname": hostname,
                            "timestamp": f"{datetime.now().timestamp()}"
                        },
                    }
                )
        self.processing = False
        self.completed = True
        self.save()
        return self


class Analysis(models.Model):
    """A data model for storing analysis with the following column:
    - analysis_name: the name of the analysis
    - created_at: the date and time the analysis was created
    - updated_at: the date and time the analysis was last updated
    - experiment: the experiment the analysis belongs to
    - analysis_type: the type of analysis
    - processing: a boolean status of the analysis indicating if it is being processed
    - completed: a boolean value indicating if the analysis has been completed
    - log: the log of the analysis
    - commands: the commands used for the analysis
    """
    analysis_name = models.CharField(max_length=200, blank=False, null=False, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE, related_name="analysis")

    analysis_type_choices = [
        ("diann-create", "DIA-NN Search (create spectral library)"),
        ("diann-spectral", "DIA-NN Search (with spectral library)"),
    ]

    analysis_type = models.CharField(max_length=20, choices=analysis_type_choices, blank=False, null=False)
    start_time = models.DateTimeField(blank=True, null=True)
    stop_time = models.DateTimeField(blank=True, null=True)
    processing = models.BooleanField(default=False)
    completed = models.BooleanField(default=False)
    log = models.TextField(blank=True, null=True)
    fasta_file = models.TextField(blank=True, null=True, default="")
    spectral_library = models.TextField(blank=True, null=True)
    commands = models.TextField(blank=True, null=True, default=DEFAULT_DIANN_PARAMS)
    output_folder = models.TextField(blank=True, null=True)
    default_analysis = models.BooleanField(default=False)
    generating_quant = models.ManyToManyField("File", related_name="quant_files", blank=True)
    generated_quant = models.ManyToManyField("File", related_name="generated_quant_files", blank=True)

    class Meta:
        ordering = ["id"]
        app_label = "catapult"
        verbose_name_plural = "Analyses"

    def __str__(self):
        return f"{self.analysis_name}"

    def __repr__(self):
        return f"{self.analysis_name}"

    def delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)

    def start_analysis(self, task_id="", hostname=""):
        commands = []
        if self.analysis_type.startswith("diann"):
            commands.append(DIANN_PATH)
            commands.append("--use-quant")
            for file in self.experiment.files.filter(ready_for_processing=True):
                commands.append("--f")
                commands.append(file.get_path())
            commands.append("--threads")
            commands.append(CPU_COUNT)
            commands.append("--lib")
            if self.analysis_type == "diann-spectral":
                commands.append(self.spectral_library)
            if self.fasta_file != "":
                commands.append("--fasta")
                commands.append(self.fasta_file)
            commands.append("--temp")
            commands.append(os.path.join(self.output_folder, "temp"))
            if self.analysis_type == "diann-create":
                commands.append("--out-lib")
                commands.append(os.path.join(self.output_folder, "report-lib.tsv"))
                commands.append("--gen-spec-lib")
                commands.append("--predictor")

        commands.extend(self.commands.split(" "))
        os.makedirs(os.path.join(self.output_folder, "temp"), exist_ok=True)
        self.processing = True
        self.completed = False
        self.start_time = datetime.now()
        self.save()
        # run the commands and stream the output to websocket channel
        process = subprocess.Popen(commands, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        channel_layer = get_channel_layer()
        while process.poll() is None:
            output = process.stdout.readline()
            if output:
                output_line = output.decode("utf-8")
                async_to_sync(channel_layer.group_send)(
                    "analysis_log", {
                        "type": "log_message",
                        "message": {
                            "task_id": task_id,
                            "log": output_line,
                            "hostname": hostname,
                            "timestamp": f"{datetime.now().timestamp()}",
                        },
                    }
                )


        #subprocess.run(commands, shell=True, check=True)
        self.stop_time = datetime.now()
        self.processing = False
        self.completed = True
        self.save()
        return self

    def create_quant_file(self, task_id="", hostname=""):
        commands = []
        files = []
        if self.analysis_type.startswith("diann"):
            commands.append(DIANN_PATH)
            commands.append("--use-quant")
            for file in self.experiment.files.filter(ready_for_processing=True):
                commands.append("--f")
                commands.append(file.get_path())
            commands.append("--threads")
            commands.append(CPU_COUNT)
            commands.append("--lib")
            if self.analysis_type == "diann-spectral":
                commands.append(self.spectral_library)
            if self.fasta_file != "":
                commands.append("--fasta")
                commands.append(self.fasta_file)
            commands.append("--temp")
            commands.append(os.path.join(self.output_folder, "temp"))
            if self.analysis_type == "diann-create":
                commands.append("--out-lib")
                commands.append(os.path.join(self.output_folder, "report-lib.tsv"))
                commands.append("--gen-spec-lib")
                commands.append("--predictor")
        if len(commands) > 0:
            commands.extend(self.commands.split(" "))
            os.makedirs(os.path.join(self.output_folder, "temp"), exist_ok=True)
            process = subprocess.Popen(commands, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            channel_layer = get_channel_layer()
            while process.poll() is None:
                output = process.stdout.readline()
                if output:
                    output_line = output.decode("utf-8")
                    async_to_sync(channel_layer.group_send)(
                        "analysis_log", {
                            "type": "log_message",
                            "message": {
                                "task_id": task_id,
                                "log": output_line,
                                "hostname": hostname,
                                "timestamp": f"{datetime.now().timestamp()}"
                            },
                        }
                    )
            self.generated_quant.add(*files)
            self.save()
        else:
            raise ValueError("Analysis type not supported for quant file generation")

    def ready(self):
        if self.experiment.ready_for_processing():
            return True
        return False


    def save(
            self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        super().save(force_insert, force_update, using, update_fields)
        return self


class UserAPIKeyManager(BaseAPIKeyManager):
    key_generator = KeyGenerator(prefix_length=8, secret_key_length=128)


class UserAPIKey(AbstractAPIKey):
    """A data model for storing the user API key data with the following column:
    - user: the user the API key belongs to
    - api_key: the API key
    - created_at: the date and time the API key was created
    - updated_at: the date and time the API key was last updated
    """
    objects = UserAPIKeyManager()

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="api_keys")
    api_key = models.CharField(max_length=40, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class UploadedFile(models.Model):
    """
    A data model for storing the uploaded file data with the following column:
    - file: the file
    - created_at: the date and time the file was created
    - updated_at: the date and time the file was last updated
    - file_type: the type of file
    - user: the user that uploaded the file
    """
    file = models.FileField(upload_to="upload/")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    file_type_choices = [
        ("fasta", "Fasta"),
        ("spectral_library", "Spectral Library"),
    ]
    file_type = models.CharField(max_length=20, choices=file_type_choices, blank=False, null=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        ordering = ["id"]
        app_label = "catapult"

    def __str__(self):
        return f"{self.file.name}"

    def __repr__(self):
        return f"{self.file.name}"

    def delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)


class CeleryTask(models.Model):
    """
    A data model for storing the celery task data with the following column:
    - task_id: the task id
    - created_at: the date and time the task was created
    - updated_at: the date and time the task was last updated
    - task_name: the name of the task
    - user: the user that created the task
    - task_status: the status of the task
    - analysis: the analysis the task belongs to
    """
    task_id = models.CharField(max_length=200, blank=False, null=False, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    task_name = models.CharField(max_length=200, blank=False, null=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    status = models.CharField(max_length=20, blank=False, null=False)
    analysis = models.ForeignKey(Analysis, on_delete=models.CASCADE, blank=True, null=True, related_name="tasks")
    analysis_params = models.JSONField(blank=True, null=True)
    worker = models.ForeignKey("CeleryWorker", on_delete=models.SET_NULL, blank=True, null=True, related_name="tasks")

    class Meta:
        ordering = ["id"]
        app_label = "catapult"

    def __str__(self):
        return f"{self.task_name}"

    def __repr__(self):
        return f"{self.task_name}"

    def delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)

class CeleryWorker(models.Model):
    """
    A data model for registering the celery worker with the following column:
    - created_at: the date and time the worker was registered
    - updated_at: the date and time the worker was last updated
    - worker_name: the name of the worker
    - worker_params: the parameters of the worker
    - worker_status: the status of the worker
    - worker_hostname: the hostname of the worker
    - folder_path_translations: a dictionary of the folder path used and its translated paths from the worker
    - worker_os: the operating system of the worker
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    worker_name = models.CharField(max_length=200, blank=False, null=False, unique=True, db_index=True)
    worker_params = models.JSONField(blank=True, null=True)
    worker_status = models.CharField(max_length=20, blank=False, null=False)
    worker_hostname = models.CharField(max_length=200, blank=False, null=False, unique=True, db_index=True)
    folder_path_translations = models.JSONField(blank=True, null=True)
    worker_os = models.CharField(max_length=20, blank=True, null=True)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)
