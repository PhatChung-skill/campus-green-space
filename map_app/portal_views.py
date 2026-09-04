import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.core.serializers import serialize
from django.db.models import Count
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .catalog import (
    ENTITIES,
    apply_list_filters,
    display_value,
    get_pk,
    paginate,
    search_queryset,
    user_search_qs,
)
from .forms import PortalLoginForm, RoleForm, UserCreateForm, UserUpdateForm
from .models import Building, Campus, Floor, GreenArea, ParkingArea, Role, Room, Tree, UserProfile
from .permissions import (
    ADMIN_ROLE_NAME,
    can_access_portal,
    perm_required,
    portal_required,
    user_has_perm,
)


class PortalLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = PortalLoginForm

    def get_success_url(self):
        next_url = self.get_redirect_url()
        if next_url:
            return next_url
        if can_access_portal(self.request.user):
            return reverse("portal_home")
        return reverse("dashboard")


def _querystring(request):
    params = request.GET.copy()
    params.pop("page", None)
    return params.urlencode()


def _entity_or_404(slug):
    cfg = ENTITIES.get(slug)
    if not cfg:
        raise Http404("Không tìm thấy mục quản lý.")
    return cfg


def _row_actions(request, resource):
    return {
        "can_add": user_has_perm(request.user, "add", resource),
        "can_change": user_has_perm(request.user, "change", resource),
        "can_delete": user_has_perm(request.user, "delete", resource),
    }


@portal_required
def portal_home(request):
    entity_cards = [
        ("co-so", Campus, "Khuôn viên trường"),
        ("toa-nha", Building, "Khối nhà"),
        ("tang", Floor, "Mặt bằng tầng"),
        ("phong", Room, "Phòng chức năng"),
        ("bai-xe", ParkingArea, "Bãi đỗ"),
        ("mang-xanh", GreenArea, "Thảm cỏ / vườn"),
        ("cay-xanh", Tree, "Cây được theo dõi"),
    ]
    stats = []
    quick_adds = []
    for slug, model, hint in entity_cards:
        cfg = ENTITIES[slug]
        if not user_has_perm(request.user, "view", cfg["resource"]):
            continue
        stats.append(
            {
                "label": cfg["title"],
                "value": model.objects.count(),
                "hint": hint,
                "url": reverse("portal_entity_list", args=[slug]),
            }
        )
        if user_has_perm(request.user, "add", cfg["resource"]):
            quick_adds.append(
                {
                    "label": f"Thêm {cfg['singular']}",
                    "url": reverse("portal_entity_create", args=[slug]),
                }
            )
    if user_has_perm(request.user, "view", "users"):
        stats.append(
            {
                "label": "Tài khoản",
                "value": User.objects.count(),
                "hint": "Người dùng hệ thống",
                "url": reverse("portal_users"),
            }
        )
    if user_has_perm(request.user, "view", "roles"):
        stats.append(
            {
                "label": "Vai trò",
                "value": Role.objects.count(),
                "hint": "Nhóm quyền",
                "url": reverse("portal_roles"),
            }
        )
    if user_has_perm(request.user, "add", "users"):
        quick_adds.append({"label": "Thêm người dùng", "url": reverse("portal_user_create")})
    campuses_geojson = serialize("geojson", Campus.objects.all())
    return render(
        request,
        "manage/dashboard.html",
        {
            "stats": stats,
            "quick_adds": quick_adds,
            "campuses_geojson": campuses_geojson,
            "campus_count": Campus.objects.count(),
        },
    )


@portal_required
def parent_geom(request, entity, pk):
    cfg = _entity_or_404(entity)
    if not user_has_perm(request.user, "view", cfg["resource"]):
        return JsonResponse({"error": "forbidden"}, status=403)
    obj = get_object_or_404(cfg["model"], pk=pk)
    if not obj.geom:
        return JsonResponse({"error": "empty"}, status=404)
    return JsonResponse(json.loads(obj.geom.geojson))


@perm_required("view", "users")
def user_list(request):
    q = request.GET.get("q", "").strip()
    page_obj = paginate(request, user_search_qs(q))
    return render(
        request,
        "manage/users/list.html",
        {
            "page_obj": page_obj,
            "q": q,
            "querystring": _querystring(request),
            **_row_actions(request, "users"),
        },
    )


