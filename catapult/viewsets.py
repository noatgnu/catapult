import json
from datetime import timedelta

from django.db import transaction
from django.db.models import Q, Avg, Count, Case, When, IntegerField
from django.template.smartif import prefix
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework import viewsets, permissions, status
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django_filters.views import FilterMixin

from catapult.filters import CatapultRunConfigFilter
from catapult.models import File, Experiment, Analysis, FolderWatchingLocation, UserAPIKey, UploadedFile, CeleryTask, \
    CeleryWorker, ResultSummary, LogRecord, PrecursorReportContent, ProteinGroupReportContent, CatapultRunConfig
from catapult.serializers import FileSerializer, ExperimentSerializer, AnalysisSerializer, \
    FolderWatchLocationSerializer, UserAPIKeySerializer, UploadedFileSerializer, CeleryTaskSerializer, \
    CeleryWorkerSerializer, ResultSummarySerializer, LogRecordSerializer, PrecursorReportContentSerializer, \
    ProteinGroupReportContentSerializer, CatapultRunConfigSerializer
from catapult.tasks import run_analysis
from catapult.util import blank_diann_config


class FileViewSet(viewsets.ModelViewSet, FilterMixin):
    queryset = File.objects.all()
    serializer_class = FileSerializer
    parser_classes = (JSONParser, FormParser, MultiPartParser)
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    ordering_fields = ['created_at', 'updated_at', 'file_path', 'ready_for_processing', 'id']
    search_fields = ['^file_path']

    def create(self, request, *args, **kwargs):
        file = request.data.get('file')
        if not file:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        file = File.objects.create(file=file)
        return Response(data=FileSerializer(file, many=False, context={"request": request}).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        file = self.get_object()
        payload = request.data
        for p in payload:
            if p != "id":
                if p == "folder_watching_location":
                    if payload[p]:
                        setattr(file, p, FolderWatchingLocation.objects.get(id=payload[p]))
                elif p == "experiment":
                    if payload[p]:
                        setattr(file, p, Experiment.objects.get(id=payload[p]))
                else:
                    setattr(file, p, payload[p])
        file.save()
        return Response(data=FileSerializer(file, many=False, context={"request": request}).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def get_exact_path(self, request):
        file_path = request.data.get("file_path", None)
        create = request.data.get("create", False)
        if not file_path:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        files = File.objects.filter(file_path=file_path)
        if not files:
            if create:
                file = File.objects.create(file_path=file_path)
                return Response(data=FileSerializer(file, many=False, context={"request": request}).data, status=status.HTTP_201_CREATED)
            else:
                return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(data=FileSerializer(files[0], many=False, context={"request": request}).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def get_exact_paths(self, request):
        file_paths = request.data.get("file_paths", None)
        create = request.data.get("create", False)
        if not file_paths:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        files = File.objects.filter(file_path__in=file_paths)
        not_exist_paths = set(file_paths) - set(files.values_list("file_path", flat=True))
        if not_exist_paths:
            if create:
                for path in not_exist_paths:
                    File.objects.create(file_path=path)
                files = File.objects.filter(file_path__in=file_paths)
        return Response(data=FileSerializer(files, many=True, context={"request": request}).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["put"])
    def update_multiple(self, request):
        files = request.data.get("files", None)
        if not files:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            ids = {f["id"]: f for f in files}
            original_files = File.objects.filter(id__in=ids)
            for file in original_files:
                data = ids[file.id]
                for p in data:
                    if p != "id":
                        if p == "folder_watching_location":
                            if data[p]:
                                setattr(file, p, FolderWatchingLocation.objects.get(id=data[p]))
                        elif p == "experiment":
                            if data[p]:
                                setattr(file, p, Experiment.objects.get(id=data[p]))
                        else:
                            setattr(file, p, data[p])
                file.save()
        results = FileSerializer(original_files, many=True, context={"request": request}).data
        return Response(data=results, status=status.HTTP_200_OK)

class ExperimentViewSet(viewsets.ModelViewSet, FilterMixin):
    queryset = Experiment.objects.all()
    serializer_class = ExperimentSerializer
    parser_classes = (JSONParser, FormParser, MultiPartParser)
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [OrderingFilter, DjangoFilterBackend, SearchFilter]
    ordering_fields = ['id', 'created_at', 'updated_at', 'experiment_name', 'vendor', 'processing_status', 'completed']
    search_fields = ['experiment_name']

    def get_queryset(self):
        query = Q()
        vendor = self.request.query_params.get("vendor", None)
        if vendor:
            query &= Q(vendor=vendor)
        processing_status = self.request.query_params.get("processing_status", None)
        if processing_status:
            query &= Q(processing_status=processing_status)
        completed = self.request.query_params.get("completed", None)
        if completed:
            query &= Q(completed=completed)
        return self.queryset.filter(query)

    def create(self, request, *args, **kwargs):
        experiment = Experiment.objects.create(
            experiment_name=request.data["experiment_name"],
            vendor=request.data["vendor"],
            sample_count=request.data["sample_count"],
        )
        data = ExperimentSerializer(experiment, many=False, context={"request": request}).data
        return Response(data=data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        experiment = self.get_object()
        for key in request.data:
            if key != "id":
                setattr(experiment, key, request.data[key])
        experiment.save()
        data = ExperimentSerializer(experiment, many=False, context={"request": request}).data
        return Response(data=data, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        experiment = self.get_object()
        experiment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["put"])
    def update_multiple(self, request):
        experiments = request.data.get("experiments", None)
        if not experiments:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            ids = {e["id"]: e for e in experiments}
            original_experiments = Experiment.objects.filter(id__in=ids)
            for experiment in original_experiments:
                data = ids[experiment.id]
                for key in data:
                    if key != "id":
                        setattr(experiment, key, data[key])
                experiment.save()
        results = ExperimentSerializer(original_experiments, many=True, context={"request": request}).data
        return Response(data=results, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def get_vendor_choices(self, request):
        return Response(
            data=[{"value": v[0], "vendor": v[1]} for v in Experiment.vendor_choices],
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["get"])
    def get_associated_files(self, request, pk=None):
        experiment = self.get_object()
        files = experiment.files.all()
        data = FileSerializer(files, many=True, context={"request": request}).data
        return Response(data=data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def get_associated_analyses(self, request, pk=None):
        experiment = self.get_object()
        analyses = experiment.analysis.all()
        data = AnalysisSerializer(analyses, many=True, context={"request": request}).data
        return Response(data=data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def get_associated_files(self, request, pk=None):
        experiment = self.get_object()
        files = experiment.files.all()
        data = FileSerializer(files, many=True, context={"request": request}).data
        return Response(data=data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def get_result_summaries(self, request, pk=None):
        experiment = self.get_object()
        analyses = experiment.analysis.all()
        result_summary = ResultSummary.objects.filter(analysis__in=analyses)
        return Response(data=ResultSummarySerializer(result_summary, many=True, context={"request": request}).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def get_exact_name(self, request):
        experiment_name = request.data.get("experiment_name", None)
        created = request.data.get("created", False)
        if not experiment_name:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        experiments = Experiment.objects.filter(experiment_name=experiment_name)
        if not experiments:
            if created:
                experiment = Experiment.objects.create(experiment_name=experiment_name)
                return Response(data=ExperimentSerializer(experiment, many=False, context={"request": request}).data, status=status.HTTP_201_CREATED)
            else:
                return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(data=ExperimentSerializer(experiments[0], many=False, context={"request": request}).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def get_exact_names(self, request):
        experiment_names = request.data.get("experiment_names", None)
        created = request.data.get("created", False)
        if not experiment_names:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        experiments = Experiment.objects.filter(experiment_name__in=experiment_names)
        not_exist_names = set(experiment_names) - set(experiments.values_list("experiment_name", flat=True))
        if not_exist_names:
            if created:
                for name in not_exist_names:
                    Experiment.objects.create(experiment_name=name)
                experiments = Experiment.objects.filter(experiment_name__in=experiment_names)
        return Response(data=ExperimentSerializer(experiments, many=True, context={"request": request}).data, status=status.HTTP_200_OK)

class AnalysisViewSet(viewsets.ModelViewSet, FilterMixin):
    queryset = Analysis.objects.all()
    serializer_class = AnalysisSerializer
    parser_classes = (JSONParser, FormParser, MultiPartParser)
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    ordering_fields = ['id', 'created_at', 'updated_at', 'analysis_path', 'experiment', 'analysis_type', 'completed']
    search_fields = ['analysis_path']

    def get_queryset(self):
        queryset = super().get_queryset()
        query = Q()
        min_precursor = self.request.query_params.get("min_precursor", None)
        if min_precursor:
            queryset = queryset.annotate(
                min_precursor_count=Count(
                    Case(
                        When(result_summary__precursor_identified__gte=min_precursor, then=1),
                        output_field=IntegerField()
                    )
                )
            )
            query &= Q(min_precursor_count__gt=0)

        max_precursor = self.request.query_params.get("max_precursor", None)
        if max_precursor:
            queryset = queryset.annotate(
                max_precursor_count=Count(
                    Case(
                        When(result_summary__precursor_identified__lte=max_precursor, then=1),
                        output_field=IntegerField()
                    )
                )
            )
            query &= Q(max_precursor_count__gt=0)

        min_protein = self.request.query_params.get("min_protein", None)
        if min_protein:
            queryset = queryset.annotate(
                min_protein_count=Count(
                    Case(
                        When(result_summary__protein_identified__gte=min_protein, then=1),
                        output_field=IntegerField()
                    )
                )
            )
            query &= Q(min_protein_count__gt=0)

        max_protein = self.request.query_params.get("max_protein", None)
        if max_protein:
            queryset = queryset.annotate(
                max_protein_count=Count(
                    Case(
                        When(result_summary__protein_identified__lte=max_protein, then=1),
                        output_field=IntegerField()
                    )
                )
            )
            query &= Q(max_protein_count__gt=0)

        for i in blank_diann_config:
            config_item = self.request.query_params.get(i, None)
            if config_item:
                if blank_diann_config[i] == "list":
                    config_item = config_item.split(",")
                    for item in config_item:
                        query &= Q(**{f"config__content__{i}__contains": item})

                elif blank_diann_config[i] == "bool":
                    if config_item.lower() == "true":
                        query &= Q(**{f"config__content__{i}": True})
                    elif config_item.lower() == "false":
                        query &= Q(**{f"config__content__{i}": False})
                elif blank_diann_config[i] == "number":
                    query &= Q(**{f"config__content__{i}": config_item})
                else:
                    query &= Q(**{f"config__content__{i}__contains": config_item})

        return queryset.filter(query)

    def create(self, request, *args, **kwargs):
        analysis = Analysis.objects.create(
            analysis_name=request.data["analysis_path"],
            experiment=Experiment.objects.get(id=request.data["experiment"]),
            analysis_type=request.data["analysis_type"],
        )
        if "fasta_file" in request.data:
            analysis.fasta_file = request.data["fasta_file"]
        if "spectral_library" in request.data:
            analysis.spectral_library = request.data["spectral_library"]
        analysis.save()
        data = AnalysisSerializer(analysis, many=False, context={"request": request}).data
        return Response(data=data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        analysis = self.get_object()
        if "analysis_path" in request.data:
            analysis.analysis_path = request.data["analysis_path"]
        analysis.experiment = Experiment.objects.get(id=request.data["experiment"])
        if "analysis_type" in request.data:
            analysis.analysis_type = request.data["analysis_type"]
        if "analysis_name" in request.data:
            analysis.analysis_name = request.data["analysis_name"]
        if "fasta_file" in request.data:
            analysis.fasta_file = request.data["fasta_file"]
        if "spectral_library" in request.data:
            analysis.spectral_library = request.data["spectral_library"]
        if "default_analysis" in request.data:
            analysis.default_analysis = request.data["default_analysis"]
        if "commands" in request.data:
            analysis.commands = request.data["commands"]
        if "processing" in request.data:
            analysis.processing = request.data["processing"]
        if "completed" in request.data:
            analysis.completed = request.data["completed"]
        analysis.save()
        data = AnalysisSerializer(analysis, many=False, context={"request": request}).data
        return Response(data=data, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        analysis = self.get_object()
        analysis.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"])
    def get_analysis_types(self, request):
        return Response(
            data=[{"value": v[0], "analysis_type": v[1]} for v in Analysis.analysis_type_choices],
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["get"])
    def get_associated_tasks(self, request, pk=None):
        analysis = self.get_object()
        tasks = analysis.tasks.all().order_by("-created_at")
        data = CeleryTaskSerializer(tasks, many=True, context={"request": request}).data
        return Response(data=data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def get_readiness(self, request, pk=None):
        analysis = self.get_object()
        return Response(data={"ready": analysis.ready()}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def queue_analysis(self, request, pk=None):
        analysis = self.get_object()
        print(analysis)
        if not analysis.ready():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        run_analysis.delay(analysis.id)

        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def get_result_summaries(self, request, pk=None):
        analysis = self.get_object()
        result_summary = analysis.result_summary.all()
        data = ResultSummarySerializer(result_summary, many=True, context={"request": request}).data
        return Response(data=data, status=status.HTTP_200_OK)


class FolderWatchingLocationViewSet(viewsets.ModelViewSet, FilterMixin):
    queryset = FolderWatchingLocation.objects.all()
    serializer_class = FolderWatchLocationSerializer
    parser_classes = (JSONParser, FormParser, MultiPartParser)
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]


    def get_queryset(self):
        return self.queryset

    def create(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        payload = request.data
        folder = FolderWatchingLocation()
        if not payload["folder_path"]:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        if not payload["vendor"]:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        for p in payload:
            if p != "id":
                setattr(folder, p, payload[p])
        folder.save()
        return Response(data=FolderWatchLocationSerializer(folder, many=False, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def get_exact_path(self, request):
        path = request.data.get("folder_path", None)
        if not path:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        folder = FolderWatchingLocation.objects.filter(folder_path=path)
        if not folder:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(data=FolderWatchLocationSerializer(folder[0], many=False, context={"request": request}).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def get_all_paths(self, request):
        folders = FolderWatchingLocation.objects.all()
        return Response(data=FolderWatchLocationSerializer(folders, many=True, context={"request": request}).data, status=status.HTTP_200_OK)

class UserAPIKeyViewSets(viewsets.ModelViewSet, FilterMixin):
    queryset = UserAPIKey.objects.all()
    serializer_class = UserAPIKeySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    lookup_field = "id"
    lookup_value_regex = '[^/]+'

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def get_object(self):
        queryset = self.get_queryset()
        filter_id = self.kwargs[self.lookup_field]
        data_object = queryset.get(id=filter_id)
        self.check_object_permissions(self.request, data_object)
        return data_object

    def create(self, request, *args, **kwargs):
        api_key, key = UserAPIKey.objects.create_key(name=self.request.data["name"], user=self.request.user)
        return Response(data={"key": key}, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        api_key = self.get_object()
        if api_key.user != self.request.user:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        api_key.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UploadedFileViewSet(viewsets.ModelViewSet, FilterMixin):
    queryset = UploadedFile.objects.all()
    serializer_class = UploadedFileSerializer
    parser_classes = (MultiPartParser,)
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]


    def create(self, request, *args, **kwargs):
        file = request.data.get('file')
        if not file:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        uploaded_file = UploadedFile.objects.create(file=file, user=request.user)
        return Response(data={"id": uploaded_file.id}, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        uploaded_file = self.get_object()
        if uploaded_file.user != self.request.user:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        uploaded_file.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def get_object(self):
        queryset = self.get_queryset()
        filter_id = self.kwargs[self.lookup_field]
        data_object = queryset.get(id=filter_id)
        self.check_object_permissions(self.request, data_object)
        return data_object


class CeleryTaskViewSet(viewsets.ReadOnlyModelViewSet, FilterMixin):
    queryset = CeleryTask.objects.all()
    serializer_class = CeleryTaskSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [OrderingFilter, SearchFilter]
    search_fields = ['task_id', 'status']
    ordering_fields = ['created_at', 'updated_at', 'status', 'task_id', 'id']

    @action(detail=True, methods=["get"])
    def get_experiment(self, request, pk=None):
        task = self.get_object()
        experiment = task.get_experiment()
        data = ExperimentSerializer(experiment, many=False, context={"request": request}).data
        return Response(data=data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def get_analysis(self, request, pk=None):
        task = self.get_object()
        analysis = task.get_analysis()
        data = AnalysisSerializer(analysis, many=False, context={"request": request}).data
        return Response(data=data, status=status.HTTP_200_OK)


class CeleryWorkerViewSet(viewsets.ReadOnlyModelViewSet, FilterMixin):
    queryset = CeleryWorker.objects.all()
    serializer_class = CeleryWorkerSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [OrderingFilter, SearchFilter]
    search_fields = ['worker_hostname', 'worker_status']
    ordering_fields = ['worker_hostname', 'worker_status']


class ResultSummaryViewSet(viewsets.ReadOnlyModelViewSet, FilterMixin):
    queryset = ResultSummary.objects.all()
    serializer_class = ResultSummarySerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    pagination_class = LimitOffsetPagination
    search_fields = ["analysis__experiment__experiment_name", "analysis__analysis_path"]
    ordering_fields = ["id", "analysis__experiment__experiment_name", "analysis__analysis_path", "created_at"]

    def get_queryset(self):
        query = Q()
        experiment = self.request.query_params.get("experiment", None)
        if experiment:
            query &= Q(analysis__experiment__id=experiment)
        analysis = self.request.query_params.get("analysis", None)
        if analysis:
            query &= Q(analysis__id=analysis)
        min_protein = self.request.query_params.get("min_protein", None)
        if min_protein:
            query &= Q(protein_identified__gte=min_protein)
        max_protein = self.request.query_params.get("max_protein", None)
        if max_protein:
            query &= Q(protein_identified__lte=max_protein)
        min_precursor = self.request.query_params.get("min_precursor", None)
        if min_precursor:
            query &= Q(precursor_identified__gte=min_precursor)
        max_precursor = self.request.query_params.get("max_precursor", None)
        if max_precursor:
            query &= Q(precursor_identified__lte=max_precursor)

        return self.queryset.filter(query)

    def get_object(self):
        object = super().get_object()
        return object

    @action(detail=False, methods=["get"])
    def get_last_month(self):
        analyses_last_month = Analysis.objects.filter(created_at__gte=timezone.now() - timedelta(days=30))
        result_summaries = ResultSummary.objects.filter(analysis__in=analyses_last_month)
        #calculate the mean of the protein_identified and precursor_identified for each analysis
        data = []
        for analysis in analyses_last_month:
            result_summary = result_summaries.filter(analysis=analysis)
            protein_identified = result_summary.aggregate(protein_identified=Avg('protein_identified'))['protein_identified']
            precursor_identified = result_summary.aggregate(precursor_identified=Avg('precursor_identified'))['precursor_identified']
            data.append({
                "analysis": analysis.id,
                "experiment": analysis.experiment.id,
                "protein_identified": protein_identified,
                "precursor_identified": precursor_identified
            })
        return Response(data=data, status=status.HTTP_200_OK)



class LogRecordViewSet(viewsets.ReadOnlyModelViewSet, FilterMixin):
    queryset = LogRecord.objects.all()
    serializer_class = LogRecordSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    search_fields = ["log"]
    ordering_fields = ["created_at"]
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        worker_id = self.request.query_params.get("worker_id", None)
        if worker_id:
            return self.queryset.filter(task__worker_id=worker_id)
        return self.queryset

    def get_object(self):
        object = super().get_object()
        return object

class PrecursorReportContentViewSet(viewsets.ReadOnlyModelViewSet, FilterMixin):
    queryset = PrecursorReportContent.objects.all()
    serializer_class = PrecursorReportContentSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    pagination_class = LimitOffsetPagination
    search_fields = ["gene_names", "protein_group", "precursor_id"]
    ordering_fields = ["id", "gene_names", "protein_group", "precursor_id", "intensity"]


    def get_queryset(self):
        queryset = super().get_queryset()
        query = Q()
        gene_names = self.request.query_params.get("gene_names", None)
        if gene_names:
            query &= Q(gene_names__icontains=gene_names)
        protein_group = self.request.query_params.get("protein_group", None)
        if protein_group:
            query &= Q(protein_group__icontains=protein_group)
        precursor_id = self.request.query_params.get("precursor_id", None)
        if precursor_id:
            query &= Q(precursor_id__icontains=precursor_id)
        file = self.request.query_params.get("file", None)
        if file:
            query &= Q(file__id=file)
        result_summary = self.request.query_params.get("result_summary", None)
        if result_summary:
            query &= Q(result_summary__id=result_summary)
        min_intensity = self.request.query_params.get("min_intensity", None)
        if min_intensity:
            query &= Q(intensity__gte=min_intensity)
        max_intensity = self.request.query_params.get("max_intensity", None)
        if max_intensity:
            query &= Q(intensity__lte=max_intensity)
        analysis = self.request.query_params.get("analysis", None)
        if analysis:
            analysis = analysis.split(",")
            if len(analysis)> 0:
                query &= Q(result_summary__analysis__id__in=analysis)

        min_protein = self.request.query_params.get("min_protein", None)
        if min_protein:
            query &= Q(result_summary__protein_identified__gte=min_protein)
        max_protein = self.request.query_params.get("max_protein", None)
        if max_protein:
            query &= Q(result_summary__protein_identified__lte=max_protein)
        min_precursor = self.request.query_params.get("min_precursor", None)
        if min_precursor:
            query &= Q(result_summary__precursor_identified__gte=min_precursor)
        max_precursor = self.request.query_params.get("max_precursor", None)
        if max_precursor:
            query &= Q(result_summary__precursor_identified__lte=max_precursor)

        return queryset.filter(query)

    def get_object(self):
        object = super().get_object()
        return object

class ProteinGroupReportContentViewSet(viewsets.ReadOnlyModelViewSet, FilterMixin):
    queryset = ProteinGroupReportContent.objects.all()
    serializer_class = ProteinGroupReportContentSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    pagination_class = LimitOffsetPagination
    search_fields = ["gene_names", "protein_group"]
    ordering_fields = ["id", "gene_names", "protein_group", "intensity"]

    def get_queryset(self):
        query = Q()
        gene_names = self.request.query_params.get("gene_names", None)
        if gene_names:
            query &= Q(gene_names__icontains=gene_names)
        protein_group = self.request.query_params.get("protein_group", None)
        if protein_group:
            query &= Q(protein_group__icontains=protein_group)
        file = self.request.query_params.get("file", None)
        if file:
            query &= Q(file__id=file)
        result_summary = self.request.query_params.get("result_summary", None)
        if result_summary:
            query &= Q(result_summary__id=result_summary)
        min_intensity = self.request.query_params.get("min_intensity", None)
        if min_intensity:
            query &= Q(intensity__gte=min_intensity)
        max_intensity = self.request.query_params.get("max_intensity", None)
        if max_intensity:
            query &= Q(intensity__lte=max_intensity)

        min_protein = self.request.query_params.get("min_protein", None)
        if min_protein:
            query &= Q(result_summary__protein_identified__gte=min_protein)
        max_protein = self.request.query_params.get("max_protein", None)
        if max_protein:
            query &= Q(result_summary__protein_identified__lte=max_protein)
        min_precursor = self.request.query_params.get("min_precursor", None)
        if min_precursor:
            query &= Q(result_summary__precursor_identified__gte=min_precursor)
        max_precursor = self.request.query_params.get("max_precursor", None)
        if max_precursor:
            query &= Q(result_summary__precursor_identified__lte=max_precursor)

        return self.queryset.filter(query)

    def get_object(self):
        object = super().get_object()
        return object


class CatapultRunConfigViewSet(viewsets.ModelViewSet):
    queryset = CatapultRunConfig.objects.all()
    serializer_class = CatapultRunConfigSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        query = Q()
        prefix = self.request.query_params.get("prefix", None)
        if prefix:
            query &= Q(content__prefix=prefix)
        experiment = self.request.query_params.get("experiment", None)
        if experiment:
            query &= Q(experiment__id=experiment)
        analysis = self.request.query_params.get("analysis", None)
        if analysis:
            query &= Q(analysis__id=analysis)
        result = self.queryset.filter(query)
        return result

    def create(self, request, *args, **kwargs):
        payload = request.data
        cat = CatapultRunConfig()
        for p in payload:
            if p != "id":
                if p == "experiment":
                    if payload[p]:
                        setattr(cat, p, Experiment.objects.get(id=payload[p]))
                elif p == "analysis":
                    if payload[p]:
                        setattr(cat, p, Analysis.objects.get(id=payload[p]))
                elif p == "folder_watching_location":
                    if payload[p]:
                        setattr(cat, p, FolderWatchingLocation.objects.get(id=payload[p]))
                else:
                    setattr(cat, p, payload[p])

        cat.save()
        data = CatapultRunConfigSerializer(cat, many=False, context={"request": request}).data
        return Response(data=data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        config = self.get_object()
        payload = request.data
        for p in payload:
            if p != "id":
                if p == "experiment":
                    if payload[p]:
                        setattr(config, p, Experiment.objects.get(id=payload[p]))
                elif p == "analysis":
                    if payload[p]:
                        setattr(config, p, Analysis.objects.get(id=payload[p]))
                elif p == "folder_watching_location":
                    if payload[p]:
                        setattr(config, p, FolderWatchingLocation.objects.get(id=payload[p]))
                else:
                    setattr(config, p, payload[p])
        config.save()
        data = CatapultRunConfigSerializer(config, many=False, context={"request": request}).data
        return Response(data=data, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        config = self.get_object()
        config.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"])
    def get_experiment(self, request, pk=None):
        config = self.get_object()
        experiment = config.experiment
        data = ExperimentSerializer(experiment, many=False, context={"request": request}).data
        return Response(data=data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def get_analysis(self, request, pk=None):
        config = self.get_object()
        analysis = config.analysis
        data = AnalysisSerializer(analysis, many=False, context={"request": request}).data
        return Response(data=data, status=status.HTTP_200_OK)