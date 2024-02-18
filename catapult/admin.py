from django.contrib import admin

from catapult.models import Experiment, File, FolderWatchingLocation


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