from rest_framework import serializers

from catapult.models import Experiment, File, Analysis, FolderWatchingLocation, UserAPIKey, UploadedFile, CeleryTask, \
    CeleryWorker, ResultSummary, LogRecord, PrecursorReportContent, ProteinGroupReportContent


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
        fields = ["id", "worker_hostname", "worker_os", "worker_status", "current_tasks", "worker_info"]


class ResultSummarySerializer(serializers.ModelSerializer):
    analysis = serializers.SerializerMethodField()
    file = serializers.SerializerMethodField()

    def get_analysis(self, obj: ResultSummary):
        return AnalysisSerializer(obj.analysis).data

    def get_file(self, obj: ResultSummary):
        return FileSerializer(obj.file).data

    class Meta:
        model = ResultSummary
        fields = ['id', 'created_at', 'updated_at', 'analysis', 'file', 'protein_identified', 'precursor_identified', 'stats_file', 'log_file']

class LogRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = LogRecord
        fields = '__all__'

class PrecursorReportContentSerializer(serializers.ModelSerializer):
    analysis = serializers.SerializerMethodField()
    file = serializers.SerializerMethodField()

    def get_analysis(self, obj: PrecursorReportContent):
        return AnalysisSerializer(obj.result_summary.analysis).data

    def get_file(self, obj: PrecursorReportContent):
        return FileSerializer(obj.file).data
    class Meta:
        model = PrecursorReportContent
        fields = ["id", "result_summary", "precursor_id", "gene_names", "protein_group", "proteotypic", "intensity", "analysis", "file"]

class ProteinGroupReportContentSerializer(serializers.ModelSerializer):
    analysis = serializers.SerializerMethodField()
    file = serializers.SerializerMethodField()
    def get_analysis(self, obj: ProteinGroupReportContent):
        return AnalysisSerializer(obj.result_summary.analysis).data
    def get_file(self, obj: ProteinGroupReportContent):
        return FileSerializer(obj.file).data
    class Meta:
        model = ProteinGroupReportContent
        fields = ["id", "result_summary", "protein_group", "gene_names", "intensity", "analysis", "file"]