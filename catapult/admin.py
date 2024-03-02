from django.contrib import admin

from catapult.models import Experiment, File, FolderWatchingLocation, Analysis, CeleryTask, CeleryWorker, MSConvert


# Register your models here.

@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    pass

@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    pass

@admin.register(FolderWatchingLocation)
class FolderWatchingLocationAdmin(admin.ModelAdmin):
    pass

@admin.register(Analysis)
class AnalysisAdmin(admin.ModelAdmin):
    pass

@admin.register(CeleryTask)
class CeleryTaskAdmin(admin.ModelAdmin):
    pass

@admin.register(CeleryWorker)
class CeleryWorkerAdmin(admin.ModelAdmin):
    pass

@admin.register(MSConvert)
class MSConvertAdmin(admin.ModelAdmin):
    pass