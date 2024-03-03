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
    ready = serializers.SerializerMethodField()

    def get_ready(self, obj):
        return obj.ready()

    class Meta:
        model = Analysis
        fields = [f.name for f in Analysis._meta.fields if f.name not in ["id"]] + ['id', 'ready']


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
    current_tasks = serializers.SerializerMethodField()

    def get_current_tasks(self, obj):
        return CeleryTaskSerializer(obj.tasks.all(), many=True).data

    class Meta:
        model = CeleryWorker
        fields = ["id", "worker_hostname", "worker_os", "worker_status", "current_tasks"]