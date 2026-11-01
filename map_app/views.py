import json
import mimetypes
import re
import unicodedata

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.serializers import serialize
from django.db.models import Prefetch, Q
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET

from .models import Building, Campus, FeedbackMessage, FeedbackReaction, FeedbackThread, Floor, GreenArea, HomepageBlock, HomepageFeatureGroup, ParkingArea, Room, Tree
from .permissions import can_access_portal, user_has_perm


def homepage_view(request):
    blocks = HomepageBlock.objects.filter(is_active=True)
    active_features = HomepageBlock.objects.filter(kind=HomepageBlock.Kind.FEATURE, is_active=True).order_by("sort_order", "pk")
    feature_groups = [
        {"group": group, "features": group.active_blocks}
        for group in HomepageFeatureGroup.objects.filter(
            is_active=True,
            blocks__kind=HomepageBlock.Kind.FEATURE,
            blocks__is_active=True,
        ).distinct().order_by("sort_order", "pk").prefetch_related(
            Prefetch("blocks", queryset=active_features, to_attr="active_blocks")
        )
    ]
    return render(
        request,
        "map_app/homepage.html",
        {
            "hero": blocks.filter(kind=HomepageBlock.Kind.HERO).first(),
            "intro": blocks.filter(kind=HomepageBlock.Kind.INTRO).first(),
            "feature_groups": feature_groups,
            "footer": blocks.filter(kind=HomepageBlock.Kind.FOOTER).first(),
        },
    )


def _feedback_message_json(message, user):
    totals = {}
    reacted = set()
    for reaction in message.reactions.all():
        totals[reaction.emoji] = totals.get(reaction.emoji, 0) + 1
        if reaction.user_id == user.pk:
            reacted.add(reaction.emoji)
    reply_data = None
    if message.reply_to_id and message.reply_to:
        if message.reply_to.sender_id == user.pk:
            reply_sender = "Bạn"
        elif message.reply_to.is_staff_reply:
            reply_sender = message.reply_to.sender_name or "Nhân viên hỗ trợ"
        else:
            reply_sender = message.reply_to.sender_name or "Khách"
        reply_data = {
            "id": message.reply_to.pk,
            "sender": reply_sender,
            "body": message.reply_to.snippet,
            "has_image": bool(message.reply_to.image),
        }
    return {
        "id": message.pk,
        "sender": message.sender_name,
        "is_staff": message.is_staff_reply,
        "body": message.body,
        "image": reverse("feedback_image", args=[message.pk]) if message.image else "",
        "created_at": timezone.localtime(message.created_at).strftime("%I:%M %p · %d/%m/%Y"),
        "reactions": [
            {"emoji": emoji, "count": totals.get(emoji, 0), "reacted": emoji in reacted}
            for emoji in FeedbackReaction.Emoji.values
        ],
        "reply_to": reply_data,
    }


