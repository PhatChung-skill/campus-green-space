from django.conf import settings
from django.contrib.gis.db import models

# ==========================================
# NHÓM 1: KHÔNG GIAN HẠ TẦNG (INFRASTRUCTURE)
# ==========================================

class Campus(models.Model):
    campus_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, verbose_name="Tên cơ sở")
    geom = models.PolygonField(srid=4326, verbose_name="Ranh giới khuôn viên")
    image_1 = models.ImageField(upload_to="campus/", blank=True, null=True, verbose_name="Hình 1")
    image_2 = models.ImageField(upload_to="campus/", blank=True, null=True, verbose_name="Hình 2")
    image_3 = models.ImageField(upload_to="campus/", blank=True, null=True, verbose_name="Hình 3")

    def __str__(self):
        return self.name

class Building(models.Model):
    building_id = models.AutoField(primary_key=True)
    campus = models.ForeignKey(Campus, on_delete=models.CASCADE, related_name='buildings')
    name = models.CharField(max_length=255, verbose_name="Tên tòa nhà")
    geom = models.PolygonField(srid=4326, verbose_name="Hình dạng tòa nhà")
    image_1 = models.ImageField(upload_to="building/", blank=True, null=True, verbose_name="Hình 1")
    image_2 = models.ImageField(upload_to="building/", blank=True, null=True, verbose_name="Hình 2")
    image_3 = models.ImageField(upload_to="building/", blank=True, null=True, verbose_name="Hình 3")

    def __str__(self):
        return f"{self.name} - {self.campus.name}"

class Floor(models.Model):
    floor_id = models.AutoField(primary_key=True)
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='floors')
    level = models.IntegerField(verbose_name="Cấp độ tầng")
    name = models.CharField(max_length=255, verbose_name="Tên tầng")
    geom = models.PolygonField(srid=4326, verbose_name="Ranh giới tầng")
    blueprint_url = models.TextField(blank=True, null=True, verbose_name="Link bản vẽ mặt bằng")

    def __str__(self):
        return f"{self.name} ({self.building.name})"

class Room(models.Model):
    ROOM_TYPES = [
        ('classroom', 'Phòng học'),
        ('lab', 'Phòng thực hành / Lab'),
        ('wc', 'Nhà vệ sinh'),
        ('office', 'Văn phòng'),
    ]
    room_id = models.AutoField(primary_key=True)
    floor = models.ForeignKey(Floor, on_delete=models.CASCADE, related_name='rooms')
    name = models.CharField(max_length=255, verbose_name="Tên phòng")
    room_type = models.CharField(max_length=50, choices=ROOM_TYPES, verbose_name="Loại phòng")
    geom = models.PointField(srid=4326, verbose_name="Tọa độ phòng")
    image_1 = models.ImageField(upload_to="room/", blank=True, null=True, verbose_name="Hình 1")
    image_2 = models.ImageField(upload_to="room/", blank=True, null=True, verbose_name="Hình 2")
    image_3 = models.ImageField(upload_to="room/", blank=True, null=True, verbose_name="Hình 3")

    def __str__(self):
        return self.name

class ParkingArea(models.Model):
    parking_id = models.AutoField(primary_key=True)
    campus = models.ForeignKey(Campus, on_delete=models.CASCADE, related_name='parkings')
    name = models.CharField(max_length=255, verbose_name="Tên bãi xe")
    capacity = models.IntegerField(verbose_name="Sức chứa dự kiến", blank=True, null=True)
    geom = models.PolygonField(srid=4326, verbose_name="Ranh giới bãi xe")
    image_1 = models.ImageField(upload_to="parking/", blank=True, null=True, verbose_name="Hình 1")
    image_2 = models.ImageField(upload_to="parking/", blank=True, null=True, verbose_name="Hình 2")
    image_3 = models.ImageField(upload_to="parking/", blank=True, null=True, verbose_name="Hình 3")

    def __str__(self):
        return self.name

# ==========================================
# NHÓM 2: KHÔNG GIAN SINH THÁI (GREEN SPACE)
# ==========================================

class GreenArea(models.Model):
    GREEN_TYPES = [
        ('grass', 'Thảm cỏ'),
        ('garden', 'Vườn hoa / Cây cảnh'),
    ]
    area_id = models.AutoField(primary_key=True)
    campus = models.ForeignKey(Campus, on_delete=models.CASCADE, related_name='green_areas')
    name = models.CharField(max_length=255, verbose_name="Tên khu vực xanh")
    type = models.CharField(max_length=50, choices=GREEN_TYPES, verbose_name="Loại mảng xanh")
    geom = models.PolygonField(srid=4326, verbose_name="Diện tích phủ xanh")
    image_1 = models.ImageField(upload_to="greenarea/", blank=True, null=True, verbose_name="Hình 1")
    image_2 = models.ImageField(upload_to="greenarea/", blank=True, null=True, verbose_name="Hình 2")
    image_3 = models.ImageField(upload_to="greenarea/", blank=True, null=True, verbose_name="Hình 3")

    def __str__(self):
        return self.name

