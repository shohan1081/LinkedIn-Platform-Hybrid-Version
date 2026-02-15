from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import os

class TestFileUploadView(APIView):
    def post(self, request, format=None):
        if 'test_image' in request.FILES:
            uploaded_file = request.FILES['test_image']
            file_name = uploaded_file.name
            
            # Construct the full path to save the file
            # Using os.path.join for cross-platform compatibility
            save_path = os.path.join(str(settings.MEDIA_ROOT), 'test_uploads', file_name) # Convert settings.MEDIA_ROOT to str
            
            # Ensure the directory exists
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            try:
                with open(save_path, 'wb+') as destination:
                    for chunk in uploaded_file.chunks():
                        destination.write(chunk)
                
                file_url = settings.MEDIA_URL + 'test_uploads/' + file_name
                return Response({
                    'message': 'File uploaded successfully',
                    'file_name': file_name,
                    'file_size': uploaded_file.size,
                    'save_path': str(save_path), # Convert to string
                    'file_url': file_url,
                    'media_root': str(settings.MEDIA_ROOT), # Convert to string
                    'media_url': settings.MEDIA_URL,
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({
                    'message': 'File upload failed during saving',
                    'error': str(e),
                    'save_path_attempted': str(save_path), # Convert to string
                    'media_root': str(settings.MEDIA_ROOT), # Convert to string
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({'message': 'No file named "test_image" found in request.FILES'}, status=status.HTTP_400_BAD_REQUEST)
