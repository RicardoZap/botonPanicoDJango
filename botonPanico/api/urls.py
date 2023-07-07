from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('get/', views.getDato),
    path('post/', views.setAlerta),
    path('gpsDetalles/', views.getGPSDetail),
]
