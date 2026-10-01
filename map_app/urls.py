from django.urls import path

from . import portal_views, views

urlpatterns = [
    path("", views.map_view, name="map_view"),
    path("dashboard/", portal_views.dashboard_view, name="dashboard"),
    # Public API
    path("api/tang/<int:building_id>/", views.floors_by_building, name="public_floors"),
    path("api/phong/<int:floor_id>/",   views.rooms_by_floor,     name="public_rooms"),
    path("api/search/",                 views.map_search,          name="map_search"),
]
