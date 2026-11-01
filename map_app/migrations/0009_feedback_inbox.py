from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def grant_feedback_access(apps, schema_editor):
    Role = apps.get_model("map_app", "Role")
    Role.objects.filter(name__in=["Quản trị viên", "Nhân viên CSVC"]).update(can_manage_feedback=True)


def revoke_feedback_access(apps, schema_editor):
    Role = apps.get_model("map_app", "Role")
    Role.objects.filter(name__in=["Quản trị viên", "Nhân viên CSVC"]).update(can_manage_feedback=False)


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("map_app", "0008_homepagefeaturegroup_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="role",
            name="can_manage_feedback",
            field=models.BooleanField(default=False, verbose_name="Quản lý góp ý / báo lỗi"),
        ),
        migrations.CreateModel(
            name="FeedbackThread",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("username_snapshot", models.CharField(max_length=150, verbose_name="Tên người gửi")),
                ("category", models.CharField(choices=[("feedback", "Góp ý"), ("bug", "Báo lỗi")], default="feedback", max_length=12, verbose_name="Loại")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Tạo lúc")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Cập nhật lúc")),
                ("staff_read_at", models.DateTimeField(blank=True, db_index=True, null=True, verbose_name="Nhân viên đã đọc lúc")),
                ("user_read_at", models.DateTimeField(blank=True, null=True, verbose_name="Người gửi đã đọc lúc")),
                ("user", models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="feedback_threads", to=settings.AUTH_USER_MODEL, verbose_name="Người gửi")),
            ],
            options={
                "verbose_name": "Hộp thư góp ý / báo lỗi",
                "verbose_name_plural": "Hộp thư góp ý / báo lỗi",
                "ordering": ("-updated_at", "-pk"),
            },
        ),
        migrations.CreateModel(
            name="FeedbackMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sender_name", models.CharField(max_length=150, verbose_name="Tên hiển thị")),
                ("is_staff_reply", models.BooleanField(default=False, verbose_name="Phản hồi của nhân viên")),
                ("body", models.TextField(blank=True, max_length=3000, verbose_name="Nội dung")),
                ("image", models.ImageField(blank=True, upload_to="feedback/%Y/%m/", verbose_name="Ảnh đính kèm")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Gửi lúc")),
                ("sender", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="feedback_messages", to=settings.AUTH_USER_MODEL, verbose_name="Người gửi tin nhắn")),
                ("thread", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="map_app.feedbackthread", verbose_name="Hội thoại")),
            ],
            options={
                "verbose_name": "Tin nhắn góp ý / báo lỗi",
                "verbose_name_plural": "Tin nhắn góp ý / báo lỗi",
                "ordering": ("created_at", "pk"),
            },
        ),
        migrations.RunPython(grant_feedback_access, revoke_feedback_access),
    ]