@login_required
def feedback_api(request):
    if can_access_portal(request.user):
        return JsonResponse({"detail": "Kênh gửi góp ý dành cho tài khoản khách."}, status=403)
    thread = FeedbackThread.objects.filter(user=request.user).first()
    if request.method == "GET":
        return JsonResponse({
            "messages": [_feedback_message_json(item, request.user) for item in thread.messages.prefetch_related("reactions").select_related("reply_to").all()] if thread else [],
            "category": thread.category if thread else FeedbackThread.Category.FEEDBACK,
            "has_unread": bool(thread and thread.user_read_at is None),
        })
    if request.method != "POST":
        return JsonResponse({"detail": "Phương thức không được hỗ trợ."}, status=405)

    if request.POST.get("action") == "mark_read":
        if thread and thread.user_read_at is None:
            thread.user_read_at = timezone.now()
            thread.save(update_fields=["user_read_at"])
        return JsonResponse({"ok": True})

    if request.POST.get("action") == "react":
        if not thread:
            return JsonResponse({"detail": "Chưa có hội thoại để thả cảm xúc."}, status=404)
        emoji = request.POST.get("emoji", "")
        if emoji not in FeedbackReaction.Emoji.values:
            return JsonResponse({"detail": "Emoji không hợp lệ."}, status=422)
        try:
            message_id = int(request.POST.get("message_id", ""))
        except (TypeError, ValueError):
            return JsonResponse({"detail": "Tin nhắn không hợp lệ."}, status=422)
        message = get_object_or_404(thread.messages.prefetch_related("reactions"), pk=message_id)
        reaction, created = FeedbackReaction.objects.get_or_create(message=message, user=request.user, emoji=emoji)
        if not created:
            reaction.delete()
        thread.user_read_at = timezone.now()
        thread.save(update_fields=["user_read_at"])
        message = thread.messages.prefetch_related("reactions").select_related("reply_to").get(pk=message.pk)
        return JsonResponse({"message": _feedback_message_json(message, request.user)})

    body = request.POST.get("body", "").strip()
    image = request.FILES.get("image")
    category = request.POST.get("category", FeedbackThread.Category.FEEDBACK)
    if len(body) > 3000:
        return JsonResponse({"detail": "Nội dung tối đa 3.000 ký tự."}, status=422)
    if not body and not image:
        return JsonResponse({"detail": "Hãy nhập nội dung hoặc đính kèm hình ảnh."}, status=422)
    if image and image.size > 5 * 1024 * 1024:
        return JsonResponse({"detail": "Hình ảnh tối đa 5 MB."}, status=422)
    if not thread and category not in FeedbackThread.Category.values:
        return JsonResponse({"detail": "Loại góp ý không hợp lệ."}, status=422)
    try:
        if image:
            FeedbackMessage._meta.get_field("image").clean(image, None)
    except ValidationError:
        return JsonResponse({"detail": "Tệp gửi lên không hợp lệ. Hãy dùng hình PNG, JPG hoặc WEBP."}, status=422)
    if not thread:
        thread = FeedbackThread.objects.create(
            user=request.user,
            username_snapshot=(request.user.get_full_name() or request.user.get_username())[:150],
            category=category,
        )
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
        reply_to=reply_to,
        body=body,
        image=image or "",
    )
    try:
        message.full_clean()
        message.save()
    except ValidationError:
        return JsonResponse({"detail": "Tệp gửi lên không hợp lệ. Hãy dùng hình PNG, JPG hoặc WEBP."}, status=422)
    thread.staff_read_at = None
    thread.user_read_at = timezone.now()
    thread.save(update_fields=["staff_read_at", "user_read_at", "updated_at"])
    message = FeedbackMessage.objects.prefetch_related("reactions").select_related("reply_to").get(pk=message.pk)
    return JsonResponse({"message": _feedback_message_json(message, request.user)}, status=201)


@login_required
@require_GET
def feedback_image(request, pk):
    message = get_object_or_404(FeedbackMessage.objects.select_related("thread"), pk=pk)
    allowed_as_staff = can_access_portal(request.user) and user_has_perm(request.user, "manage", "feedback")
    if message.thread.user_id != request.user.pk and not allowed_as_staff:
        raise Http404
    if not message.image:
        raise Http404
    try:
        image_file = message.image.open("rb")
    except FileNotFoundError:
        raise Http404
    content_type = mimetypes.guess_type(message.image.name)[0] or "application/octet-stream"
    return FileResponse(image_file, content_type=content_type)


@login_required
def account_view(request):
    profile = getattr(request.user, "profile", None)
    return render(request, "map_app/account.html", {"profile": profile})


def map_view(request):
    # Tính số thứ tự cơ sở theo thứ tự tên (thay vì dùng PK tự tăng)
    campus_qs = list(Campus.objects.order_by("name"))
    campus_order_map = {c.pk: idx + 1 for idx, c in enumerate(campus_qs)}

    campuses_geojson_data = json.loads(serialize(
        "geojson", campus_qs, geometry_field="geom",
        fields=["pk", "name", "image_1", "image_2", "image_3"],
    ))
    # Gắn thêm campus_order vào properties
    for feat in campuses_geojson_data.get("features", []):
        pk = feat.get("id") or feat["properties"].get("pk")
        feat["properties"]["campus_order"] = campus_order_map.get(pk, "")

    context = {
        "campuses_geojson": json.dumps(campuses_geojson_data),
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
            fields=["name", "capacity", "description", "campus", "image_1", "image_2", "image_3"],
        ),
        "greens_geojson": serialize(
            "geojson",
            GreenArea.objects.select_related("campus").all(),
            geometry_field="geom",
            fields=["name", "type", "description", "campus", "image_1", "image_2", "image_3"],
        ),
        "trees_geojson": serialize(
            "geojson",
            Tree.objects.select_related("campus").all(),
            geometry_field="geom",
            fields=["species", "health_status", "description", "campus", "image_1", "image_2", "image_3"],
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
                  fields=["name", "room_type", "description", "floor", "image_1", "image_2", "image_3"])
    )
    return JsonResponse(data)



# ─────────────────────────────────────────────────────────────────
# SMART SEARCH ENGINE — hỗ trợ tìm kiếm kết hợp đa trường
# Ví dụ: "WC tầng 1 cơ sở Lê Văn Sỹ", "phòng học A101 cơ sở 2"
# ─────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────
# SMART SEARCH ENGINE — Hỗ trợ tìm kiếm kết hợp đa trường
# Không phụ thuộc thứ tự từ khoá: "A103 Lê Văn Sỹ" == "Lê Văn Sỹ A103"
# ─────────────────────────────────────────────────────────────────

