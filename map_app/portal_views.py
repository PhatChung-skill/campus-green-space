import json
import logging
import re
import secrets
from datetime import timedelta

from django.contrib.auth import login as auth_login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.serializers import serialize
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from .catalog import (
    ENTITIES,
    apply_list_filters,
    display_value,
    get_pk,
    paginate,
    search_queryset,
    user_search_qs,
)
from .forms import (
    HomepageBlockForm,
    PasswordResetConfirmForm,
    PasswordResetRequestForm,
    PortalLoginForm,
    RegisterForm,
    RoleForm,
    UserCreateForm,
    UserUpdateForm,
)
from .models import Building, Campus, FeedbackMessage, FeedbackReaction, FeedbackThread, Floor, GreenArea, HomepageBlock, ParkingArea, PasswordResetOTP, PendingEmailRegistration, Role, Room, Tree, UserProfile
from .permissions import (
    ADMIN_ROLE_NAME,
    can_access_portal,
    is_admin_user,
    perm_required,
    portal_required,
    user_has_perm,
)

logger = logging.getLogger(__name__)


class PortalLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = PortalLoginForm

    def get_success_url(self):
        return reverse("home")


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
    if user_has_perm(request.user, "manage", "feedback"):
        unread_feedback = FeedbackThread.objects.filter(staff_read_at__isnull=True).count()
        stats.append({
            "label": "Góp ý / Báo lỗi",
            "value": FeedbackThread.objects.count(),
            "hint": f"{unread_feedback} hội thoại chưa đọc",
            "url": reverse("portal_feedback_inbox"),
        })
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


@login_required
def homepage_content_view(request):
    if not is_admin_user(request.user):
        messages.error(request, "Chỉ Quản trị viên được phép chỉnh sửa nội dung trang chủ.")
        return redirect("portal_home" if can_access_portal(request.user) else "home")
    sections = []
    for kind, label, description in (
        (HomepageBlock.Kind.HEADER, "Đầu trang", "Tên thương hiệu, mô tả ngắn và logo dùng trên thanh điều hướng."),
        (HomepageBlock.Kind.HERO, "Banner đầu trang", "Nội dung nổi bật và nút khám phá bản đồ."),
        (HomepageBlock.Kind.INTRO, "Phần giới thiệu", "Nội dung chính và hình ảnh giới thiệu."),
        (HomepageBlock.Kind.FEATURE, "Các thẻ tiện ích", "Mỗi thẻ được thêm, sửa hoặc xóa độc lập."),
        (HomepageBlock.Kind.FOOTER, "Chân trang", "Thông tin và liên kết ở cuối trang."),
    ):
        items = list(HomepageBlock.objects.filter(kind=kind).order_by("sort_order", "pk"))
        sections.append(
            {
                "kind": kind,
                "label": label,
                "description": description,
                "items": items,
                "can_add": kind == HomepageBlock.Kind.FEATURE or not items,
            }
        )
    return render(
        request,
        "manage/homepage_content_list.html",
        {"sections": sections},
    )


def _homepage_admin_or_redirect(request):
    if is_admin_user(request.user):
        return None
    messages.error(request, "Chỉ Quản trị viên được phép chỉnh sửa nội dung trang chủ.")
    return redirect("portal_home" if can_access_portal(request.user) else "home")


@login_required
def homepage_block_create_view(request, kind):
    denied = _homepage_admin_or_redirect(request)
    if denied:
        return denied
    labels = dict(HomepageBlock.Kind.choices)
    if kind not in labels:
        raise Http404("Không tìm thấy loại nội dung.")
    if kind != HomepageBlock.Kind.FEATURE and HomepageBlock.objects.filter(kind=kind).exists():
        messages.warning(request, f'Khu vực "{labels[kind]}" chỉ có một khối nội dung. Hãy sửa khối đang có.')
        return redirect("homepage_content")
    form = HomepageBlockForm(request.POST or None, request.FILES or None, kind=kind)
    if request.method == "POST" and form.is_valid():
        block = form.save()
        messages.success(request, f'Đã thêm nội dung vào khu vực "{labels[kind]}".')
        return redirect("homepage_content")
    return render(
        request,
        "manage/homepage_block_form.html",
        {"form": form, "kind": kind, "kind_label": labels[kind], "is_create": True},
    )