@perm_required("add", "users")
def user_create(request):
    form = UserCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Đã tạo tài khoản mới.")
        return redirect("portal_users")
    return render(request, "manage/users/form.html", {"form": form, "is_create": True})


@perm_required("change", "users")
def user_update(request, pk):
    user = get_object_or_404(User, pk=pk)
    form = UserUpdateForm(request.POST or None, instance=user)
    if request.method == "POST" and form.is_valid():
        new_role = form.cleaned_data["role"]
        if user == request.user and new_role.name != ADMIN_ROLE_NAME and is_last_admin(user):
            messages.error(request, "Không thể đổi vai trò của quản trị viên cuối cùng.")
            return redirect("portal_user_edit", pk=pk)
        form.save()
        messages.success(request, "Đã cập nhật tài khoản.")
        return redirect("portal_users")
    return render(
        request,
        "manage/users/form.html",
        {"form": form, "is_create": False, "edited_user": user},
    )


def is_last_admin(user):
    admin_role = Role.objects.filter(name=ADMIN_ROLE_NAME).first()
    if not admin_role:
        return user.is_superuser and User.objects.filter(is_superuser=True).count() <= 1
    count = UserProfile.objects.filter(role=admin_role).count()
    current = getattr(getattr(user, "profile", None), "role", None)
    return current == admin_role and count <= 1


@perm_required("delete", "users")
def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, "Bạn không thể xóa chính tài khoản đang đăng nhập.")
        return redirect("portal_users")
    if is_last_admin(user):
        messages.error(request, "Không thể xóa quản trị viên cuối cùng của hệ thống.")
        return redirect("portal_users")
    if request.method == "POST":
        username = user.username
        user.delete()
        messages.success(request, f"Đã xóa tài khoản {username}.")
        return redirect("portal_users")
    return render(
        request,
        "manage/confirm_delete.html",
        {
            "object_label": user.username,
            "cancel_url": reverse("portal_users"),
            "title": "Xóa người dùng",
        },
    )


@perm_required("view", "roles")
def role_list(request):
    q = request.GET.get("q", "").strip()
    qs = Role.objects.annotate(user_count=Count("users")).order_by("name")
    if q:
        qs = qs.filter(name__icontains=q)
    page_obj = paginate(request, qs)
    return render(
        request,
        "manage/roles/list.html",
        {
            "page_obj": page_obj,
            "q": q,
            "querystring": _querystring(request),
            **_row_actions(request, "roles"),
        },
    )


ROLE_GROUPS = [
    ("Cổng quản lý", ["can_access_portal"]),
    ("Người dùng", ["can_view_users", "can_add_users", "can_change_users", "can_delete_users"]),
    ("Vai trò", ["can_view_roles", "can_add_roles", "can_change_roles", "can_delete_roles"]),
    ("Cơ sở", ["can_view_campus", "can_add_campus", "can_change_campus", "can_delete_campus"]),
    ("Tòa nhà", ["can_view_building", "can_add_building", "can_change_building", "can_delete_building"]),
    ("Tầng", ["can_view_floor", "can_add_floor", "can_change_floor", "can_delete_floor"]),
    ("Phòng", ["can_view_room", "can_add_room", "can_change_room", "can_delete_room"]),
    ("Bãi xe", ["can_view_parking", "can_add_parking", "can_change_parking", "can_delete_parking"]),
    ("Mảng xanh", ["can_view_greenarea", "can_add_greenarea", "can_change_greenarea", "can_delete_greenarea"]),
    ("Cây xanh", ["can_view_tree", "can_add_tree", "can_change_tree", "can_delete_tree"]),
]


def _role_form_groups(form):
    return [(title, [form[name] for name in fields]) for title, fields in ROLE_GROUPS]


@perm_required("add", "roles")
def role_create(request):
    form = RoleForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Đã tạo vai trò mới.")
        return redirect("portal_roles")
    return render(
        request,
        "manage/roles/form.html",
        {"form": form, "is_create": True, "role_groups": _role_form_groups(form)},
    )


@perm_required("change", "roles")
def role_update(request, pk):
    role = get_object_or_404(Role, pk=pk)
    form = RoleForm(request.POST or None, instance=role)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Đã cập nhật vai trò.")
        return redirect("portal_roles")
    return render(
        request,
        "manage/roles/form.html",
        {"form": form, "is_create": False, "role": role, "role_groups": _role_form_groups(form)},
    )


