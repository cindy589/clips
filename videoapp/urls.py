from django.urls import path
from . import views

urlpatterns = [
    path('', views.procesar_video, name='procesar_video'),
]
