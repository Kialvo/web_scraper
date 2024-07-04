from django.contrib import admin
from django.urls import path
from webscraper import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.upload_file, name='upload'),
    path('success/', views.success, name='success'),
    path('download/', views.download_file, name='download'),
]