@perm_required("delete", "roles")
def role_delete(request, pk):
    role = get_object_or_404(Role, pk=pk)
    if role.is_system:
        messages.error(request, "Không thể xóa vai trò hệ thống.")
        return redirect("portal_roles")
    if role.users.exists():
        messages.error(request, "Vai trò đang được gán cho người dùng, hãy đổi vai trò trước khi xóa.")
        return redirect("portal_roles")
    if request.method == "POST":
        name = role.name
        role.delete()
        messages.success(request, f"Đã xóa vai trò {name}.")
        return redirect("portal_roles")
    return render(
        request,
        "manage/confirm_delete.html",
        {
            "object_label": role.name,
            "cancel_url": reverse("portal_roles"),
            "title": "Xóa vai trò",
        },
    )


@portal_required
def entity_list(request, entity):
    cfg = _entity_or_404(entity)
    if not user_has_perm(request.user, "view", cfg["resource"]):
        messages.error(request, "Bạn không đủ quyền xem mục này.")
        return redirect("portal_home")
    q = request.GET.get("q", "").strip()
    qs = search_queryset(cfg["model"].objects.all(), cfg, q)
    qs, list_filters = apply_list_filters(qs, cfg, request)
    page_obj = paginate(request, qs)
    rows = []
    for obj in page_obj.object_list:
        rows.append(
            {
                "pk": get_pk(obj, cfg),
                "values": [display_value(obj, field) for field, _label in cfg["list_fields"]],
            }
        )
    return render(
        request,
        "manage/entity_list.html",
        {
            "cfg": cfg,
            "entity": entity,
            "page_obj": page_obj,
            "rows": rows,
            "q": q,
            "list_filters": list_filters,
            "querystring": _querystring(request),
            **_row_actions(request, cfg["resource"]),
        },
    )


@portal_required
def entity_create(request, entity):
    cfg = _entity_or_404(entity)
    if not user_has_perm(request.user, "add", cfg["resource"]):
        messages.error(request, "Bạn không đủ quyền thêm dữ liệu.")
        return redirect("portal_entity_list", entity=entity)
    initial = {}
    parent = cfg.get("parent_field")
    if parent:
        value = request.GET.get(parent, "").strip()
        if value:
            initial[parent] = value
    form = cfg["form"](request.POST or None, initial=initial or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Đã thêm {cfg['singular']}.")
        return redirect("portal_entity_list", entity=entity)
    return render(
        request,
        "manage/entity_form.html",
        {"form": form, "cfg": cfg, "entity": entity, "is_create": True},
    )


@portal_required
def entity_update(request, entity, pk):
    cfg = _entity_or_404(entity)
    if not user_has_perm(request.user, "change", cfg["resource"]):
        messages.error(request, "Bạn không đủ quyền sửa dữ liệu.")
        return redirect("portal_entity_list", entity=entity)
    obj = get_object_or_404(cfg["model"], pk=pk)
    form = cfg["form"](request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Đã cập nhật {cfg['singular']}.")
        return redirect("portal_entity_list", entity=entity)
    return render(
        request,
        "manage/entity_form.html",
        {"form": form, "cfg": cfg, "entity": entity, "is_create": False, "obj": obj},
    )


@portal_required
def entity_delete(request, entity, pk):
    cfg = _entity_or_404(entity)
    if not user_has_perm(request.user, "delete", cfg["resource"]):
        messages.error(request, "Bạn không đủ quyền xóa dữ liệu.")
        return redirect("portal_entity_list", entity=entity)
    obj = get_object_or_404(cfg["model"], pk=pk)
    if request.method == "POST":
        label = str(obj)
        obj.delete()
        messages.success(request, f"Đã xóa {label}.")
        return redirect("portal_entity_list", entity=entity)
    return render(
        request,
        "manage/confirm_delete.html",
        {
            "object_label": str(obj),
            "cancel_url": reverse("portal_entity_list", args=[entity]),
            "title": f"Xóa {cfg['singular']}",
        },
    )


@login_required
def dashboard_view(request):
    if can_access_portal(request.user):
        return redirect("portal_home")
    role = getattr(getattr(request.user, "profile", None), "role", None)
    context = {
        "username": request.user.get_full_name() or request.user.username,
        "role": role.name if role else "Khách",
    }
    return render(request, "map_app/dashboard.html", context)
