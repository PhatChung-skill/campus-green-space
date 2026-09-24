import json

from django.core.serializers import serialize
from django.http import JsonResponse
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
        # Tầng & Phòng không tải trước — được tải theo yêu cầu qua API
    }
    return render(request, "map_app/map.html", context)


def floors_by_building(request, building_id):
    """Trả về GeoJSON tất cả tầng của một tòa nhà (public API)."""
    qs = Floor.objects.filter(building_id=building_id).select_related("building").order_by("level")
    data = json.loads(
        serialize("geojson", qs, geometry_field="geom",
                  fields=["name", "level", "building", "blueprint_url"])
    )
    # Bổ sung building_name vào properties để hiển thị
    for feat in data.get("features", []):
        feat["properties"]["building_pk"] = building_id
    return JsonResponse(data)


def rooms_by_floor(request, floor_id):
    """Trả về GeoJSON tất cả phòng của một tầng (public API)."""
    qs = Room.objects.filter(floor_id=floor_id).select_related("floor__building")
    data = json.loads(
        serialize("geojson", qs, geometry_field="geom",
                  fields=["name", "room_type", "floor", "image_1", "image_2", "image_3"])
    )
    return JsonResponse(data)
