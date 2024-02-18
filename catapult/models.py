from django.db import models

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
    experiment_name = models.CharField(max_length=100, blank=False, null=False, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    vendor_choices = [
        (".wiff", "AB Sciex (.wiff)"),
        (".raw", "Thermo Fisher (.raw)"),
        (".d", "Bruker (.d)"),
        (".mzML", "Generic (.mzML)"),
        (".dia", "DIA-NN (.dia)"),
    ]
    vendor = models.CharField(max_length=5, choices=vendor_choices, blank=False, null=False)
    sample_count = models.IntegerField(blank=False, null=False)


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

    class Meta:
        ordering = ["id"]
        app_label = "catapult"

    def __str__(self):
        return f"{self.file_path}"

    def __repr__(self):
        return f"{self.file_path}"

    def delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)

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
    analysis_name = models.CharField(max_length=100, blank=False, null=False, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE, related_name="analysis")
    analysis_type = models.CharField(max_length=100, blank=False, null=False)
    start_time = models.DateTimeField(blank=True, null=True)
    stop_time = models.DateTimeField(blank=True, null=True)
    processing = models.BooleanField(default=False)
    completed = models.BooleanField(default=False)
    log = models.TextField(blank=True, null=True)
    fasta_file = models.TextField(blank=True, null=True)
    commands = models.TextField(blank=True, null=True)
    output_folder = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["id"]
        app_label = "catapult"

    def __str__(self):
        return f"{self.analysis_name}"

    def __repr__(self):
        return f"{self.analysis_name}"

    def delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)



