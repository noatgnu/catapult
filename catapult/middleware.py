from django.http import JsonResponse
from django.conf import settings

class DemoModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.DEMO:
            restricted_endpoints = [
                '/api/api-keys',
                '/api/file-browser',
                '/admin',
                '/api/experiments',
                '/api/analyses',
                '/api/files',
                '/api/uploadedfiles',
                '/api/folderlocations',
                '/api/tasks',
                '/api/workers',
                '/api/logrecords',
                '/api/proteingroup',
                '/api/precursor'
                # Add more endpoints as needed
            ]
            print(request.path)
            for endpoint in restricted_endpoints:
                if request.path.startswith(endpoint) and request.method != 'GET':
                    return JsonResponse({'error': 'This action is not allowed in demo mode.'}, status=403)
        response = self.get_response(request)
        return response