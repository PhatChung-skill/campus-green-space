from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q

from .forms import (
    BuildingForm,
    CampusForm,
    FloorForm,
    GreenAreaForm,
    ParkingAreaForm,
    RoomForm,
    TreeForm,
)
from .models import Building, Campus, Floor, GreenArea, ParkingArea, Room, Tree

PAGE_SIZE = 12

ENTITIES = {
    "co-so": {
        "model": Campus,
        "form": CampusForm,
        "resource": "campus",
        "title": "Cơ sở / Khuôn viên",
        "singular": "cơ sở",
        "pk_field": "campus_id",
        "search_fields": ["name"],
        "select_related": [],
        "list_fields": [("name", "Tên cơ sở")],
        "geom_type": "polygon",
        "order_by": "name",
        "filters": [],
        "parent_field": "",
        "parent_entity": "",
        "media_fields": ["image_1", "image_2", "image_3"],
    },
    "toa-nha": {
        "model": Building,
        "form": BuildingForm,
        "resource": "building",
        "title": "Tòa nhà",
        "singular": "tòa nhà",
        "pk_field": "building_id",
        "search_fields": ["name", "campus__name"],
        "select_related": ["campus"],
        "list_fields": [("name", "Tên tòa nhà"), ("campus", "Cơ sở")],
        "geom_type": "polygon",
        "order_by": "name",
        "filters": [{"param": "campus", "field": "campus_id", "label": "Cơ sở", "source": "campus"}],
        "parent_field": "campus",
        "parent_entity": "co-so",
        "media_fields": ["image_1", "image_2", "image_3"],
    },
    "tang": {
        "model": Floor,
        "form": FloorForm,
        "resource": "floor",
        "title": "Tầng",
        "singular": "tầng",
        "pk_field": "floor_id",
        "search_fields": ["name", "building__name"],
        "select_related": ["building", "building__campus"],
        "list_fields": [("name", "Tên tầng"), ("level", "Cấp"), ("building", "Tòa nhà")],
        "geom_type": "polygon",
        "order_by": "level",
        "filters": [{"param": "building", "field": "building_id", "label": "Tòa nhà", "source": "building"}],
        "parent_field": "building",
        "parent_entity": "toa-nha",
        "media_fields": ["blueprint_url"],
    },
    "phong": {
        "model": Room,
        "form": RoomForm,
        "resource": "room",
        "title": "Phòng",
        "singular": "phòng",
        "pk_field": "room_id",
        "search_fields": ["name", "floor__name", "floor__building__name"],
        "select_related": ["floor", "floor__building"],
        "list_fields": [("name", "Tên phòng"), ("room_type", "Loại"), ("floor", "Tầng")],
        "geom_type": "point",
        "order_by": "name",
        "filters": [
            {"param": "building", "field": "floor__building_id", "label": "Tòa nhà", "source": "building"},
            {"param": "floor", "field": "floor_id", "label": "Tầng", "source": "floor"},
        ],
        "parent_field": "floor",
        "parent_entity": "tang",
        "media_fields": ["image_1", "image_2", "image_3"],
    },
    "bai-xe": {
        "model": ParkingArea,
        "form": ParkingAreaForm,
        "resource": "parking",
        "title": "Bãi xe",
        "singular": "bãi xe",
        "pk_field": "parking_id",
        "search_fields": ["name", "campus__name"],
        "select_related": ["campus"],
        "list_fields": [("name", "Tên bãi xe"), ("capacity", "Sức chứa"), ("campus", "Cơ sở")],
        "geom_type": "polygon",
        "order_by": "name",
        "filters": [{"param": "campus", "field": "campus_id", "label": "Cơ sở", "source": "campus"}],
        "parent_field": "campus",
        "parent_entity": "co-so",
        "media_fields": ["image_1", "image_2", "image_3"],
    },
    "mang-xanh": {
        "model": GreenArea,
        "form": GreenAreaForm,
        "resource": "greenarea",
        "title": "Mảng xanh",
        "singular": "mảng xanh",
        "pk_field": "area_id",
        "search_fields": ["name", "campus__name"],
        "select_related": ["campus"],
        "list_fields": [("name", "Tên khu vực"), ("type", "Loại"), ("campus", "Cơ sở")],
        "geom_type": "polygon",
        "order_by": "name",
        "filters": [{"param": "campus", "field": "campus_id", "label": "Cơ sở", "source": "campus"}],
        "parent_field": "campus",
        "parent_entity": "co-so",
        "media_fields": ["image_1", "image_2", "image_3"],
    },
    "cay-xanh": {
        "model": Tree,
        "form": TreeForm,
        "resource": "tree",
        "title": "Cây xanh",
        "singular": "cây xanh",
        "pk_field": "tree_id",
        "search_fields": ["species", "campus__name", "health_status"],
        "select_related": ["campus"],
        "list_fields": [("species", "Giống cây"), ("health_status", "Tình trạng"), ("campus", "Cơ sở")],
        "geom_type": "point",
        "order_by": "species",
        "filters": [{"param": "campus", "field": "campus_id", "label": "Cơ sở", "source": "campus"}],
        "parent_field": "campus",
        "parent_entity": "co-so",
        "media_fields": ["image_1", "image_2", "image_3"],
    },
}

FILTER_SOURCES = {
    "campus": lambda: Campus.objects.order_by("name"),
    "building": lambda: Building.objects.select_related("campus").order_by("name"),
    "floor": lambda: Floor.objects.select_related("building").order_by("building__name", "level"),
}


def get_pk(obj, cfg):
    return getattr(obj, cfg["pk_field"])


def apply_list_filters(qs, cfg, request):
    specs = []
    for spec in cfg.get("filters") or []:
        selected = request.GET.get(spec["param"], "").strip()
        if selected:
            qs = qs.filter(**{spec["field"]: selected})
        specs.append(
            {
                "param": spec["param"],
                "label": spec["label"],
                "selected": selected,
                "choices": FILTER_SOURCES[spec["source"]](),
            }
        )
    return qs, specs


def search_queryset(qs, cfg, q):
    related = cfg.get("select_related") or []
    if related:
        qs = qs.select_related(*related)
    order = cfg.get("order_by")
    if order:
        qs = qs.order_by(order)
    if not q:
        return qs
    query = Q()
    for field in cfg["search_fields"]:
        query |= Q(**{f"{field}__icontains": q})
    return qs.filter(query)


def paginate(request, qs):
    paginator = Paginator(qs, PAGE_SIZE)
    page = request.GET.get("page")
    return paginator.get_page(page)


def display_value(obj, field):
    value = getattr(obj, field)
    if hasattr(obj, f"get_{field}_display"):
        return getattr(obj, f"get_{field}_display")()
    return value if value not in (None, "") else "—"


def user_search_qs(q):
    qs = User.objects.select_related("profile", "profile__role").order_by("username")
    if q:
        qs = qs.filter(
            Q(username__icontains=q)
            | Q(email__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(profile__phone__icontains=q)
            | Q(profile__role__name__icontains=q)
        )
    return qs