ROOM_TYPE_KEYWORDS = [
    ("nha ve sinh", "wc"), ("ve sinh", "wc"), ("toilet", "wc"), ("wc", "wc"),
    ("phong hoc", "classroom"), ("lop hoc", "classroom"), ("giang duong", "classroom"), ("classroom", "classroom"),
    ("thuc hanh", "lab"), ("thi nghiem", "lab"), ("lab", "lab"),
    ("van phong", "office"), ("hanh chinh", "office"), ("office", "office"),
]

GREEN_TYPE_KEYWORDS = [
    ("tham co", "grass"), ("bai co", "grass"), ("grass", "grass"),
    ("vuon hoa", "garden"), ("cay canh", "garden"), ("garden", "garden"),
]

STOP_WORDS = {
    'phong', 'toa', 'bai', 'xe', 'cay', 'khu', 'tang', 'co', 'so',
    'va', 'la', 'cac', 'cua', 'trong', 'cho', 'duoc', 'o', 'tai', 'nhu', 'thuoc'
}


def _normalize(text):
    """Chuẩn hoá chuỗi tiếng Việt: chữ thường, không dấu để so khớp không phụ thuộc dấu."""
    if not text:
        return ""
    text = unicodedata.normalize('NFD', str(text))
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    text = text.replace('đ', 'd').replace('Đ', 'd')
    return re.sub(r'\s+', ' ', text).strip().lower()


def _detect_level_from_str(s):
    """Tìm số tầng trong chuỗi. VD: 'tang 1' hoặc 'tầng 2' → 1 hoặc 2."""
    m = re.search(r'\bt[aâă]ng\s*(\d+)', s)
    if m:
        return int(m.group(1))
    return None


def match_entity(query_text, query_words, name_norm, desc_norm=""):
    """
    So khớp văn bản đối tượng theo nguyên từ / tiền tố / chuỗi con:
    - 2500: Khớp chính xác 100%
    - 2200: Khớp nguyên cụm từ hoàn chỉnh (có ranh giới từ 2 đầu)
    - 2000: Khớp tiền tố từ (bắt đầu tại ranh giới từ, vd: 'a20' khớp 'a201', 'a202')
    - 1800: Khớp chuỗi số/mã hiệu nằm trong tên (vd: '20' trong 'a201', '103' trong 'a103')
    - 1600: Tất cả các từ đều có trong tên (hoặc là tiền tố của từ trong tên)
    - 1400: Cụm từ là chuỗi con trong tên
    - 1100: Có từ quan trọng trong tên
    - 600-700: Khớp trong mô tả
    """
    if not query_text:
        return 0

    name_words = set(name_norm.split())

    # 1. Khớp chính xác 100%
    if name_norm == query_text:
        return 2500

    # 2. Khớp cụm từ hoàn chỉnh (có ranh giới từ 2 đầu)
    pattern_full = r'(?<!\w)' + re.escape(query_text) + r'(?!\w)'
    if re.search(pattern_full, name_norm):
        return 2200

    # 3. Khớp tiền tố từ (bắt đầu tại ranh giới từ, vd: 'a20' khớp 'a201', 'a202')
    pattern_prefix = r'(?<!\w)' + re.escape(query_text)
    if re.search(pattern_prefix, name_norm):
        return 2000

    # 4. Khớp chuỗi số/mã hiệu nằm trong tên (vd: '20' trong 'a201', '103' trong 'a103')
    if any(c.isdigit() for c in query_text) and query_text in name_norm:
        return 1800

    # 5. Tất cả các từ đều có trong tên (hoặc là tiền tố của từ trong tên)
    if query_words and len(query_words) > 1:
        all_words_matched = True
        for w in query_words:
            if not any(nw.startswith(w) for nw in name_words):
                all_words_matched = False
                break
        if all_words_matched:
            return 1600

    # 6. Chuỗi con thông thường (>= 2 ký tự, không phải stop word)
    if query_text in name_norm and len(query_text) >= 2 and query_text not in STOP_WORDS:
        return 1400

    # 7. Có từ quan trọng trong tên (>= 2 ký tự, không phải stop word)
    matched = [w for w in query_words if any(nw.startswith(w) for nw in name_words) and w not in STOP_WORDS and len(w) >= 2]
    if matched:
        return 1000 + len(matched) * 100

    # 8. So khớp mô tả
    if desc_norm:
        if re.search(pattern_full, desc_norm) or re.search(pattern_prefix, desc_norm):
            return 700
        desc_words = set(desc_norm.split())
        if query_words and len(query_words) > 1 and query_words.issubset(desc_words):
            return 600
        matched_desc = [w for w in query_words if w in desc_words and w not in STOP_WORDS and len(w) >= 3]
        if matched_desc:
            return 400 + len(matched_desc) * 100

    return 0


