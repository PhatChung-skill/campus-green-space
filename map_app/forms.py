from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.gis.geos import GEOSGeometry
from django.core.exceptions import ValidationError

from .models import (
    Building,
    Campus,
    Floor,
    GreenArea,
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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({**INPUT_CLASS, "placeholder": "Tên đăng nhập"})
        self.fields["password"].widget.attrs.update({**INPUT_CLASS, "placeholder": "Mật khẩu"})
        self.fields["username"].label = "Tên đăng nhập"
        self.fields["password"].label = "Mật khẩu"


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


class FloorForm(GeomModelForm):
    geom_type = "Polygon"

    class Meta:
        model = Floor
        fields = ["building", "level", "name", "blueprint_url"]
        widgets = {
            "building": forms.Select(attrs=SELECT_CLASS),
            "level": forms.NumberInput(attrs=INPUT_CLASS),
            "name": forms.TextInput(attrs=INPUT_CLASS),
            "blueprint_url": forms.TextInput(attrs={**INPUT_CLASS, "placeholder": "https://..."}),
        }


class RoomForm(GeomModelForm):
    geom_type = "Point"

    class Meta:
        model = Room
        fields = ["floor", "name", "room_type", "image_1", "image_2", "image_3"]
        labels = IMAGE_LABELS
        widgets = {
            "floor": forms.Select(attrs=SELECT_CLASS),
            "name": forms.TextInput(attrs=INPUT_CLASS),
            "room_type": forms.Select(attrs=SELECT_CLASS),
            "image_1": forms.ClearableFileInput(attrs=IMAGE_WIDGET),
            "image_2": forms.ClearableFileInput(attrs=IMAGE_WIDGET),
            "image_3": forms.ClearableFileInput(attrs=IMAGE_WIDGET),
        }


class ParkingAreaForm(GeomModelForm):
    geom_type = "Polygon"

    class Meta:
        model = ParkingArea
        fields = ["campus", "name", "capacity", "image_1", "image_2", "image_3"]
        labels = IMAGE_LABELS
        widgets = {
            "campus": forms.Select(attrs=SELECT_CLASS),
            "name": forms.TextInput(attrs=INPUT_CLASS),
            "capacity": forms.NumberInput(attrs=INPUT_CLASS),
            "image_1": forms.ClearableFileInput(attrs=IMAGE_WIDGET),
            "image_2": forms.ClearableFileInput(attrs=IMAGE_WIDGET),
            "image_3": forms.ClearableFileInput(attrs=IMAGE_WIDGET),
        }


class GreenAreaForm(GeomModelForm):
    geom_type = "Polygon"

    class Meta:
        model = GreenArea
        fields = ["campus", "name", "type", "image_1", "image_2", "image_3"]
        labels = IMAGE_LABELS
        widgets = {
            "campus": forms.Select(attrs=SELECT_CLASS),
            "name": forms.TextInput(attrs=INPUT_CLASS),
            "type": forms.Select(attrs=SELECT_CLASS),
            "image_1": forms.ClearableFileInput(attrs=IMAGE_WIDGET),
            "image_2": forms.ClearableFileInput(attrs=IMAGE_WIDGET),
            "image_3": forms.ClearableFileInput(attrs=IMAGE_WIDGET),
        }


class TreeForm(GeomModelForm):
    geom_type = "Point"

    class Meta:
        model = Tree
        fields = ["campus", "species", "health_status", "image_1", "image_2", "image_3"]
        labels = IMAGE_LABELS
        widgets = {
            "campus": forms.Select(attrs=SELECT_CLASS),
            "species": forms.TextInput(attrs=INPUT_CLASS),
            "health_status": forms.Select(attrs=SELECT_CLASS),
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
    phone = forms.CharField(
        required=False,
        label="Số điện thoại",
        widget=forms.TextInput(attrs=INPUT_CLASS),
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
            profile.phone = self.cleaned_data.get("phone", "")
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
    phone = forms.CharField(
        required=False,
        label="Số điện thoại",
        widget=forms.TextInput(attrs=INPUT_CLASS),
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
            self.fields["phone"].initial = profile.phone
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
            profile.phone = self.cleaned_data.get("phone", "")
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
