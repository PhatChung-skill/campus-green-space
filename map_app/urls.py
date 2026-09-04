from django.urls import path
from . import views

urlpatterns = [
    path('', views.map_view, name='map_view'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
]