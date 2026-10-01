import json

from django.core.serializers import serialize
from django.db.models import Q
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


def map_search(request):
    """API tra cứu tất cả đối tượng bản đồ theo từ khoá (tối đa 5 kết quả mỗi loại)."""
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse({"results": []})

    results = []

    # ── Khuôn viên ──
    for obj in Campus.objects.filter(name__icontains=q)[:5]:
        if not obj.geom:
            continue
        c = obj.geom.centroid
        results.append({
            "type": "campus", "label": "Khuôn viên", "icon": "🏫",
            "id": obj.pk, "name": obj.name, "campus": obj.name,
            "lat": c.y, "lng": c.x,
            "images": [
                obj.image_1.name if obj.image_1 else None,
                obj.image_2.name if obj.image_2 else None,
                obj.image_3.name if obj.image_3 else None,
            ],
        })

    # ── Tòa nhà ──
    for obj in Building.objects.select_related("campus").filter(name__icontains=q)[:5]:
        if not obj.geom:
            continue
        c = obj.geom.centroid
        results.append({
            "type": "building", "label": "Tòa nhà", "icon": "🏢",
            "id": obj.pk, "name": obj.name,
            "campus": obj.campus.name if obj.campus else "",
            "campus_pk": obj.campus_id,
            "lat": c.y, "lng": c.x,
            "images": [
                obj.image_1.name if obj.image_1 else None,
                obj.image_2.name if obj.image_2 else None,
                obj.image_3.name if obj.image_3 else None,
            ],
        })

    # ── Tầng ──
    for obj in Floor.objects.select_related("building__campus").filter(
        Q(name__icontains=q) | Q(building__name__icontains=q)
    )[:6]:
        if not obj.geom:
            continue
        c = obj.geom.centroid
        bld = obj.building
        results.append({
            "type": "floor", "label": "Tầng", "icon": "📐",
            "id": obj.pk, "name": obj.name or f"Tầng {obj.level}",
            "campus": bld.campus.name if bld and bld.campus else "",
            "campus_pk": bld.campus_id if bld else None,
            "building_id": obj.building_id,
            "building_name": bld.name if bld else "",
            "level": obj.level,
            "lat": c.y, "lng": c.x,
        })

    # ── Phòng ──
    for obj in Room.objects.select_related("floor__building__campus").filter(name__icontains=q)[:8]:
        if not obj.geom:
            continue
        fl = obj.floor
        bld = fl.building if fl else None
        campus = bld.campus if bld else None
        results.append({
            "type": "room", "label": "Phòng", "icon": "🚪",
            "id": obj.pk, "name": obj.name,
            "campus": campus.name if campus else "",
            "campus_pk": campus.pk if campus else None,
            "building_id": bld.pk if bld else None,
            "building_name": bld.name if bld else "",
            "floor_id": fl.pk if fl else None,
            "floor_name": fl.name or f"Tầng {fl.level}" if fl else "",
            "room_type": obj.room_type,
            "lat": obj.geom.y, "lng": obj.geom.x,
            "images": [
                obj.image_1.name if obj.image_1 else None,
                obj.image_2.name if obj.image_2 else None,
                obj.image_3.name if obj.image_3 else None,
            ],
        })

    # ── Mảng xanh ──
    for obj in GreenArea.objects.select_related("campus").filter(name__icontains=q)[:5]:
        if not obj.geom:
            continue
        c = obj.geom.centroid
        type_label = "🌿 Thảm cỏ" if obj.type == "grass" else "🌸 Vườn hoa"
        results.append({
            "type": "green", "label": "Mảng xanh", "icon": "🌿",
            "id": obj.pk, "name": obj.name,
            "campus": obj.campus.name if obj.campus else "",
            "lat": c.y, "lng": c.x,
            "detail_type": type_label,
            "images": [
                obj.image_1.name if obj.image_1 else None,
                obj.image_2.name if obj.image_2 else None,
                obj.image_3.name if obj.image_3 else None,
            ],
        })

    # ── Bãi đỗ xe ──
    for obj in ParkingArea.objects.select_related("campus").filter(name__icontains=q)[:5]:
        if not obj.geom:
            continue
        c = obj.geom.centroid
        results.append({
            "type": "parking", "label": "Bãi xe", "icon": "🅿️",
            "id": obj.pk, "name": obj.name,
            "campus": obj.campus.name if obj.campus else "",
            "capacity": obj.capacity,
            "lat": c.y, "lng": c.x,
            "images": [
                obj.image_1.name if obj.image_1 else None,
                obj.image_2.name if obj.image_2 else None,
                obj.image_3.name if obj.image_3 else None,
            ],
        })

    # ── Cây xanh ──
    for obj in Tree.objects.select_related("campus").filter(species__icontains=q)[:5]:
        if not obj.geom:
            continue
        HEALTH = {"good": "✅ Phát triển tốt", "needs_care": "⚠️ Cần chăm sóc"}
        results.append({
            "type": "tree", "label": "Cây xanh", "icon": "🌳",
            "id": obj.pk, "name": obj.species or "Cây xanh",
            "campus": obj.campus.name if obj.campus else "",
            "health": HEALTH.get(obj.health_status, obj.health_status),
            "lat": obj.geom.y, "lng": obj.geom.x,
            "images": [
                obj.image_1.name if obj.image_1 else None,
                obj.image_2.name if obj.image_2 else None,
                obj.image_3.name if obj.image_3 else None,
            ],
        })

    return JsonResponse({"results": results})