@login_required
def homepage_block_edit_view(request, pk):
    denied = _homepage_admin_or_redirect(request)
    if denied:
        return denied
    block = get_object_or_404(HomepageBlock, pk=pk)
    form = HomepageBlockForm(request.POST or None, request.FILES or None, instance=block)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f'Đã cập nhật "{block.title}".')
        return redirect("homepage_content")
    return render(
        request,
        "manage/homepage_block_form.html",
        {
            "form": form,
            "kind": block.kind,
            "kind_label": block.get_kind_display(),
            "block": block,
            "is_create": False,
        },
    )


@login_required
def homepage_block_delete_view(request, pk):
    denied = _homepage_admin_or_redirect(request)
    if denied:
        return denied
    block = get_object_or_404(HomepageBlock, pk=pk)
    if request.method == "POST":
        title = block.title
        feature_group = block.feature_group if block.kind == HomepageBlock.Kind.FEATURE else None
        block.delete()
        if feature_group and not feature_group.blocks.exists():
            feature_group.delete()
        messages.success(request, f'Đã xóa nội dung "{title}" khỏi trang chủ.')
        return redirect("homepage_content")
    return render(
        request,
        "manage/confirm_delete.html",
        {
            "title": "Xóa nội dung trang chủ",
            "object_label": block.title,
            "cancel_url": reverse("homepage_content"),
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


@portal_required
def entity_context_geojson(request, entity):
    """
    Trả về các lớp GeoJSON ngữ cảnh để hiển thị trên map khi thêm/sửa dữ liệu.
    Tham số GET: campus, building, floor (là pk của đối tượng cha tương ứng)
    """
    campus_id  = request.GET.get("campus")
    building_id = request.GET.get("building")
    floor_id   = request.GET.get("floor")
    layers = {}

    def to_geojson(qs, fields):
        return json.loads(serialize("geojson", qs, geometry_field="geom", fields=fields))

    if entity == "toa-nha":
        if campus_id:
            layers["campus"]   = to_geojson(Campus.objects.filter(pk=campus_id),                    ["name"])
            layers["buildings"]= to_geojson(Building.objects.filter(campus_id=campus_id),            ["name"])
            layers["greens"]   = to_geojson(GreenArea.objects.filter(campus_id=campus_id),           ["name"])
            layers["parkings"] = to_geojson(ParkingArea.objects.filter(campus_id=campus_id),         ["name"])
            layers["trees"]    = to_geojson(Tree.objects.filter(campus_id=campus_id),                ["species"])

    elif entity == "tang":
        if building_id:
            bld_qs = Building.objects.filter(pk=building_id).select_related("campus")
            if bld_qs.exists():
                bld = bld_qs.first()
                layers["campus"]   = to_geojson(Campus.objects.filter(pk=bld.campus_id),  ["name"])
                layers["building"] = to_geojson(bld_qs,                                    ["name"])
                layers["floors"]   = to_geojson(Floor.objects.filter(building_id=building_id), ["name", "level"])

    elif entity == "phong":
        if floor_id:
            flr_qs = Floor.objects.filter(pk=floor_id).select_related("building__campus")
            if flr_qs.exists():
                flr = flr_qs.first()
                layers["campus"]   = to_geojson(Campus.objects.filter(pk=flr.building.campus_id), ["name"])
                layers["building"] = to_geojson(Building.objects.filter(pk=flr.building_id),       ["name"])
                layers["floor"]    = to_geojson(flr_qs,                                            ["name", "level"])
                layers["rooms"]    = to_geojson(Room.objects.filter(floor_id=floor_id),            ["name", "room_type"])

    elif entity == "bai-xe":
        # Bãi xe: hiện khuôn viên + tòa nhà + mảng xanh + bãi xe đã có để vẽ chính xác hơn
        if campus_id:
            layers["campus"]   = to_geojson(Campus.objects.filter(pk=campus_id),              ["name"])
            layers["buildings"]= to_geojson(Building.objects.filter(campus_id=campus_id),     ["name"])
            layers["greens"]   = to_geojson(GreenArea.objects.filter(campus_id=campus_id),    ["name"])
            layers["parkings"] = to_geojson(ParkingArea.objects.filter(campus_id=campus_id),  ["name"])

    elif entity == "mang-xanh":
        if campus_id:
            layers["campus"]   = to_geojson(Campus.objects.filter(pk=campus_id),              ["name"])
            layers["buildings"]= to_geojson(Building.objects.filter(campus_id=campus_id),     ["name"])
            layers["parkings"] = to_geojson(ParkingArea.objects.filter(campus_id=campus_id),  ["name"])
            layers["greens"]   = to_geojson(GreenArea.objects.filter(campus_id=campus_id),    ["name"])

    elif entity == "cay-xanh":
        if campus_id:
            layers["campus"]   = to_geojson(Campus.objects.filter(pk=campus_id),              ["name"])
            layers["buildings"]= to_geojson(Building.objects.filter(campus_id=campus_id),     ["name"])
            layers["parkings"] = to_geojson(ParkingArea.objects.filter(campus_id=campus_id),  ["name"])
            layers["greens"]   = to_geojson(GreenArea.objects.filter(campus_id=campus_id),    ["name"])
            layers["trees"]    = to_geojson(Tree.objects.filter(campus_id=campus_id),         ["species"])

    elif entity == "co-so":
        layers["campuses"] = to_geojson(Campus.objects.all(), ["name"])

    return JsonResponse(layers)


@portal_required
def filter_buildings(request):
    """API: Trả về danh sách tòa nhà theo cơ sở, dùng cho cascade dropdown phòng."""
    campus_id = request.GET.get("campus")
    if campus_id:
        buildings = list(Building.objects.filter(campus_id=campus_id).order_by("name").values("pk", "name"))
    else:
        buildings = list(Building.objects.order_by("name").values("pk", "name"))
    return JsonResponse({"buildings": buildings})


@portal_required
def filter_floors(request):
    """API: Trả về danh sách tầng theo tòa nhà, dùng cho cascade dropdown phòng."""
    building_id = request.GET.get("building")
    if building_id:
        floors = list(Floor.objects.filter(building_id=building_id).order_by("level").values("pk", "name", "level"))
    else:
        floors = []
    return JsonResponse({"floors": floors})



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
        with transaction.atomic():
            FeedbackThread.objects.filter(user=user).delete()
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
    ("Góp ý / Báo lỗi", ["can_manage_feedback"]),
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


def _feedback_permission_denied(request):
    if not request.user.is_authenticated:
        return redirect(f"{reverse('login')}?next={request.path}")
    if not can_access_portal(request.user) or not user_has_perm(request.user, "manage", "feedback"):
        messages.error(request, "Bạn không đủ quyền quản lý góp ý / báo lỗi.")
        return redirect("portal_home" if can_access_portal(request.user) else "home")
    return None


def feedback_inbox(request):
    denied = _feedback_permission_denied(request)
    if denied:
        return denied
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    threads = FeedbackThread.objects.annotate(message_count=Count("messages")).order_by("-updated_at", "-pk")
    if q:
        threads = threads.filter(Q(username_snapshot__icontains=q) | Q(messages__body__icontains=q)).distinct()
    if status == "unread":
        threads = threads.filter(staff_read_at__isnull=True)
    elif status == "read":
        threads = threads.filter(staff_read_at__isnull=False)
    page_obj = paginate(request, threads)
    return render(request, "manage/feedback/inbox.html", {
        "threads": page_obj.object_list,
        "page_obj": page_obj,
        "q": q,
        "status": status,
        "querystring": _querystring(request),
        "unread_count": FeedbackThread.objects.filter(staff_read_at__isnull=True).count(),
    })


def feedback_unread_count_api(request):
    denied = _feedback_permission_denied(request)
    if denied:
        return JsonResponse({"detail": "Bạn không đủ quyền."}, status=403)
    return JsonResponse({"count": FeedbackThread.objects.filter(staff_read_at__isnull=True).count()})


def _feedback_reaction_summary(message, user):
    totals = {}
    reacted = set()
    for reaction in message.reactions.select_related("user").all():
        totals[reaction.emoji] = totals.get(reaction.emoji, 0) + 1
        if reaction.user_id == user.pk:
            reacted.add(reaction.emoji)
    summary = [
        {"emoji": emoji, "label": label, "count": totals.get(emoji, 0), "reacted": emoji in reacted}
        for emoji, label in FeedbackReaction.Emoji.choices
    ]
    return summary, sum(totals.values())


def feedback_thread_view(request, pk):
    denied = _feedback_permission_denied(request)
    if denied:
        return denied
    thread = get_object_or_404(FeedbackThread.objects.prefetch_related("messages__sender"), pk=pk)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "react":
            try:
                message_id = int(request.POST.get("message_id", ""))
            except (TypeError, ValueError):
                message_id = None
            message = get_object_or_404(thread.messages.all(), pk=message_id)
            emoji = request.POST.get("emoji", "")
            if emoji not in FeedbackReaction.Emoji.values:
                messages.error(request, "Emoji không hợp lệ.")
            else:
                reaction, created = FeedbackReaction.objects.get_or_create(message=message, user=request.user, emoji=emoji)
                if not created:
                    reaction.delete()
                thread.staff_read_at = timezone.now()
                thread.save(update_fields=["staff_read_at"])
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    reaction_summary, reaction_total = _feedback_reaction_summary(message, request.user)
                    return JsonResponse({
                        "reaction_summary": reaction_summary,
                        "reaction_total": reaction_total,
                    })
            return redirect("portal_feedback_thread", pk=thread.pk)
        if action == "mark_read":
            thread.staff_read_at = timezone.now()
            thread.save(update_fields=["staff_read_at"])
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"ok": True})
            messages.success(request, "Đã đánh dấu hội thoại là đã đọc.")
            return redirect("portal_feedback_thread", pk=thread.pk)
        if action == "delete":
            for feedback_message in thread.messages.all():
                if feedback_message.image:
                    feedback_message.image.delete(save=False)
            thread.delete()
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"redirect_url": reverse("portal_feedback_inbox")})
            messages.success(request, "Đã xóa hội thoại và toàn bộ tin nhắn đính kèm.")
            return redirect("portal_feedback_inbox")
        if action == "delete_message":
            try:
                message_id = int(request.POST.get("message_id", ""))
            except (TypeError, ValueError):
                message_id = None
            message = get_object_or_404(FeedbackMessage, pk=message_id, thread=thread)
            if message.image:
                message.image.delete(save=False)
            message.delete()
            thread.staff_read_at = timezone.now()
            thread.save(update_fields=["staff_read_at", "updated_at"])
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"deleted": True, "empty": not thread.messages.exists()})
            messages.success(request, "Đã xóa tin nhắn.")
            return redirect("portal_feedback_thread", pk=thread.pk)
        if action == "reply":
            body = request.POST.get("body", "").strip()
            image = request.FILES.get("image")
            is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
            error = ""
            if len(body) > 3000:
                error = "Nội dung phản hồi tối đa 3.000 ký tự."
            elif not body and not image:
                error = "Hãy nhập nội dung hoặc đính kèm hình ảnh."
            elif image and image.size > 5 * 1024 * 1024:
                error = "Hình ảnh tối đa 5 MB."
            else:
                reply_to = None
                reply_to_id = request.POST.get("reply_to")
                if reply_to_id:
                    try:
                        reply_to = thread.messages.filter(pk=int(reply_to_id)).first()
                    except (TypeError, ValueError):
                        reply_to = None

                message = FeedbackMessage(
                    thread=thread,
                    sender=request.user,
                    sender_name=(request.user.get_full_name() or request.user.get_username())[:150],
                    is_staff_reply=True,
                    reply_to=reply_to,
                    body=body,
                    image=image or "",
                )
                try:
                    message.full_clean()
                    message.save()
                    thread.user_read_at = None
                    thread.staff_read_at = timezone.now()
                    thread.save(update_fields=["user_read_at", "staff_read_at", "updated_at"])
                    if is_ajax:
                        message.reaction_summary, message.reaction_total = _feedback_reaction_summary(message, request.user)
                        html = render_to_string("manage/feedback/_message.html", {"message": message}, request=request)
                        return JsonResponse({"ok": True, "html": html})
                    messages.success(request, "Đã gửi phản hồi.")
                except ValidationError as exc:
                    details = " ".join(str(error) for error in exc.messages)
                    error = f"Chưa gửi được phản hồi: {details}"
            if is_ajax:
                return JsonResponse({"detail": error or "Chưa gửi được phản hồi."}, status=422)
            if error:
                messages.error(request, error)
            return redirect("portal_feedback_thread", pk=thread.pk)
    feedback_messages = list(thread.messages.prefetch_related("reactions").select_related("reply_to", "sender").all())
    for feedback_message in feedback_messages:
        feedback_message.reaction_summary, feedback_message.reaction_total = _feedback_reaction_summary(feedback_message, request.user)
    return render(request, "manage/feedback/thread.html", {
        "thread": thread,
        "feedback_messages": feedback_messages,
        "reaction_choices": FeedbackReaction.Emoji.choices,
    })


