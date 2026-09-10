from django.core.serializers import serialize
from django.shortcuts import render

from .models import Building, Campus, Floor, GreenArea, ParkingArea, Room, Tree


def map_view(request):
    context = {
        # Campus: cần pk để campus selector dùng flyToBounds
        "campuses_geojson": serialize(
            "geojson",
            Campus.objects.all(),
            geometry_field="geom",
            fields=["pk", "name", "image_1", "image_2", "image_3"],
        ),
        "buildings_geojson": serialize(
            "geojson",
            Building.objects.select_related("campus").all(),
            geometry_field="geom",
            fields=["name", "campus", "image_1", "image_2", "image_3"],
        ),
        "floors_geojson": serialize(
            "geojson",
            Floor.objects.select_related("building").all(),
            geometry_field="geom",
            fields=["name", "level", "building", "blueprint_url"],
        ),
        "rooms_geojson": serialize(
            "geojson",
            Room.objects.select_related("floor").all(),
            geometry_field="geom",
            fields=["name", "room_type", "floor", "image_1", "image_2", "image_3"],
        ),
        "parkings_geojson": serialize(
            "geojson",
            ParkingArea.objects.select_related("campus").all(),
            geometry_field="geom",
            fields=["name", "capacity", "campus", "image_1", "image_2", "image_3"],
        ),
        "greens_geojson": serialize(
            "geojson",
            GreenArea.objects.select_related("campus").all(),
            geometry_field="geom",
            fields=["name", "type", "campus", "image_1", "image_2", "image_3"],
        ),
        "trees_geojson": serialize(
            "geojson",
            Tree.objects.select_related("campus").all(),
            geometry_field="geom",
            fields=["species", "health_status", "campus", "image_1", "image_2", "image_3"],
        ),
    }
    return render(request, "map_app/map.html", context)