def map_search(request):
    """
    Smart Search API — Tìm kiếm kết hợp thông minh & So khớp bộ lọc đa năng:
    - Bất kể thứ tự từ khóa: 'A103 Lê Văn Sỹ' == 'Lê Văn Sỹ A103'.
    - Tự động nhận diện Cơ sở, Tòa nhà, Tầng, Loại phòng từ Database.
    - Tìm kiếm tiền tố/tên phòng: 'A20' hiển thị A201, A202...
    - Tìm kiếm tên cây (cây bàng, bàng, bàng 2...) hiển thị chính xác.
    - Tìm kiếm bãi xe linh hoạt (xe hơi, xe học sinh, học sinh, bãi xe...).
    - Tìm kiếm mảng xanh (bãi cỏ, vườn hoa, hoa lan...).
    - Sắp xếp kết quả liên quan nhất lên đầu tiên.
    """
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse({"results": [], "hint": ""})

    # Lấy cơ sở đang chọn từ dropdown (nếu có)
    campus_id_param = request.GET.get("campus_id")
    selected_campus = None
    if campus_id_param:
        try:
            selected_campus = Campus.objects.get(pk=campus_id_param)
        except (Campus.DoesNotExist, ValueError):
            pass

    q_norm = _normalize(q)
    HEALTH = {"good": "✅ Phát triển tốt", "needs_care": "⚠️ Cần chăm sóc"}
    ROOM_TYPE_LABELS = {
        "classroom": "📚 Phòng học", "lab": "🔬 Thực hành / Lab",
        "wc": "🚻 Nhà vệ sinh", "office": "💼 Văn phòng",
    }
    GREEN_LABELS = {"grass": "🌿 Thảm cỏ", "garden": "🌸 Vườn hoa / Cây cảnh"}

    # ── 1. NHẬN DIỆN CƠ SỞ (CAMPUS) TỪ DATABASE ──
    all_campuses = list(Campus.objects.all())
    matched_campus = None
    for c in sorted(all_campuses, key=lambda x: len(x.name), reverse=True):
        c_norm = _normalize(c.name)
        if c_norm and (re.search(r'(?<!\w)' + re.escape(c_norm) + r'(?!\w)', q_norm) or f"co so {c_norm}" in q_norm):
            matched_campus = c
            break

    # ── 2. NHẬN DIỆN TÒA NHÀ (BUILDING) TỪ DATABASE ──
    bld_qs = Building.objects.filter(campus=matched_campus) if matched_campus else Building.objects.all()
    all_buildings = list(bld_qs.select_related("campus"))
    matched_building = None
    for b in sorted(all_buildings, key=lambda x: len(x.name), reverse=True):
        b_norm = _normalize(b.name)
        if b_norm and re.search(r'(?<!\w)' + re.escape(b_norm) + r'(?!\w)', q_norm):
            matched_building = b
            break

    # ── 3. NHẬN DIỆN TẦNG, LOẠI PHÒNG, LOẠI MẢNG XANH ──
    detected_level = _detect_level_from_str(q_norm)

    detected_room_type = None
    matched_room_kw = None
    for kw, code in ROOM_TYPE_KEYWORDS:
        kw_norm = _normalize(kw)
        if re.search(r'(?<!\w)' + re.escape(kw_norm) + r'(?!\w)', q_norm):
            detected_room_type = code
            matched_room_kw = kw_norm
            break

    detected_green_type = None
    matched_green_kw = None
    for kw, code in GREEN_TYPE_KEYWORDS:
        kw_norm = _normalize(kw)
        if re.search(r'(?<!\w)' + re.escape(kw_norm) + r'(?!\w)', q_norm):
            detected_green_type = code
            matched_green_kw = kw_norm
            break

    # ── 4. TRÍCH XUẤT TỪ KHÓA TÌM KIẾM ──
    rem = q_norm
    if matched_campus:
        rem = rem.replace(_normalize(matched_campus.name), " ")
    if matched_building:
        rem = rem.replace(_normalize(matched_building.name), " ")
    for stop in ["co so", "toa nha", "toa", "tang", "khu vuc", "o", "tai", "thuoc"]:
        rem = re.sub(r'(?<!\w)' + re.escape(stop) + r'(?!\w)', ' ', rem)
    if detected_level is not None:
        rem = re.sub(r'\b\d+\b', ' ', rem, count=1)

    clean_term = re.sub(r'\s+', ' ', rem).strip()

    # Core term loại bỏ các tiền tố loại hình đối tượng
    core_term = clean_term
    for prefix in ["bai xe", "phong", "cay xanh", "mang xanh"]:
        core_term = re.sub(r'(?<!\w)' + re.escape(prefix) + r'(?!\w)', ' ', core_term)
    if matched_room_kw:
        core_term = re.sub(r'(?<!\w)' + re.escape(matched_room_kw) + r'(?!\w)', ' ', core_term)
    if matched_green_kw:
        core_term = re.sub(r'(?<!\w)' + re.escape(matched_green_kw) + r'(?!\w)', ' ', core_term)
    core_term = re.sub(r'\s+', ' ', core_term).strip()

    is_tree_query = ('cay' in clean_term.split()) or ('cay xanh' in q_norm)
    is_parking_query = ('bai xe' in q_norm) or ('xe' in clean_term.split())
    is_green_query = ('mang xanh' in q_norm) or ('co' in clean_term.split()) or ('vuon' in clean_term.split()) or (detected_green_type is not None)

    if detected_room_type or detected_green_type or is_tree_query or is_parking_query:
        target_phrase = core_term
    else:
        target_phrase = core_term or clean_term

    target_words = set(target_phrase.split()) if target_phrase else set()

    has_specific_filter = bool(target_phrase or detected_room_type or detected_level or detected_green_type or is_tree_query or is_parking_query)

    results = []

    # ════════════════════════════════════════════════════
    # 1. TÌM PHÒNG (ROOM)
    # ════════════════════════════════════════════════════
    room_qs = Room.objects.select_related("floor__building__campus")
    if matched_campus:
        room_qs = room_qs.filter(floor__building__campus=matched_campus)
    if matched_building:
        room_qs = room_qs.filter(floor__building=matched_building)
    if detected_level is not None:
        room_qs = room_qs.filter(floor__level=detected_level)
    if detected_room_type:
        room_qs = room_qs.filter(room_type=detected_room_type)

    for obj in room_qs:
        if not obj.geom:
            continue
        fl = obj.floor
        bld = fl.building if fl else None
        campus = bld.campus if bld else None
        campus_name = campus.name if campus else ""
        floor_name = fl.name or f"Tầng {fl.level}" if fl else ""

        name_norm = _normalize(obj.name)
        desc_norm = _normalize(obj.description)
        score = 0
        if detected_room_type and obj.room_type == detected_room_type:
            score = 2000
            if target_phrase:
                score += match_entity(target_phrase, target_words, name_norm, desc_norm)
        elif target_phrase:
            score = match_entity(target_phrase, target_words, name_norm, desc_norm)
        elif not has_specific_filter:
            score = 400

        if score > 0:
            if matched_campus and campus == matched_campus:
                score += 200
            elif selected_campus and campus == selected_campus:
                score += 150
            if matched_building and bld == matched_building:
                score += 100
            if detected_level is not None and fl and fl.level == detected_level:
                score += 200

            results.append({
                "type": "room", "label": "Phòng", "icon": "🚪",
                "id": obj.pk, "name": obj.name,
                "campus": campus_name, "campus_pk": campus.pk if campus else None,
                "building_id": bld.pk if bld else None,
                "building_name": bld.name if bld else "",
                "floor_id": fl.pk if fl else None,
                "floor_name": floor_name,
                "room_type": obj.room_type,
                "room_type_label": ROOM_TYPE_LABELS.get(obj.room_type, obj.room_type),
                "lat": obj.geom.y, "lng": obj.geom.x, "_score": score,
                "images": [
                    obj.image_1.name if obj.image_1 else None,
                    obj.image_2.name if obj.image_2 else None,
                    obj.image_3.name if obj.image_3 else None,
                ],
            })

    # ════════════════════════════════════════════════════
    # 2. BÃI XE (PARKING)
    # ════════════════════════════════════════════════════
    park_qs = ParkingArea.objects.select_related("campus")
    if matched_campus:
        park_qs = park_qs.filter(campus=matched_campus)

    for obj in park_qs:
        if not obj.geom:
            continue
        c = obj.geom.centroid
        campus_name = obj.campus.name if obj.campus else ""
        name_norm = _normalize(obj.name)
        desc_norm = _normalize(obj.description)
        score = 0
        if target_phrase:
            score = match_entity(target_phrase, target_words, name_norm, desc_norm)
        elif is_parking_query:
            score = 2000
        elif not has_specific_filter:
            score = 500

        if score > 0:
            if matched_campus and obj.campus == matched_campus:
                score += 200
            elif selected_campus and obj.campus == selected_campus:
                score += 150
            results.append({
                "type": "parking", "label": "Bãi xe", "icon": "🅿️",
                "id": obj.pk, "name": obj.name,
                "campus": campus_name, "campus_pk": obj.campus_id,
                "capacity": obj.capacity,
                "description": obj.description,
                "lat": c.y, "lng": c.x, "_score": score,
                "images": [
                    obj.image_1.name if obj.image_1 else None,
                    obj.image_2.name if obj.image_2 else None,
                    obj.image_3.name if obj.image_3 else None,
                ],
            })

    # ════════════════════════════════════════════════════
    # 3. CÂY XANH (TREE)
    # ════════════════════════════════════════════════════
    tree_qs = Tree.objects.select_related("campus")
    if matched_campus:
        tree_qs = tree_qs.filter(campus=matched_campus)

    for obj in tree_qs:
        if not obj.geom:
            continue
        campus_name = obj.campus.name if obj.campus else ""
        spec_norm = _normalize(obj.species)
        desc_norm = _normalize(obj.description)
        score = 0

        tree_target = target_phrase
        if tree_target.startswith("cay "):
            tree_target_core = tree_target[4:].strip()
        else:
            tree_target_core = tree_target

        if tree_target:
            score = match_entity(tree_target, target_words, spec_norm, desc_norm)
            if score == 0 and tree_target_core:
                score = match_entity(tree_target_core, set(tree_target_core.split()), spec_norm, desc_norm)
        elif is_tree_query:
            score = 2000
        elif not has_specific_filter:
            score = 500

        if score > 0:
            if matched_campus and obj.campus == matched_campus:
                score += 200
            elif selected_campus and obj.campus == selected_campus:
                score += 150
            results.append({
                "type": "tree", "label": "Cây xanh", "icon": "🌳",
                "id": obj.pk, "name": obj.species or "Cây xanh",
                "campus": campus_name, "campus_pk": obj.campus_id,
                "health": HEALTH.get(obj.health_status, obj.health_status),
                "description": obj.description,
                "lat": obj.geom.y, "lng": obj.geom.x, "_score": score,
                "images": [
                    obj.image_1.name if obj.image_1 else None,
                    obj.image_2.name if obj.image_2 else None,
                    obj.image_3.name if obj.image_3 else None,
                ],
            })

    # ════════════════════════════════════════════════════
    # 4. MẢNG XANH (GREEN)
    # ════════════════════════════════════════════════════
    green_qs = GreenArea.objects.select_related("campus")
    if matched_campus:
        green_qs = green_qs.filter(campus=matched_campus)

    for obj in green_qs:
        if not obj.geom:
            continue
        c = obj.geom.centroid
        campus_name = obj.campus.name if obj.campus else ""
        name_norm = _normalize(obj.name)
        desc_norm = _normalize(obj.description)
        score = 0
        if detected_green_type and obj.type == detected_green_type:
            score = 2000
            if target_phrase:
                score += match_entity(target_phrase, target_words, name_norm, desc_norm)
        elif target_phrase:
            score = match_entity(target_phrase, target_words, name_norm, desc_norm)
        elif is_green_query:
            score = 1800
        elif not has_specific_filter:
            score = 500

        if score > 0:
            if matched_campus and obj.campus == matched_campus:
                score += 200
            elif selected_campus and obj.campus == selected_campus:
                score += 150
            results.append({
                "type": "green", "label": "Mảng xanh", "icon": "🌿",
                "id": obj.pk, "name": obj.name,
                "campus": campus_name, "campus_pk": obj.campus_id,
                "lat": c.y, "lng": c.x,
                "detail_type": GREEN_LABELS.get(obj.type, obj.type),
                "description": obj.description,
                "_score": score,
                "images": [
                    obj.image_1.name if obj.image_1 else None,
                    obj.image_2.name if obj.image_2 else None,
                    obj.image_3.name if obj.image_3 else None,
                ],
            })

    # ════════════════════════════════════════════════════
    # 5. TÒA NHÀ (BUILDING)
    # ════════════════════════════════════════════════════
    bld_candidates = Building.objects.select_related("campus")
    if matched_campus:
        bld_candidates = bld_candidates.filter(campus=matched_campus)

    for obj in bld_candidates:
        if not obj.geom:
            continue
        c = obj.geom.centroid
        campus_name = obj.campus.name if obj.campus else ""
        name_norm = _normalize(obj.name)
        score = 0
        if matched_building and obj == matched_building:
            score = 2200 if not target_phrase else 1400
        elif target_phrase:
            score = match_entity(target_phrase, target_words, name_norm)
        elif not has_specific_filter:
            score = 600

        if score > 0:
            if matched_campus and obj.campus == matched_campus:
                score += 200
            elif selected_campus and obj.campus == selected_campus:
                score += 150
            results.append({
                "type": "building", "label": "Tòa nhà", "icon": "🏢",
                "id": obj.pk, "name": obj.name,
                "campus": campus_name, "campus_pk": obj.campus_id,
                "lat": c.y, "lng": c.x, "_score": score,
                "images": [
                    obj.image_1.name if obj.image_1 else None,
                    obj.image_2.name if obj.image_2 else None,
                    obj.image_3.name if obj.image_3 else None,
                ],
            })

    # ════════════════════════════════════════════════════
    # 6. TẦNG (FLOOR)
    # ════════════════════════════════════════════════════
    if detected_level is not None:
        floor_qs = Floor.objects.select_related("building__campus")
        if matched_campus:
            floor_qs = floor_qs.filter(building__campus=matched_campus)
        if matched_building:
            floor_qs = floor_qs.filter(building=matched_building)
        floor_qs = floor_qs.filter(level=detected_level)

        for obj in floor_qs:
            if not obj.geom:
                continue
            c = obj.geom.centroid
            bld = obj.building
            campus_name = bld.campus.name if bld and bld.campus else ""
            score = 1600 if not target_phrase else 1000
            if matched_campus and bld and bld.campus == matched_campus:
                score += 200
            elif selected_campus and bld and bld.campus == selected_campus:
                score += 150
            if matched_building and bld == matched_building:
                score += 100

            results.append({
                "type": "floor", "label": "Tầng", "icon": "📐",
                "id": obj.pk, "name": obj.name or f"Tầng {obj.level}",
                "campus": campus_name, "campus_pk": bld.campus_id if bld else None,
                "building_id": obj.building_id,
                "building_name": bld.name if bld else "",
                "level": obj.level,
                "lat": c.y, "lng": c.x, "_score": score,
            })

    # ════════════════════════════════════════════════════
    # 7. KHUÔN VIÊN (CAMPUS)
    # ════════════════════════════════════════════════════
    if matched_campus and not has_specific_filter:
        if matched_campus.geom:
            c = matched_campus.geom.centroid
            results.append({
                "type": "campus", "label": "Khuôn viên", "icon": "🏫",
                "id": matched_campus.pk, "name": matched_campus.name, "campus": matched_campus.name,
                "lat": c.y, "lng": c.x, "_score": 1500,
                "images": [
                    matched_campus.image_1.name if matched_campus.image_1 else None,
                    matched_campus.image_2.name if matched_campus.image_2 else None,
                    matched_campus.image_3.name if matched_campus.image_3 else None,
                ],
            })
    elif not has_specific_filter:
        for obj in Campus.objects.all():
            if not obj.geom:
                continue
            name_norm = _normalize(obj.name)
            score = match_entity(target_phrase, target_words, name_norm) if target_phrase else 0
            if score > 0:
                c = obj.geom.centroid
                results.append({
                    "type": "campus", "label": "Khuôn viên", "icon": "🏫",
                    "id": obj.pk, "name": obj.name, "campus": obj.name,
                    "lat": c.y, "lng": c.x, "_score": score,
                    "images": [
                        obj.image_1.name if obj.image_1 else None,
                        obj.image_2.name if obj.image_2 else None,
                        obj.image_3.name if obj.image_3 else None,
                    ],
                })

    # ── Sắp xếp theo điểm relevance giảm dần, sau đó theo tên A-Z ──
    results.sort(key=lambda x: (-x.get("_score", 0), x.get("name", "")))

    # Giới hạn tối đa 25 kết quả tốt nhất
    results = results[:25]

    # Loại bỏ thuộc tính tạm _score trước khi trả về
    for r in results:
        r.pop("_score", None)

    # ── Gợi ý lọc ──
    hints = []
    if matched_campus:
        hints.append(f"Cơ sở: {matched_campus.name}")
    if matched_building:
        hints.append(f"Tòa nhà: {matched_building.name}")
    if detected_room_type:
        hints.append(f"Loại phòng: {ROOM_TYPE_LABELS.get(detected_room_type, detected_room_type)}")
    if detected_level is not None:
        hints.append(f"Tầng {detected_level}")
    if detected_green_type:
        hints.append(f"Mảng xanh: {GREEN_LABELS.get(detected_green_type, detected_green_type)}")
    if is_parking_query:
        hints.append("Bãi xe")
    if is_tree_query:
        hints.append("Cây xanh")

    hint_str = " · ".join(hints) if hints else ""
    return JsonResponse({"results": results, "hint": hint_str})




