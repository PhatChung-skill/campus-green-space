from django.db import migrations, models


def create_default_homepage(apps, schema_editor):
    HomepageContent = apps.get_model("map_app", "HomepageContent")
    HomepageContent.objects.using(schema_editor.connection.alias).get_or_create(
        pk=1,
        defaults={
            "hero_badge": "HCMUNRE · WEBGIS",
            "hero_title": "Khám phá khuôn viên xanh",
            "hero_subtitle": "Tra cứu không gian, tiện ích và cảnh quan xanh trong khuôn viên trường.",
            "intro_title": "Một khuôn viên, nhiều điều để khám phá",
            "intro_body": "WebGIS giúp bạn tìm hiểu các cơ sở, công trình và mảng xanh của trường trên cùng một bản đồ.",
            "features_title": "Khám phá tiện ích trong khuôn viên",
            "feature_1_title": "Bản đồ trực quan",
            "feature_1_body": "Tìm cơ sở, tòa nhà, tầng và phòng trên bản đồ.",
            "feature_2_title": "Không gian xanh",
            "feature_2_body": "Khám phá các khu vực xanh và thông tin cây trong khuôn viên.",
            "feature_3_title": "Thông tin cập nhật",
            "feature_3_body": "Tra cứu thông tin tiện ích và hạ tầng của trường.",
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("map_app", "0005_greenarea_description_parkingarea_description_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="HomepageContent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("hero_badge", models.CharField(default="HCMUNRE · WEBGIS", max_length=100, verbose_name="Nhãn đầu trang")),
                ("hero_title", models.CharField(default="Khám phá khuôn viên xanh", max_length=220, verbose_name="Tiêu đề chính")),
                ("hero_subtitle", models.TextField(default="Tra cứu không gian, tiện ích và cảnh quan xanh trong khuôn viên trường.", verbose_name="Mô tả chính")),
                ("hero_image", models.ImageField(blank=True, upload_to="homepage/", verbose_name="Ảnh banner")),
                ("intro_title", models.CharField(default="Một khuôn viên, nhiều điều để khám phá", max_length=220, verbose_name="Tiêu đề giới thiệu")),
                ("intro_body", models.TextField(default="WebGIS giúp bạn tìm hiểu các cơ sở, công trình và mảng xanh của trường trên cùng một bản đồ.", verbose_name="Nội dung giới thiệu")),
                ("intro_image", models.ImageField(blank=True, upload_to="homepage/", verbose_name="Ảnh giới thiệu")),
                ("features_title", models.CharField(default="Khám phá tiện ích trong khuôn viên", max_length=220, verbose_name="Tiêu đề khu vực tiện ích")),
                ("feature_1_title", models.CharField(default="Bản đồ trực quan", max_length=120, verbose_name="Thẻ 1 · Tiêu đề")),
                ("feature_1_body", models.TextField(default="Tìm cơ sở, tòa nhà, tầng và phòng trên bản đồ.", verbose_name="Thẻ 1 · Mô tả")),
                ("feature_1_image", models.ImageField(blank=True, upload_to="homepage/", verbose_name="Thẻ 1 · Ảnh")),
                ("feature_2_title", models.CharField(default="Không gian xanh", max_length=120, verbose_name="Thẻ 2 · Tiêu đề")),
                ("feature_2_body", models.TextField(default="Khám phá các khu vực xanh và thông tin cây trong khuôn viên.", verbose_name="Thẻ 2 · Mô tả")),
                ("feature_2_image", models.ImageField(blank=True, upload_to="homepage/", verbose_name="Thẻ 2 · Ảnh")),
                ("feature_3_title", models.CharField(default="Thông tin cập nhật", max_length=120, verbose_name="Thẻ 3 · Tiêu đề")),
                ("feature_3_body", models.TextField(default="Tra cứu thông tin tiện ích và hạ tầng của trường.", verbose_name="Thẻ 3 · Mô tả")),
                ("feature_3_image", models.ImageField(blank=True, upload_to="homepage/", verbose_name="Thẻ 3 · Ảnh")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Cập nhật lúc")),
            ],
            options={
                "verbose_name": "Nội dung trang chủ",
                "verbose_name_plural": "Nội dung trang chủ",
            },
        ),
        migrations.RunPython(create_default_homepage, migrations.RunPython.noop),
    ]
