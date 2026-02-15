"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app import views
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from config import temp_views # Add this import


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/', include('users.urls')),
    # Legal pages
    path('legal/', include('legal_pages.urls')),
    # Business account
    path('api/business-account/', include('business_account.urls')),
    # Posts app
    path('api/posts/', include('posts.urls')),
    # Temporary test upload endpoint
    path('api/test-upload/', temp_views.TestFileUploadView.as_view(), name='test-file-upload'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) # Also include STATIC_ROOT for completeness if it's set and needed for development.
