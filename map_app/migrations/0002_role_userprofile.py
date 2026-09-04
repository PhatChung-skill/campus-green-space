from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


ADMIN_PERMS = {
    "can_access_portal": True,
    "can_view_users": True,
    "can_add_users": True,
    "can_change_users": True,
    "can_delete_users": True,
    "can_view_roles": True,
    "can_add_roles": True,
    "can_change_roles": True,
    "can_delete_roles": True,
    "can_view_campus": True,
    "can_add_campus": True,
    "can_change_campus": True,
    "can_delete_campus": True,
    "can_view_building": True,
    "can_add_building": True,
    "can_change_building": True,
    "can_delete_building": True,
    "can_view_floor": True,
    "can_add_floor": True,
    "can_change_floor": True,
    "can_delete_floor": True,
    "can_view_room": True,
    "can_add_room": True,
    "can_change_room": True,
    "can_delete_room": True,
    "can_view_parking": True,
    "can_add_parking": True,
    "can_change_parking": True,
    "can_delete_parking": True,
    "can_view_greenarea": True,
    "can_add_greenarea": True,
    "can_change_greenarea": True,
    "can_delete_greenarea": True,
    "can_view_tree": True,
    "can_add_tree": True,
    "can_change_tree": True,
    "can_delete_tree": True,
}

STAFF_PERMS = {
    "can_access_portal": True,
    "can_view_users": False,
    "can_add_users": False,
    "can_change_users": False,
    "can_delete_users": False,
    "can_view_roles": False,
    "can_add_roles": False,
    "can_change_roles": False,
    "can_delete_roles": False,
    "can_view_campus": True,
    "can_add_campus": True,
    "can_change_campus": True,
    "can_delete_campus": True,
    "can_view_building": True,
    "can_add_building": True,
    "can_change_building": True,
    "can_delete_building": True,
    "can_view_floor": True,
    "can_add_floor": True,
    "can_change_floor": True,
    "can_delete_floor": True,
    "can_view_room": True,
    "can_add_room": True,
    "can_change_room": True,
    "can_delete_room": True,
    "can_view_parking": True,
    "can_add_parking": True,
    "can_change_parking": True,
    "can_delete_parking": True,
    "can_view_greenarea": True,
    "can_add_greenarea": True,
    "can_change_greenarea": True,
    "can_delete_greenarea": True,
    "can_view_tree": True,
    "can_add_tree": True,
    "can_change_tree": True,
    "can_delete_tree": True,
}


def seed_roles(apps, schema_editor):
    Role = apps.get_model("map_app", "Role")
    User = apps.get_model("auth", "User")
    UserProfile = apps.get_model("map_app", "UserProfile")

    admin_role, _ = Role.objects.get_or_create(
        name="Quản trị viên",
        defaults={
            "description": "Toàn quyền quản lý hệ thống, người dùng và dữ liệu.",
            "is_system": True,
            **ADMIN_PERMS,
        },
    )
    staff_role, _ = Role.objects.get_or_create(
        name="Nhân viên CSVC",
        defaults={
            "description": "Quản lý hạ tầng và không gian xanh, không quản lý tài khoản.",
            "is_system": True,
            **STAFF_PERMS,
        },
    )
    guest_role, _ = Role.objects.get_or_create(
        name="Khách",
        defaults={
            "description": "Chỉ tra cứu bản đồ, không vào trang quản lý.",
            "is_system": True,
        },
    )

    for user in User.objects.all():
        if user.is_superuser:
            role = admin_role
        elif user.is_staff:
            role = staff_role
        else:
            role = guest_role
        UserProfile.objects.get_or_create(user=user, defaults={"role": role})