def _role_form_groups(form):
    return [(title, [form[name] for name in fields]) for title, fields in ROLE_GROUPS]


@perm_required("add", "roles")
def role_create(request):
    messages.error(request, "Không thể tạo vai trò mới. Hệ thống chỉ cho phép xem và không thể thêm vai trò.")
    return redirect("portal_roles")


@perm_required("change", "roles")
def role_update(request, pk):
    role = get_object_or_404(Role, pk=pk)
    # Vai trò hệ thống chỉ được xem, không sửa
    if role.is_system:
        form = RoleForm(instance=role)
        return render(
            request,
            "manage/roles/form.html",
            {
                "form": form,
                "is_create": False,
                "role": role,
                "role_groups": _role_form_groups(form),
                "readonly": True,
            },
        )
    form = RoleForm(request.POST or None, instance=role)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Đã cập nhật vai trò.")
        return redirect("portal_roles")
    return render(
        request,
        "manage/roles/form.html",
        {"form": form, "is_create": False, "role": role, "role_groups": _role_form_groups(form), "readonly": False},
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
    form = cfg["form"](request.POST or None, request.FILES or None, initial=initial or None)
    if request.method == "POST":
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
        if form.is_valid():
            form.save()
            if is_ajax:
                return JsonResponse({"ok": True})
            messages.success(request, f"Đã thêm {cfg['singular']}.")
            return redirect("portal_entity_list", entity=entity)
        elif is_ajax:
            errors = {}
            for field_name, errs in form.errors.items():
                errors[field_name] = [str(e) for e in errs]
            return JsonResponse({"ok": False, "errors": errors}, status=422)
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
    form = cfg["form"](request.POST or None, request.FILES or None, instance=obj)
    if request.method == "POST":
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
        if form.is_valid():
            form.save()
            if is_ajax:
                return JsonResponse({"ok": True})
            messages.success(request, f"Đã cập nhật {cfg['singular']}.")
            return redirect("portal_entity_list", entity=entity)
        elif is_ajax:
            errors = {}
            for field_name, errs in form.errors.items():
                errors[field_name] = [str(e) for e in errs]
            return JsonResponse({"ok": False, "errors": errors}, status=422)
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


def register_view(request):
    """Start public registration; the User row is created only after email OTP verification."""
    if request.user.is_authenticated:
        return redirect("home")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        otp = f"{secrets.randbelow(1_000_000):06d}"
        now = timezone.now()
        challenge = PendingEmailRegistration(
            email=user.email,
            registration_data={
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                # Django's salted password hash is stored; the plain password is never persisted.
                "password": user.password,
            },
            otp_hash=make_password(otp),
            expires_at=now + timedelta(minutes=10),
            last_sent_at=now,
        )
        try:
            send_mail(
                subject="Mã xác thực đăng ký HCMUNRE WebGIS",
                message=(
                    f"Mã xác thực email của bạn là: {otp}\n\n"
                    "Mã có hiệu lực trong 10 phút. Nếu bạn không thực hiện đăng ký, hãy bỏ qua email này."
                ),
                from_email=None,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception:
            form.add_error(None, "Chưa gửi được email xác thực. Vui lòng thử lại sau hoặc kiểm tra cấu hình email.")
        else:
            # A newer registration for this address invalidates any older pending code.
            PendingEmailRegistration.objects.filter(expires_at__lte=now).delete()
            PendingEmailRegistration.objects.filter(email__iexact=user.email).delete()
            challenge.save()
            request.session["pending_email_registration_id"] = challenge.pk
            return redirect("verify_registration_email")
    return render(request, "registration/register.html", {"form": form})


def verify_registration_email_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    challenge_id = request.session.get("pending_email_registration_id")
    challenge = PendingEmailRegistration.objects.filter(pk=challenge_id).first() if challenge_id else None
    if challenge is None:
        messages.info(request, "Bắt đầu đăng ký để nhận mã xác thực email.")
        return redirect("register")

    error = ""
    if request.method == "POST":
        otp = request.POST.get("otp", "").strip()
        now = timezone.now()
        if now >= challenge.expires_at:
            challenge.delete()
            request.session.pop("pending_email_registration_id", None)
            error = "Mã xác thực đã hết hạn. Vui lòng đăng ký lại để nhận mã mới."
        elif challenge.attempts >= 5:
            challenge.delete()
            request.session.pop("pending_email_registration_id", None)
            error = "Bạn đã nhập sai quá số lần cho phép. Vui lòng đăng ký lại."
        elif not re.fullmatch(r"\d{6}", otp):
            error = "Vui lòng nhập mã OTP gồm đúng 6 chữ số."
        elif not check_password(otp, challenge.otp_hash):
            challenge.attempts += 1
            challenge.save(update_fields=["attempts"])
            error = f"Mã xác thực không đúng. Bạn còn {max(0, 5 - challenge.attempts)} lần thử."
        elif User.objects.filter(email__iexact=challenge.email).exists():
            challenge.delete()
            request.session.pop("pending_email_registration_id", None)
            error = "Email này đã được đăng ký. Vui lòng đăng nhập bằng tài khoản hiện có."
        else:
            data = challenge.registration_data
            try:
                user = User.objects.create(
                    username=data["username"],
                    first_name=data["first_name"],
                    last_name=data["last_name"],
                    email=challenge.email,
                    password=data["password"],
                )
            except (IntegrityError, KeyError):
                challenge.delete()
                request.session.pop("pending_email_registration_id", None)
                error = "Tên đăng nhập đã được sử dụng. Vui lòng đăng ký lại với tên khác."
            else:
                challenge.delete()
                request.session.pop("pending_email_registration_id", None)
                auth_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
                messages.success(request, "Email đã được xác thực. Đăng ký thành công, chào mừng bạn!")
                return redirect("home")

    return render(request, "registration/verify_email.html", {"email": challenge.email, "error": error})


def resend_registration_otp_view(request):
    if request.method != "POST":
        return redirect("verify_registration_email")
    challenge_id = request.session.get("pending_email_registration_id")
    challenge = PendingEmailRegistration.objects.filter(pk=challenge_id).first() if challenge_id else None
    if challenge is None:
        return redirect("register")
    now = timezone.now()
    if challenge.resend_count >= 3:
        messages.error(request, "Bạn đã yêu cầu gửi lại mã quá số lần. Vui lòng đăng ký lại sau.")
    elif now - challenge.last_sent_at < timedelta(seconds=60):
        messages.error(request, "Vui lòng đợi 60 giây trước khi yêu cầu gửi mã mới.")
    else:
        otp = f"{secrets.randbelow(1_000_000):06d}"
        try:
            send_mail(
                "Mã xác thực đăng ký HCMUNRE WebGIS",
                f"Mã xác thực email của bạn là: {otp}\n\nMã có hiệu lực trong 10 phút.",
                None,
                [challenge.email],
                fail_silently=False,
            )
        except Exception:
            messages.error(request, "Chưa gửi được email. Vui lòng thử lại sau hoặc kiểm tra cấu hình email.")
        else:
            challenge.otp_hash = make_password(otp)
            challenge.created_at = now
            challenge.expires_at = now + timedelta(minutes=10)
            challenge.last_sent_at = now
            challenge.attempts = 0
            challenge.resend_count += 1
            challenge.save(update_fields=["otp_hash", "created_at", "expires_at", "last_sent_at", "attempts", "resend_count"])
            messages.success(request, "Đã gửi mã xác thực mới đến email của bạn.")
    return redirect("verify_registration_email")


def password_reset_request_view(request):
    """Send a short-lived OTP without disclosing whether the email is registered."""
    if request.user.is_authenticated:
        return redirect("home")
    form = PasswordResetRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        now = timezone.now()
        request.session.pop("pending_password_reset_id", None)
        user = User.objects.filter(email__iexact=email, is_active=True).first()

        if user:
            challenge = PasswordResetOTP.objects.filter(user=user).order_by("-created_at").first()
            if challenge and challenge.expires_at > now:
                # Reuse the active challenge so repeated form submissions cannot bypass resend limits.
                request.session["pending_password_reset_id"] = challenge.pk
                if challenge.resend_count < 3 and now - challenge.last_sent_at >= timedelta(seconds=60):
                    otp = f"{secrets.randbelow(1_000_000):06d}"
                    try:
                        send_mail(
                            "Mã OTP đặt lại mật khẩu HCMUNRE WebGIS",
                            f"Mã OTP đặt lại mật khẩu của bạn là: {otp}\n\nMã có hiệu lực trong 10 phút.",
                            None,
                            [user.email],
                            fail_silently=False,
                        )
                    except Exception:
                        logger.exception("Could not send password reset OTP")
                    else:
                        challenge.otp_hash = make_password(otp)
                        challenge.created_at = now
                        challenge.expires_at = now + timedelta(minutes=10)
                        challenge.last_sent_at = now
                        challenge.attempts = 0
                        challenge.resend_count += 1
                        challenge.save(update_fields=["otp_hash", "created_at", "expires_at", "last_sent_at", "attempts", "resend_count"])
            else:
                if challenge:
                    challenge.delete()
                otp = f"{secrets.randbelow(1_000_000):06d}"
                try:
                    send_mail(
                        "Mã OTP đặt lại mật khẩu HCMUNRE WebGIS",
                        f"Mã OTP đặt lại mật khẩu của bạn là: {otp}\n\nMã có hiệu lực trong 10 phút.",
                        None,
                        [user.email],
                        fail_silently=False,
                    )
                except Exception:
                    logger.exception("Could not send password reset OTP")
                else:
                    challenge = PasswordResetOTP(
                        user=user,
                        otp_hash=make_password(otp),
                        expires_at=now + timedelta(minutes=10),
                        last_sent_at=now,
                    )
                    challenge.save()
                    request.session["pending_password_reset_id"] = challenge.pk

        messages.success(request, "Nếu email thuộc một tài khoản đang hoạt động, mã OTP sẽ được gửi đến email đó.")
        return redirect("password_reset_verify")
    return render(request, "registration/password_reset_request.html", {"form": form})


def password_reset_verify_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    challenge_id = request.session.get("pending_password_reset_id")
    challenge = PasswordResetOTP.objects.select_related("user").filter(pk=challenge_id).first() if challenge_id else None
    form = PasswordResetConfirmForm(request.POST or None, user=challenge.user if challenge else None)
    error = ""

    if request.method == "POST":
        if challenge is None:
            error = "Mã OTP không đúng, không hợp lệ hoặc đã hết hạn. Hãy yêu cầu mã mới nếu cần."
        elif timezone.now() >= challenge.expires_at:
            challenge.delete()
            request.session.pop("pending_password_reset_id", None)
            error = "Mã OTP không đúng, không hợp lệ hoặc đã hết hạn. Hãy yêu cầu mã mới nếu cần."
        elif challenge.attempts >= 5:
            error = "Mã OTP không đúng, không hợp lệ hoặc đã hết hạn. Hãy yêu cầu mã mới nếu cần."
        elif form.is_valid():
            if not check_password(form.cleaned_data["otp"], challenge.otp_hash):
                challenge.attempts += 1
                challenge.save(update_fields=["attempts"])
                error = "Mã OTP không đúng, không hợp lệ hoặc đã hết hạn. Hãy kiểm tra email hoặc yêu cầu mã mới."
            else:
                challenge.user.set_password(form.cleaned_data["new_password1"])
                challenge.user.save(update_fields=["password"])
                PasswordResetOTP.objects.filter(user=challenge.user).delete()
                request.session.pop("pending_password_reset_id", None)
                messages.success(request, "Đặt lại mật khẩu thành công. Hãy đăng nhập bằng mật khẩu mới.")
                return redirect("login")

    return render(
        request,
        "registration/password_reset_verify.html",
        {"form": form, "email": challenge.user.email if challenge else "", "error": error},
    )


def password_reset_resend_otp_view(request):
    if request.method != "POST":
        return redirect("password_reset_verify")
    challenge_id = request.session.get("pending_password_reset_id")
    challenge = PasswordResetOTP.objects.select_related("user").filter(pk=challenge_id).first() if challenge_id else None
    if challenge is None or not challenge.user.is_active:
        messages.info(request, "Nếu có yêu cầu hợp lệ, mã mới sẽ được gửi khi đủ điều kiện.")
        return redirect("password_reset_verify")

    now = timezone.now()
    if challenge.resend_count < 3 and now - challenge.last_sent_at >= timedelta(seconds=60):
        otp = f"{secrets.randbelow(1_000_000):06d}"
        try:
            send_mail(
                "Mã OTP đặt lại mật khẩu HCMUNRE WebGIS",
                f"Mã OTP đặt lại mật khẩu của bạn là: {otp}\n\nMã có hiệu lực trong 10 phút.",
                None,
                [challenge.user.email],
                fail_silently=False,
            )
        except Exception:
            logger.exception("Could not resend password reset OTP")
        else:
            challenge.otp_hash = make_password(otp)
            challenge.created_at = now
            challenge.expires_at = now + timedelta(minutes=10)
            challenge.last_sent_at = now
            challenge.attempts = 0
            challenge.resend_count += 1
            challenge.save(update_fields=["otp_hash", "created_at", "expires_at", "last_sent_at", "attempts", "resend_count"])
    messages.info(request, "Nếu có yêu cầu hợp lệ, mã mới sẽ được gửi khi đủ điều kiện.")
    return redirect("password_reset_verify")
