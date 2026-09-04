from django.contrib.gis.db import models
from django.contrib.auth.models import User

# ==========================================
# NHÓM 1: KHÔNG GIAN HẠ TẦNG (INFRASTRUCTURE)
# ==========================================

class Campus(models.Model):
    campus_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, verbose_name="Tên cơ sở")
    geom = models.PolygonField(srid=4326, verbose_name="Ranh giới khuôn viên")
    image_1 = models.TextField(blank=True, null=True)
    image_2 = models.TextField(blank=True, null=True)
    image_3 = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Building(models.Model):
    building_id = models.AutoField(primary_key=True)
    campus = models.ForeignKey(Campus, on_delete=models.CASCADE, related_name='buildings')
    name = models.CharField(max_length=255, verbose_name="Tên tòa nhà")
    geom = models.PolygonField(srid=4326, verbose_name="Hình dạng tòa nhà")
    image_1 = models.TextField(blank=True, null=True)
    image_2 = models.TextField(blank=True, null=True)
    image_3 = models.TextField(blank=True, null=True)

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
    image_1 = models.TextField(blank=True, null=True)
    image_2 = models.TextField(blank=True, null=True)
    image_3 = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class ParkingArea(models.Model):
    parking_id = models.AutoField(primary_key=True)
    campus = models.ForeignKey(Campus, on_delete=models.CASCADE, related_name='parkings')
    name = models.CharField(max_length=255, verbose_name="Tên bãi xe")
    capacity = models.IntegerField(verbose_name="Sức chứa dự kiến", blank=True, null=True)
    geom = models.PolygonField(srid=4326, verbose_name="Ranh giới bãi xe")
    image_1 = models.TextField(blank=True, null=True)
    image_2 = models.TextField(blank=True, null=True)
    image_3 = models.TextField(blank=True, null=True)

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
    image_1 = models.TextField(blank=True, null=True)
    image_2 = models.TextField(blank=True, null=True)
    image_3 = models.TextField(blank=True, null=True)

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
    image_1 = models.TextField(blank=True, null=True)
    image_2 = models.TextField(blank=True, null=True)
    image_3 = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Cây {self.species} - ID: {self.tree_id}"