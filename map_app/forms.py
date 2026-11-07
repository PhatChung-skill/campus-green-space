from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.contrib.gis.geos import GEOSGeometry
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import (
    Building,
    Campus,
    Floor,
    GreenArea,
    HomepageBlock,
    HomepageFeatureGroup,
    ParkingArea,
    Role,
    Room,
    Tree,
    UserProfile,
)

INPUT_CLASS = {"class": "form-control"}
SELECT_CLASS = {"class": "form-select"}
CHECK_CLASS = {"class": "form-check-input"}
TEXTAREA_CLASS = {"class": "form-control", "rows": 3}
IMAGE_LABELS = {
    "image_1": "Hình 1",
    "image_2": "Hình 2",
    "image_3": "Hình 3",
}
IMAGE_WIDGET = {"class": "form-control-file"}


class PortalLoginForm(AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        "inactive": "Tài khoản của bạn đã bị khóa. Vui lòng liên hệ quản trị viên để được hỗ trợ.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({**INPUT_CLASS, "placeholder": "Tên đăng nhập"})
        self.fields["password"].widget.attrs.update({**INPUT_CLASS, "placeholder": "Mật khẩu"})
        self.fields["username"].label = "Tên đăng nhập"
        self.fields["password"].label = "Mật khẩu"

    def clean(self):
        try:
            return super().clean()
        except ValidationError:
            username = self.cleaned_data.get("username")
            password = self.cleaned_data.get("password")
            if username and password:
                user_model = get_user_model()
                try:
                    user = user_model._default_manager.get_by_natural_key(username)
                except user_model.DoesNotExist:
                    user = None
                if user and not user.is_active and user.check_password(password):
                    raise ValidationError(self.error_messages["inactive"], code="inactive")
            raise


class PersonalPasswordChangeForm(PasswordChangeForm):
    """Đổi mật khẩu cá nhân sau khi xác minh mật khẩu hiện tại."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["old_password"].label = "Mật khẩu hiện tại"
        self.fields["old_password"].error_messages["required"] = "Vui lòng nhập mật khẩu hiện tại."
        self.fields["old_password"].widget.attrs.update(
            {**INPUT_CLASS, "placeholder": "Nhập mật khẩu hiện tại", "autocomplete": "current-password"}
        )
        self.fields["new_password1"].label = "Mật khẩu mới"
        self.fields["new_password1"].error_messages["required"] = "Vui lòng nhập mật khẩu mới."
        self.fields["new_password1"].widget.attrs.update(
            {**INPUT_CLASS, "placeholder": "Nhập mật khẩu mới", "autocomplete": "new-password"}
        )
        self.fields["new_password2"].label = "Xác nhận mật khẩu mới"
        self.fields["new_password2"].error_messages["required"] = "Vui lòng xác nhận mật khẩu mới."
        self.fields["new_password2"].widget.attrs.update(
            {**INPUT_CLASS, "placeholder": "Nhập lại mật khẩu mới", "autocomplete": "new-password"}
        )

    def clean_old_password(self):
        try:
            return super().clean_old_password()
        except ValidationError as error:
            raise ValidationError("Mật khẩu hiện tại không chính xác.", code="password_incorrect") from error

    @staticmethod
    def _vietnamese_password_errors(error):
        localized_messages = []
        for item in error.error_list:
            params = item.params or {}
            if item.code == "password_too_short":
                minimum = params.get("min_length", 8)
                message = f"Mật khẩu quá ngắn. Mật khẩu cần có ít nhất {minimum} ký tự."
            elif item.code == "password_too_common":
                message = "Mật khẩu này quá phổ biến. Hãy chọn mật khẩu khó đoán hơn."
            elif item.code == "password_entirely_numeric":
                message = "Mật khẩu không được chỉ gồm chữ số."
            elif item.code == "password_too_similar":
                message = "Mật khẩu không được quá giống với thông tin cá nhân của bạn."
            else:
                message = "Mật khẩu chưa đáp ứng yêu cầu bảo mật. Vui lòng chọn mật khẩu khác."
            localized_messages.append(message)
        return localized_messages

    def validate_passwords(self, password1_field_name="password1", password2_field_name="password2"):
        password1 = self.cleaned_data.get(password1_field_name)
        password2 = self.cleaned_data.get(password2_field_name)
        if password1 and password2 and password1 != password2:
            self.add_error(password2_field_name, ValidationError(
                "Mật khẩu mới nhập lại không khớp.", code="password_mismatch"
            ))

    def validate_password_for_user(self, user, password_field_name="password2"):
        password = self.cleaned_data.get(password_field_name)
        if not password:
            return
        try:
            validate_password(password, user)
        except ValidationError as error:
            self.add_error(password_field_name, self._vietnamese_password_errors(error))


class HomepageBlockForm(forms.ModelForm):
    FIELDS_BY_KIND = {
        "header": ("title", "body", "image", "image_alt", "sort_order", "is_active"),
        "hero": ("eyebrow", "title", "body", "image", "image_alt", "button_label", "button_url", "sort_order", "is_active"),
        "intro": ("eyebrow", "title", "body", "image", "image_alt", "sort_order", "is_active"),
        "feature": ("group_title", "title", "body", "image", "image_alt", "button_label", "button_url", "sort_order", "is_active"),
        "footer": ("title", "body", "button_label", "button_url", "sort_order", "is_active"),
    }

    def __init__(self, *args, kind=None, **kwargs):
        instance = kwargs.get("instance")
        super().__init__(*args, **kwargs)
        kind = kind or getattr(instance, "kind", None)
        if kind in self.FIELDS_BY_KIND:
            field_names = self.FIELDS_BY_KIND[kind]
            self.fields = {name: self.fields[name] for name in field_names if name != "group_title"}
            if kind == HomepageBlock.Kind.FEATURE:
                group_title = forms.CharField(
                    label="Tiêu đề nhóm tiện ích",
                    max_length=220,
                    help_text="Nhập tên nhóm đã có để thêm thẻ vào nhóm đó. Đổi tên tại đây sẽ cập nhật tên cho tất cả thẻ cùng nhóm.",
                    widget=forms.TextInput(attrs={**INPUT_CLASS, "placeholder": "Ví dụ: Khám phá tiện ích trong khuôn viên"}),
                )
                current_group = getattr(instance, "feature_group", None)
                if current_group:
                    group_title.initial = current_group.title
                else:
                    previous_group = HomepageFeatureGroup.objects.order_by("sort_order", "pk").first()
                    group_title.initial = previous_group.title if previous_group else "Khám phá tiện ích trong khuôn viên"
                self.fields = {"group_title": group_title, **self.fields}
            if kind and not self.instance.pk:
                self.instance.kind = kind

    def clean_group_title(self):
        title = self.cleaned_data.get("group_title", "").strip()
        current_group = getattr(self.instance, "feature_group", None)
        duplicate = HomepageFeatureGroup.objects.filter(title__iexact=title)
        if current_group:
            duplicate = duplicate.exclude(pk=current_group.pk)
        if current_group and title and duplicate.exists():
            raise ValidationError("Tên này đã được dùng bởi một nhóm khác. Hãy dùng đúng tên nhóm đó hoặc chọn tên mới.")
        return title

    def save(self, commit=True):
        block = super().save(commit=False)
        if block.kind == HomepageBlock.Kind.FEATURE:
            title = self.cleaned_data["group_title"]
            current_group = getattr(self.instance, "feature_group", None)
            if commit:
                with transaction.atomic():
                    if current_group:
                        current_group.title = title
                        current_group.save()
                        group = current_group
                    else:
                        group = HomepageFeatureGroup.objects.filter(title__iexact=title).first()
                        if group is None:
                            group = HomepageFeatureGroup.objects.create(title=title)
                    block.feature_group = group
                    block.save()
                return block
            if current_group:
                block.feature_group = current_group
            else:
                block._pending_feature_group_title = title
        if commit:
            block.save()
        return block

    class Meta:
        model = HomepageBlock
        fields = [
            "eyebrow", "title", "body", "image", "image_alt",
            "button_label", "button_url", "sort_order", "is_active",
        ]
        widgets = {
            "eyebrow": forms.TextInput(attrs=INPUT_CLASS),
            "title": forms.TextInput(attrs=INPUT_CLASS),
            "body": forms.Textarea(attrs={**TEXTAREA_CLASS, "rows": 5}),
            "image": forms.ClearableFileInput(attrs=IMAGE_WIDGET),
            "image_alt": forms.TextInput(attrs=INPUT_CLASS),
            "button_label": forms.TextInput(attrs=INPUT_CLASS),
            "button_url": forms.TextInput(attrs=INPUT_CLASS),
            "sort_order": forms.NumberInput(attrs=INPUT_CLASS),
            "is_active": forms.CheckboxInput(attrs=CHECK_CLASS),
        }


class GeomModelForm(forms.ModelForm):
    geom_geojson = forms.CharField(widget=forms.HiddenInput(), required=False)
    geom_type = "Polygon"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.geom:
            self.fields["geom_geojson"].initial = self.instance.geom.geojson
        for field in self.fields.values():
            if isinstance(field, forms.ModelChoiceField):
                field.empty_label = "— Chọn —"

    def clean(self):
        cleaned = super().clean()
        raw = (cleaned.get("geom_geojson") or "").strip()
        if not raw:
            raise ValidationError({"geom_geojson": "Vui lòng vẽ hoặc chọn vị trí trên bản đồ."})
        try:
            geom = GEOSGeometry(raw)
        except Exception as exc:
            raise ValidationError({"geom_geojson": f"Dữ liệu bản đồ không hợp lệ: {exc}"}) from exc
        expected = self.geom_type
        if expected == "Polygon" and geom.geom_type not in ("Polygon", "MultiPolygon"):
            raise ValidationError({"geom_geojson": "Cần vẽ một vùng (đa giác) trên bản đồ."})
        if expected == "Point" and geom.geom_type != "Point":
            raise ValidationError({"geom_geojson": "Cần chọn một điểm trên bản đồ."})
        geom.srid = 4326
        cleaned["geom"] = geom
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.geom = self.cleaned_data["geom"]
        if commit:
            obj.save()
        return obj


class CampusForm(GeomModelForm):
    geom_type = "Polygon"

    class Meta:
        model = Campus
        fields = ["name", "image_1", "image_2", "image_3"]
        labels = IMAGE_LABELS
        widgets = {
            "name": forms.TextInput(attrs=INPUT_CLASS),
            "image_1": forms.ClearableFileInput(attrs=IMAGE_WIDGET),
            "image_2": forms.ClearableFileInput(attrs=IMAGE_WIDGET),
            "image_3": forms.ClearableFileInput(attrs=IMAGE_WIDGET),
        }


class BuildingForm(GeomModelForm):
    geom_type = "Polygon"

    class Meta:
        model = Building
        fields = ["campus", "name", "image_1", "image_2", "image_3"]
        labels = IMAGE_LABELS
        widgets = {
            "campus": forms.Select(attrs=SELECT_CLASS),
            "name": forms.TextInput(attrs=INPUT_CLASS),
            "image_1": forms.ClearableFileInput(attrs=IMAGE_WIDGET),
            "image_2": forms.ClearableFileInput(attrs=IMAGE_WIDGET),
            "image_3": forms.ClearableFileInput(attrs=IMAGE_WIDGET),
        }

    def clean(self):
        cleaned_data = super().clean()
        campus = cleaned_data.get("campus")
        name = cleaned_data.get("name")
        if campus and name and "name" not in self.errors:
            qs = Building.objects.filter(campus=campus, name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error(
                    "name",
                    f"Tòa nhà \"{name}\" đã tồn tại trong cơ sở \"{campus.name}\". "
                    "Vui lòng đặt tên khác.",
                )
        return cleaned_data

    def validate_unique(self):
        # clean() đã xử lý → bỏ qua lỗi model-level generic để tránh phá layout
        try:
            super().validate_unique()
        except forms.ValidationError:
            pass


class FloorForm(GeomModelForm):
    geom_type = "Polygon"

    class Meta:
        model = Floor
        fields = ["building", "level", "name", "blueprint_url"]
        widgets = {
            "building": forms.Select(attrs=SELECT_CLASS),
            "level": forms.NumberInput(attrs={**INPUT_CLASS, "min": "0"}),
            "name": forms.TextInput(attrs=INPUT_CLASS),
            "blueprint_url": forms.TextInput(attrs={**INPUT_CLASS, "placeholder": "https://..."}),
        }

    def clean_level(self):
        level = self.cleaned_data.get("level")
        if level is not None and level < 0:
            raise forms.ValidationError(
                "Cấp độ tầng không được là số âm. Vui lòng nhập số từ 0 trở lên."
            )
        return level

    def clean(self):
        cleaned_data = super().clean()
        building = cleaned_data.get("building")
        level = cleaned_data.get("level")
        if building and level is not None and "level" not in self.errors:
            qs = Floor.objects.filter(building=building, level=level)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error(
                    "level",
                    f"Tầng {level} đã tồn tại trong tòa nhà \"{building.name}\". "
                    "Vui lòng chọn cấp độ tầng khác.",
                )
        return cleaned_data

    def validate_unique(self):
        # clean() đã xử lý → bỏ qua lỗi model-level generic để tránh phá layout
        try:
            super().validate_unique()
        except forms.ValidationError:
            pass


class RoomForm(GeomModelForm):
    # ── Virtual fields cho cascade lọc: không lưu vào DB ──
    campus_filter = forms.ModelChoiceField(
        queryset=Campus.objects.all(),
        required=False,
        label="Lọc theo cơ sở",
        widget=forms.Select(attrs=SELECT_CLASS),
    )
    building_filter = forms.ModelChoiceField(
        queryset=Building.objects.all(),
        required=False,
        label="Lọc theo tòa nhà",
        widget=forms.Select(attrs=SELECT_CLASS),
    )


    geom_type = "Point"

    # Thứ tự hiển thị: cascade trước, floor sau
    field_order = ["campus_filter", "building_filter", "floor", "name", "room_type",
                   "image_1", "image_2", "image_3"]

    class Meta:
        model = Room
        fields = ["floor", "name", "room_type", "description", "image_1", "image_2", "image_3"]
        labels = IMAGE_LABELS
        widgets = {
            "floor": forms.Select(attrs=SELECT_CLASS),
            "name": forms.TextInput(attrs=INPUT_CLASS),
            "room_type": forms.Select(attrs=SELECT_CLASS),
            "description": forms.Textarea(attrs={**TEXTAREA_CLASS, "placeholder": "Mô tả thêm về phòng này…"}),
            "image_1": forms.ClearableFileInput(attrs=IMAGE_WIDGET),
            "image_2": forms.ClearableFileInput(attrs=IMAGE_WIDGET),
            "image_3": forms.ClearableFileInput(attrs=IMAGE_WIDGET),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-populate virtual fields khi đang edit phòng hiện có
        if self.instance and self.instance.pk:
            try:
                floor = self.instance.floor
                self.fields["building_filter"].initial = floor.building_id
                self.fields["campus_filter"].initial   = floor.building.campus_id
            except Exception:
                pass

    def clean(self):
        cleaned_data = super().clean()
        floor = cleaned_data.get("floor")
        name = cleaned_data.get("name")
        if floor and name and "name" not in self.errors:
            qs = Room.objects.filter(floor=floor, name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error(
                    "name",
                    f"Phòng \"{name}\" đã tồn tại trong tầng \"{floor.name}\". "
                    "Vui lòng đặt tên phòng khác.",
                )
        return cleaned_data

    def validate_unique(self):
        # clean() đã kiểm tra và đưa lỗi vào field cụ thể → bỏ qua lỗi model-level generic
        try:
            super().validate_unique()
        except forms.ValidationError:
            pass



class ParkingAreaForm(GeomModelForm):
    geom_type = "Polygon"

    class Meta:
        model = ParkingArea
        fields = ["campus", "name", "capacity", "description", "image_1", "image_2", "image_3"]
        labels = IMAGE_LABELS
        widgets = {
            "campus": forms.Select(attrs=SELECT_CLASS),
            "name": forms.TextInput(attrs=INPUT_CLASS),
            "capacity": forms.NumberInput(attrs={**INPUT_CLASS, "min": "0"}),
            "description": forms.Textarea(attrs={**TEXTAREA_CLASS, "placeholder": "Mô tả thêm về bãi xe này…"}),
            "image_1": forms.ClearableFileInput(attrs=IMAGE_WIDGET),
            "image_2": forms.ClearableFileInput(attrs=IMAGE_WIDGET),
            "image_3": forms.ClearableFileInput(attrs=IMAGE_WIDGET),
        }

    def clean_capacity(self):
        capacity = self.cleaned_data.get("capacity")
        if capacity is not None and capacity < 0:
            raise forms.ValidationError(
                "Sức chứa không được là số âm. Vui lòng nhập số từ 0 trở lên."
            )
        return capacity

    def clean(self):
        cleaned_data = super().clean()
        campus = cleaned_data.get("campus")
        name = cleaned_data.get("name")
        if campus and name and "name" not in self.errors:
            qs = ParkingArea.objects.filter(campus=campus, name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error(
                    "name",
                    f"Bãi xe \"{name}\" đã tồn tại trong cơ sở \"{campus.name}\".",
                )
        return cleaned_data


class GreenAreaForm(GeomModelForm):
    geom_type = "Polygon"

    class Meta:
        model = GreenArea
        fields = ["campus", "name", "type", "description", "image_1", "image_2", "image_3"]
        labels = IMAGE_LABELS
        widgets = {
            "campus": forms.Select(attrs=SELECT_CLASS),
            "name": forms.TextInput(attrs=INPUT_CLASS),
            "type": forms.Select(attrs=SELECT_CLASS),
            "description": forms.Textarea(attrs={**TEXTAREA_CLASS, "placeholder": "Mô tả thêm về khu vực xanh này…"}),
            "image_1": forms.ClearableFileInput(attrs=IMAGE_WIDGET),
            "image_2": forms.ClearableFileInput(attrs=IMAGE_WIDGET),
            "image_3": forms.ClearableFileInput(attrs=IMAGE_WIDGET),
        }

    def clean(self):
        cleaned_data = super().clean()
        campus = cleaned_data.get("campus")
        name = cleaned_data.get("name")
        if campus and name and "name" not in self.errors:
            qs = GreenArea.objects.filter(campus=campus, name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error(
                    "name",
                    f"Mảng xanh \"{name}\" đã tồn tại trong cơ sở \"{campus.name}\".",
                )
        return cleaned_data


class TreeForm(GeomModelForm):
    geom_type = "Point"

    class Meta:
        model = Tree
        fields = ["campus", "species", "health_status", "description", "image_1", "image_2", "image_3"]
        labels = IMAGE_LABELS
        widgets = {
            "campus": forms.Select(attrs=SELECT_CLASS),
            "species": forms.TextInput(attrs=INPUT_CLASS),
            "health_status": forms.Select(attrs=SELECT_CLASS),
            "description": forms.Textarea(attrs={**TEXTAREA_CLASS, "placeholder": "Mô tả thêm về cây này…"}),
            "image_1": forms.ClearableFileInput(attrs=IMAGE_WIDGET),
            "image_2": forms.ClearableFileInput(attrs=IMAGE_WIDGET),
            "image_3": forms.ClearableFileInput(attrs=IMAGE_WIDGET),
        }



ROLE_CHECKBOX_FIELDS = [
    "can_access_portal",
    "can_view_users",
    "can_add_users",
    "can_change_users",
    "can_delete_users",
    "can_view_roles",
    "can_add_roles",
    "can_change_roles",
    "can_delete_roles",
    "can_view_campus",
    "can_add_campus",
    "can_change_campus",
    "can_delete_campus",
    "can_view_building",
    "can_add_building",
    "can_change_building",
    "can_delete_building",
    "can_view_floor",
    "can_add_floor",
    "can_change_floor",
    "can_delete_floor",
    "can_view_room",
    "can_add_room",
    "can_change_room",
    "can_delete_room",
    "can_view_parking",
    "can_add_parking",
    "can_change_parking",
    "can_delete_parking",
    "can_view_greenarea",
    "can_add_greenarea",
    "can_change_greenarea",
    "can_delete_greenarea",
    "can_view_tree",
    "can_add_tree",
    "can_change_tree",
    "can_delete_tree",
    "can_manage_feedback",
]


class RoleForm(forms.ModelForm):
    class Meta:
        model = Role
        fields = ["name", "description"] + ROLE_CHECKBOX_FIELDS
        widgets = {
            "name": forms.TextInput(attrs=INPUT_CLASS),
            "description": forms.Textarea(attrs=TEXTAREA_CLASS),
            **{f: forms.CheckboxInput(attrs=CHECK_CLASS) for f in ROLE_CHECKBOX_FIELDS},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.is_system:
            self.fields["name"].widget.attrs["readonly"] = True


class UserCreateForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Mật khẩu",
        widget=forms.PasswordInput(attrs=INPUT_CLASS),
    )
    password2 = forms.CharField(
        label="Nhập lại mật khẩu",
        widget=forms.PasswordInput(attrs=INPUT_CLASS),
    )
    role = forms.ModelChoiceField(
        queryset=Role.objects.all(),
        required=True,
        label="Vai trò",
        widget=forms.Select(attrs=SELECT_CLASS),
    )
    notes = forms.CharField(
        required=False,
        label="Ghi chú",
        widget=forms.Textarea(attrs=TEXTAREA_CLASS),
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "is_active"]
        labels = {
            "username": "Tên đăng nhập",
            "first_name": "Họ",
            "last_name": "Tên",
            "email": "Email",
            "is_active": "Tài khoản đang hoạt động",
        }
        widgets = {
            "username": forms.TextInput(attrs=INPUT_CLASS),
            "first_name": forms.TextInput(attrs=INPUT_CLASS),
            "last_name": forms.TextInput(attrs=INPUT_CLASS),
            "email": forms.EmailInput(attrs=INPUT_CLASS),
            "is_active": forms.CheckboxInput(attrs=CHECK_CLASS),
        }

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Mật khẩu nhập lại không khớp.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        role = self.cleaned_data["role"]
        user.is_staff = role.can_access_portal
        if commit:
            user.save()
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.notes = self.cleaned_data.get("notes", "")
            profile.save()
        return user


class UserUpdateForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Mật khẩu mới (để trống nếu giữ nguyên)",
        required=False,
        widget=forms.PasswordInput(attrs=INPUT_CLASS),
    )
    password2 = forms.CharField(
        label="Nhập lại mật khẩu mới",
        required=False,
        widget=forms.PasswordInput(attrs=INPUT_CLASS),
    )
    role = forms.ModelChoiceField(
        queryset=Role.objects.all(),
        required=True,
        label="Vai trò",
        widget=forms.Select(attrs=SELECT_CLASS),
    )
    notes = forms.CharField(
        required=False,
        label="Ghi chú",
        widget=forms.Textarea(attrs=TEXTAREA_CLASS),
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "is_active"]
        labels = {
            "username": "Tên đăng nhập",
            "first_name": "Họ",
            "last_name": "Tên",
            "email": "Email",
            "is_active": "Tài khoản đang hoạt động",
        }
        widgets = {
            "username": forms.TextInput(attrs=INPUT_CLASS),
            "first_name": forms.TextInput(attrs=INPUT_CLASS),
            "last_name": forms.TextInput(attrs=INPUT_CLASS),
            "email": forms.EmailInput(attrs=INPUT_CLASS),
            "is_active": forms.CheckboxInput(attrs=CHECK_CLASS),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        profile = getattr(self.instance, "profile", None)
        if profile:
            self.fields["role"].initial = profile.role_id
            self.fields["notes"].initial = profile.notes

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 or p2:
            if p1 != p2:
                self.add_error("password2", "Mật khẩu nhập lại không khớp.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        p1 = self.cleaned_data.get("password1")
        if p1:
            user.set_password(p1)
        role = self.cleaned_data["role"]
        user.is_staff = role.can_access_portal
        if commit:
            user.save()
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.notes = self.cleaned_data.get("notes", "")
            profile.save()
        return user


class RegisterForm(forms.ModelForm):
    """Form đăng ký tài khoản công khai — role tự động gán là 'Khách'."""

    password1 = forms.CharField(
        label="Mật khẩu",
        widget=forms.PasswordInput(attrs={**INPUT_CLASS, "placeholder": "Ít nhất 8 ký tự"}),
    )
    password2 = forms.CharField(
        label="Nhập lại mật khẩu",
        widget=forms.PasswordInput(attrs={**INPUT_CLASS, "placeholder": "Nhập lại mật khẩu"}),
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]
        labels = {
            "username": "Tên đăng nhập",
            "first_name": "Họ",
            "last_name": "Tên",
            "email": "Email",
        }
        widgets = {
            "username": forms.TextInput(attrs={**INPUT_CLASS, "placeholder": "Tên đăng nhập"}),
            "first_name": forms.TextInput(attrs={**INPUT_CLASS, "placeholder": "Họ"}),
            "last_name": forms.TextInput(attrs={**INPUT_CLASS, "placeholder": "Tên"}),
            "email": forms.EmailInput(attrs={**INPUT_CLASS, "placeholder": "email@example.com"}),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        if email and User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Email này đã được dùng bởi tài khoản khác.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Mật khẩu nhập lại không khớp.")
        if p1 and len(p1) < 8:
            self.add_error("password1", "Mật khẩu phải có ít nhất 8 ký tự.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            # Signal ensure_user_profile sẽ tự tạo profile với role "Khách"
        return user


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        label="Email tài khoản",
        error_messages={
            "required": "Vui lòng nhập email tài khoản.",
            "invalid": "Vui lòng nhập địa chỉ email hợp lệ.",
        },
        widget=forms.EmailInput(attrs={**INPUT_CLASS, "autocomplete": "email", "placeholder": "email@example.com"}),
    )

    def clean_email(self):
        return self.cleaned_data["email"].strip()


class PasswordResetConfirmForm(forms.Form):
    otp = forms.RegexField(
        regex=r"^\d{6}$",
        label="Mã OTP 6 chữ số",
        error_messages={
            "required": "Vui lòng nhập mã OTP.",
            "invalid": "Vui lòng nhập mã OTP gồm đúng 6 chữ số.",
        },
        widget=forms.TextInput(attrs={
            **INPUT_CLASS,
            "inputmode": "numeric",
            "autocomplete": "one-time-code",
            "maxlength": "6",
            "placeholder": "Nhập mã OTP",
        }),
    )
    new_password1 = forms.CharField(
        label="Mật khẩu mới",
        error_messages={"required": "Vui lòng nhập mật khẩu mới."},
        widget=forms.PasswordInput(attrs={**INPUT_CLASS, "autocomplete": "new-password"}),
    )
    new_password2 = forms.CharField(
        label="Nhập lại mật khẩu mới",
        error_messages={"required": "Vui lòng nhập lại mật khẩu mới."},
        widget=forms.PasswordInput(attrs={**INPUT_CLASS, "autocomplete": "new-password"}),
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_new_password1(self):
        password = self.cleaned_data["new_password1"]
        try:
            validate_password(password, user=self.user)
        except ValidationError as error:
            messages = []
            for item in error.error_list:
                code = item.code
                if code == "password_too_short":
                    minimum = item.params.get("min_length", 8)
                    message = f"Mật khẩu quá ngắn. Mật khẩu phải có ít nhất {minimum} ký tự."
                elif code == "password_too_common":
                    message = "Mật khẩu này quá phổ biến. Vui lòng chọn mật khẩu khó đoán hơn."
                elif code == "password_entirely_numeric":
                    message = "Mật khẩu không được chỉ gồm chữ số."
                elif code == "password_too_similar":
                    message = "Mật khẩu quá giống thông tin tài khoản của bạn. Vui lòng chọn mật khẩu khác."
                else:
                    message = "Mật khẩu chưa đáp ứng yêu cầu bảo mật. Vui lòng chọn mật khẩu khác."
                messages.append(ValidationError(message, code=code))
            raise ValidationError(messages)
        return password

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("new_password1")
        password2 = cleaned.get("new_password2")
        if password1 and password2 and password1 != password2:
            self.add_error("new_password2", "Hai mật khẩu không khớp.")
        return cleaned
