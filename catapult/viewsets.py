from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework import viewsets, permissions, status
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from filters.mixins import FiltersMixin
from catapult.models import File, Experiment, Analysis, FolderWatchingLocation, UserAPIKey, UploadedFile
from catapult.serializers import FileSerializer, ExperimentSerializer, AnalysisSerializer, \
    FolderWatchLocationSerializer, UserAPIKeySerializer, UploadedFileSerializer


class FileViewSet(viewsets.ModelViewSet, FiltersMixin):
    queryset = File.objects.all()
    serializer_class = FileSerializer
    parser_classes = (JSONParser, FormParser, MultiPartParser)
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    ordering_fields = ['created_at', 'updated_at', 'file_path', 'ready_for_processing', 'id']
    search_fields = ['file_path']


class ExperimentViewSet(viewsets.ModelViewSet, FiltersMixin):
    queryset = Experiment.objects.all()
    serializer_class = ExperimentSerializer
    parser_classes = (JSONParser, FormParser, MultiPartParser)
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [OrderingFilter, DjangoFilterBackend, SearchFilter]
    ordering_fields = ['id', 'created_at', 'updated_at', 'experiment_name', 'vendor', 'processing_status', 'completed']
    search_fields = ['experiment_name']

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
        experiment.experiment_name = request.data["experiment_name"]
        experiment.vendor = request.data["vendor"]
        experiment.sample_count = request.data["sample_count"]
        experiment.save()
        data = ExperimentSerializer(experiment, many=False, context={"request": request}).data
        return Response(data=data, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        experiment = self.get_object()
        experiment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"])
    def get_vendor_choices(self, request):
        return Response(
            data=[{"value": v[0], "vendor": v[1]} for v in Experiment.vendor_choices],
            status=status.HTTP_200_OK
        )

class AnalysisViewSet(viewsets.ModelViewSet, FiltersMixin):
    queryset = Analysis.objects.all()
    serializer_class = AnalysisSerializer
    parser_classes = (JSONParser, FormParser, MultiPartParser)
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    ordering_fields = ['id', 'created_at', 'updated_at', 'analysis_name', 'experiment', 'analysis_type', 'completed']
    search_fields = ['analysis_name']

    def create(self, request, *args, **kwargs):
        analysis = Analysis.objects.create(
            analysis_name=request.data["analysis_name"],
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
        analysis.analysis_name = request.data["analysis_name"]
        analysis.experiment = Experiment.objects.get(id=request.data["experiment"])
        analysis.analysis_type = request.data["analysis_type"]
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


class FolderWatchingLocationViewSet(viewsets.ModelViewSet, FiltersMixin):
    queryset = FolderWatchingLocation.objects.all()
    serializer_class = FolderWatchLocationSerializer
    parser_classes = (JSONParser, FormParser, MultiPartParser)
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]


class UserAPIKeyViewSets(viewsets.ModelViewSet, FiltersMixin):
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


class UploadedFileViewSet(viewsets.ModelViewSet, FiltersMixin):
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
