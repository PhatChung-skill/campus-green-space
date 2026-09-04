from django.core.serializers import serialize
from django.shortcuts import render

from .models import Building, Campus, Floor, GreenArea, ParkingArea, Room, Tree


def map_view(request):
    context = {
        "campuses_geojson": serialize("geojson", Campus.objects.all()),
        "buildings_geojson": serialize("geojson", Building.objects.all()),
        "floors_geojson": serialize("geojson", Floor.objects.all()),
        "rooms_geojson": serialize("geojson", Room.objects.all()),
        "parkings_geojson": serialize("geojson", ParkingArea.objects.all()),
        "greens_geojson": serialize("geojson", GreenArea.objects.all()),
        "trees_geojson": serialize("geojson", Tree.objects.all()),
    }
    return render(request, "map_app/map.html", context)
