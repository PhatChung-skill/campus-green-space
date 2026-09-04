from django.urls import path

from . import portal_views, views

urlpatterns = [
    path("", views.map_view, name="map_view"),
    path("dashboard/", portal_views.dashboard_view, name="dashboard"),
]
