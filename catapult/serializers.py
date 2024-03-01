from rest_framework import serializers

from catapult.models import Experiment, File, Analysis, FolderWatchingLocation, UserAPIKey, UploadedFile, CeleryTask, \
    CeleryWorker


class ExperimentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experiment
        fields = '__all__'


class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = '__all__'


class AnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Analysis
        fields = '__all__'


class FolderWatchLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = FolderWatchingLocation
        fields = '__all__'


class UserAPIKeySerializer(serializers.ModelSerializer):

    class Meta:
        model = UserAPIKey
        fields = ["id", "name"]


class UploadedFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadedFile
        fields = '__all__'


class CeleryTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = CeleryTask
        fields = '__all__'


class CeleryWorkerSerializer(serializers.ModelSerializer):
    class Meta:
        model = CeleryWorker
        fields = '__all__'