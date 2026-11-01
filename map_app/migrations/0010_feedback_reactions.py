from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("map_app", "0009_feedback_inbox"),
    ]

    operations = [
        migrations.CreateModel(
            name="FeedbackReaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("emoji", models.CharField(choices=[("👍", "Thích"), ("❤️", "Yêu thích"), ("😂", "Vui"), ("😮", "Ngạc nhiên"), ("😢", "Buồn"), ("🙏", "Cảm ơn")], max_length=8, verbose_name="Emoji")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Thả lúc")),
                ("message", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reactions", to="map_app.feedbackmessage", verbose_name="Tin nhắn")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="feedback_reactions", to=settings.AUTH_USER_MODEL, verbose_name="Người thả cảm xúc")),
            ],
            options={
                "verbose_name": "Cảm xúc tin nhắn góp ý",
                "verbose_name_plural": "Cảm xúc tin nhắn góp ý",
                "ordering": ("created_at", "pk"),
                "constraints": [models.UniqueConstraint(fields=("message", "user", "emoji"), name="unique_feedback_message_reaction")],
            },
        ),
    ]
