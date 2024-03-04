from django.http import HttpResponse
from django.shortcuts import render
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.views import APIView
import os
from rest_framework.response import Response
# Create your views here.

class FileBrowserView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def post(self, request, *args, **kwargs):
        file_path = request.data.get("file_path", ".")
        file_path = os.path.abspath(file_path)
        folder = []
        files = []
        for i in os.scandir(file_path):
            if i.is_dir():
                folder.append(i.name)
            else:
                files.append(i.name)

        return Response(data={"folders": folder, "files": files, "current": file_path})