def unseed_roles(apps, schema_editor):
    Role = apps.get_model("map_app", "Role")
    UserProfile = apps.get_model("map_app", "UserProfile")
    UserProfile.objects.all().delete()
    Role.objects.filter(name__in=["Quản trị viên", "Nhân viên CSVC", "Khách"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("map_app", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Role",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True, verbose_name="Tên vai trò")),
                ("description", models.TextField(blank=True, verbose_name="Mô tả")),
                ("is_system", models.BooleanField(default=False, verbose_name="Vai trò hệ thống")),
                ("can_access_portal", models.BooleanField(default=False, verbose_name="Truy cập trang quản lý")),
                ("can_view_users", models.BooleanField(default=False, verbose_name="Xem người dùng")),
                ("can_add_users", models.BooleanField(default=False, verbose_name="Thêm người dùng")),
                ("can_change_users", models.BooleanField(default=False, verbose_name="Sửa người dùng")),
                ("can_delete_users", models.BooleanField(default=False, verbose_name="Xóa người dùng")),
                ("can_view_roles", models.BooleanField(default=False, verbose_name="Xem vai trò")),
                ("can_add_roles", models.BooleanField(default=False, verbose_name="Thêm vai trò")),
                ("can_change_roles", models.BooleanField(default=False, verbose_name="Sửa vai trò")),
                ("can_delete_roles", models.BooleanField(default=False, verbose_name="Xóa vai trò")),
                ("can_view_campus", models.BooleanField(default=False, verbose_name="Xem cơ sở")),
                ("can_add_campus", models.BooleanField(default=False, verbose_name="Thêm cơ sở")),
                ("can_change_campus", models.BooleanField(default=False, verbose_name="Sửa cơ sở")),
                ("can_delete_campus", models.BooleanField(default=False, verbose_name="Xóa cơ sở")),
                ("can_view_building", models.BooleanField(default=False, verbose_name="Xem tòa nhà")),
                ("can_add_building", models.BooleanField(default=False, verbose_name="Thêm tòa nhà")),
                ("can_change_building", models.BooleanField(default=False, verbose_name="Sửa tòa nhà")),
                ("can_delete_building", models.BooleanField(default=False, verbose_name="Xóa tòa nhà")),
                ("can_view_floor", models.BooleanField(default=False, verbose_name="Xem tầng")),
                ("can_add_floor", models.BooleanField(default=False, verbose_name="Thêm tầng")),
                ("can_change_floor", models.BooleanField(default=False, verbose_name="Sửa tầng")),
                ("can_delete_floor", models.BooleanField(default=False, verbose_name="Xóa tầng")),
                ("can_view_room", models.BooleanField(default=False, verbose_name="Xem phòng")),
                ("can_add_room", models.BooleanField(default=False, verbose_name="Thêm phòng")),
                ("can_change_room", models.BooleanField(default=False, verbose_name="Sửa phòng")),
                ("can_delete_room", models.BooleanField(default=False, verbose_name="Xóa phòng")),
                ("can_view_parking", models.BooleanField(default=False, verbose_name="Xem bãi xe")),
                ("can_add_parking", models.BooleanField(default=False, verbose_name="Thêm bãi xe")),
                ("can_change_parking", models.BooleanField(default=False, verbose_name="Sửa bãi xe")),
                ("can_delete_parking", models.BooleanField(default=False, verbose_name="Xóa bãi xe")),
                ("can_view_greenarea", models.BooleanField(default=False, verbose_name="Xem mảng xanh")),
                ("can_add_greenarea", models.BooleanField(default=False, verbose_name="Thêm mảng xanh")),
                ("can_change_greenarea", models.BooleanField(default=False, verbose_name="Sửa mảng xanh")),
                ("can_delete_greenarea", models.BooleanField(default=False, verbose_name="Xóa mảng xanh")),
                ("can_view_tree", models.BooleanField(default=False, verbose_name="Xem cây xanh")),
                ("can_add_tree", models.BooleanField(default=False, verbose_name="Thêm cây xanh")),
                ("can_change_tree", models.BooleanField(default=False, verbose_name="Sửa cây xanh")),
                ("can_delete_tree", models.BooleanField(default=False, verbose_name="Xóa cây xanh")),
            ],
            options={
                "verbose_name": "Vai trò",
                "verbose_name_plural": "Vai trò",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("phone", models.CharField(blank=True, max_length=20, verbose_name="Số điện thoại")),
                ("notes", models.TextField(blank=True, verbose_name="Ghi chú")),
                (
                    "role",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="users",
                        to="map_app.role",
                        verbose_name="Vai trò",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Tài khoản",
                    ),
                ),
            ],
            options={
                "verbose_name": "Hồ sơ người dùng",
                "verbose_name_plural": "Hồ sơ người dùng",
            },
        ),
        migrations.RunPython(seed_roles, unseed_roles),
    ]