# ─────────────────────────────────────────────────────────────────
# THỐNG KÊ KHÔNG GIAN XANH — Green Space Analytics API
# Tính diện tích chính xác bằng cách chuyển hệ tọa độ sang UTM 48N
# (EPSG:32648) phù hợp Việt Nam trước khi gọi hàm tính diện tích
# của PostGIS, đơn vị kết quả: mét vuông (m²).
# ─────────────────────────────────────────────────────────────────

from django.contrib.gis.db.models.functions import Area, Transform
from django.db.models import Sum as _Sum


def _total_area_m2(qs, geom_field="geom"):
    """Tổng diện tích (m²) của queryset sau khi chuyển sang EPSG:32648."""
    result = qs.annotate(
        area_m2=Area(Transform(geom_field, 32648))
    ).aggregate(total=_Sum("area_m2"))
    val = result.get("total")
    if val is None:
        return 0.0
    # Area() trả về đối tượng có thuộc tính .sq_m (mét vuông)
    return float(val.sq_m) if hasattr(val, "sq_m") else float(val)


def _pct(part, total):
    if total <= 0:
        return 0.0
    return round(part / total * 100, 2)


def green_space_stats(request):
    """
    GET /api/thong-ke-xanh/?campus_id=<pk>

    Trả về JSON thống kê diện tích khuôn viên / mảng xanh / tòa nhà.
    Nếu không truyền campus_id thì thống kê tổng hợp tất cả cơ sở.
    """
    campus_id = request.GET.get("campus_id")

    if campus_id:
        campus_qs   = Campus.objects.filter(pk=campus_id)
        building_qs = Building.objects.filter(campus_id=campus_id)
        green_qs    = GreenArea.objects.filter(campus_id=campus_id)
        tree_qs     = Tree.objects.filter(campus_id=campus_id)
    else:
        campus_qs   = Campus.objects.all()
        building_qs = Building.objects.all()
        green_qs    = GreenArea.objects.all()
        tree_qs     = Tree.objects.all()

    campus_area   = _total_area_m2(campus_qs)
    building_area = _total_area_m2(building_qs)
    green_area    = _total_area_m2(green_qs)
    yard_area     = max(0.0, campus_area - building_area - green_area)

    green_pct    = _pct(green_area,    campus_area)
    building_pct = _pct(building_area, campus_area)
    yard_pct     = _pct(yard_area,     campus_area)

    # Thống kê số lượng cây xanh
    total_trees = tree_qs.count()
    good_trees  = tree_qs.filter(health_status="good").count()
    care_trees  = tree_qs.filter(health_status="needs_care").count()

    # Đánh giá tự động theo ngưỡng 30%
    threshold_good = 30
    threshold_warn = 15
    if green_pct >= threshold_good:
        evaluation = "✅ Tỷ lệ không gian xanh đạt chuẩn (≥ 30%)"
        eval_level = "good"
    elif green_pct >= threshold_warn:
        evaluation = "⚠️ Tỷ lệ khá thấp, cần bổ sung thêm mảng xanh"
        eval_level = "warning"
    else:
        evaluation = "🔴 Tỷ lệ thấp, cần quy hoạch bổ sung không gian xanh"
        eval_level = "bad"

    # Chi tiết từng cơ sở
    campuses_data = []
    for c in campus_qs.order_by("name"):
        ca = _total_area_m2(Campus.objects.filter(pk=c.pk))
        ba = _total_area_m2(Building.objects.filter(campus=c))
        ga = _total_area_m2(GreenArea.objects.filter(campus=c))
        ya = max(0.0, ca - ba - ga)
        c_trees = Tree.objects.filter(campus=c)
        campuses_data.append({
            "id":           c.pk,
            "name":         c.name,
            "campus_area":  round(ca, 2),
            "green_area":   round(ga, 2),
            "building_area":round(ba, 2),
            "yard_area":    round(ya, 2),
            "green_pct":    _pct(ga, ca),
            "building_pct": _pct(ba, ca),
            "yard_pct":     _pct(ya, ca),
            "trees": {
                "total": c_trees.count(),
                "good": c_trees.filter(health_status="good").count(),
                "needs_care": c_trees.filter(health_status="needs_care").count(),
            },
        })

    return JsonResponse({
        "campus_area":   round(campus_area, 2),
        "green_area":    round(green_area, 2),
        "building_area": round(building_area, 2),
        "yard_area":     round(yard_area, 2),
        "green_pct":     green_pct,
        "building_pct":  building_pct,
        "yard_pct":      yard_pct,
        "evaluation":    evaluation,
        "eval_level":    eval_level,
        "trees": {
            "total": total_trees,
            "good": good_trees,
            "needs_care": care_trees,
        },
        "campuses":      campuses_data,
    })