class Tree(models.Model):
    HEALTH_STATUS = [
        ('good', 'Phát triển tốt'),
        ('needs_care', 'Cần chăm sóc / Cắt tỉa'),
    ]
    tree_id = models.AutoField(primary_key=True)
    campus = models.ForeignKey(Campus, on_delete=models.CASCADE, related_name='trees')
    species = models.CharField(max_length=255, verbose_name="Giống cây")
    health_status = models.CharField(max_length=50, choices=HEALTH_STATUS, verbose_name="Tình trạng")
    geom = models.PointField(srid=4326, verbose_name="Tọa độ gốc cây")
    image_1 = models.ImageField(upload_to="tree/", blank=True, null=True, verbose_name="Hình 1")
    image_2 = models.ImageField(upload_to="tree/", blank=True, null=True, verbose_name="Hình 2")
    image_3 = models.ImageField(upload_to="tree/", blank=True, null=True, verbose_name="Hình 3")

    def __str__(self):
        return f"Cây {self.species} - ID: {self.tree_id}"


# ==========================================
# NHÓM 3: NGƯỜI DÙNG & VAI TRÒ
# ==========================================

class Role(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Tên vai trò")
    description = models.TextField(blank=True, verbose_name="Mô tả")
    is_system = models.BooleanField(default=False, verbose_name="Vai trò hệ thống")

    can_access_portal = models.BooleanField(default=False, verbose_name="Truy cập trang quản lý")

    can_view_users = models.BooleanField(default=False, verbose_name="Xem người dùng")
    can_add_users = models.BooleanField(default=False, verbose_name="Thêm người dùng")
    can_change_users = models.BooleanField(default=False, verbose_name="Sửa người dùng")
    can_delete_users = models.BooleanField(default=False, verbose_name="Xóa người dùng")

    can_view_roles = models.BooleanField(default=False, verbose_name="Xem vai trò")
    can_add_roles = models.BooleanField(default=False, verbose_name="Thêm vai trò")
    can_change_roles = models.BooleanField(default=False, verbose_name="Sửa vai trò")
    can_delete_roles = models.BooleanField(default=False, verbose_name="Xóa vai trò")

    can_view_campus = models.BooleanField(default=False, verbose_name="Xem cơ sở")
    can_add_campus = models.BooleanField(default=False, verbose_name="Thêm cơ sở")
    can_change_campus = models.BooleanField(default=False, verbose_name="Sửa cơ sở")
    can_delete_campus = models.BooleanField(default=False, verbose_name="Xóa cơ sở")

    can_view_building = models.BooleanField(default=False, verbose_name="Xem tòa nhà")
    can_add_building = models.BooleanField(default=False, verbose_name="Thêm tòa nhà")
    can_change_building = models.BooleanField(default=False, verbose_name="Sửa tòa nhà")
    can_delete_building = models.BooleanField(default=False, verbose_name="Xóa tòa nhà")

    can_view_floor = models.BooleanField(default=False, verbose_name="Xem tầng")
    can_add_floor = models.BooleanField(default=False, verbose_name="Thêm tầng")
    can_change_floor = models.BooleanField(default=False, verbose_name="Sửa tầng")
    can_delete_floor = models.BooleanField(default=False, verbose_name="Xóa tầng")

    can_view_room = models.BooleanField(default=False, verbose_name="Xem phòng")
    can_add_room = models.BooleanField(default=False, verbose_name="Thêm phòng")
    can_change_room = models.BooleanField(default=False, verbose_name="Sửa phòng")
    can_delete_room = models.BooleanField(default=False, verbose_name="Xóa phòng")

    can_view_parking = models.BooleanField(default=False, verbose_name="Xem bãi xe")
    can_add_parking = models.BooleanField(default=False, verbose_name="Thêm bãi xe")
    can_change_parking = models.BooleanField(default=False, verbose_name="Sửa bãi xe")
    can_delete_parking = models.BooleanField(default=False, verbose_name="Xóa bãi xe")

    can_view_greenarea = models.BooleanField(default=False, verbose_name="Xem mảng xanh")
    can_add_greenarea = models.BooleanField(default=False, verbose_name="Thêm mảng xanh")
    can_change_greenarea = models.BooleanField(default=False, verbose_name="Sửa mảng xanh")
    can_delete_greenarea = models.BooleanField(default=False, verbose_name="Xóa mảng xanh")

    can_view_tree = models.BooleanField(default=False, verbose_name="Xem cây xanh")
    can_add_tree = models.BooleanField(default=False, verbose_name="Thêm cây xanh")
    can_change_tree = models.BooleanField(default=False, verbose_name="Sửa cây xanh")
    can_delete_tree = models.BooleanField(default=False, verbose_name="Xóa cây xanh")

    class Meta:
        verbose_name = "Vai trò"
        verbose_name_plural = "Vai trò"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def has_perm(self, action, resource):
        return bool(getattr(self, f"can_{action}_{resource}", False))


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="Tài khoản",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="Vai trò",
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name="Số điện thoại")
    notes = models.TextField(blank=True, verbose_name="Ghi chú")

    class Meta:
        verbose_name = "Hồ sơ người dùng"
        verbose_name_plural = "Hồ sơ người dùng"

    def __str__(self):
        return self.user.get_username()