from django.apps import AppConfig


class MapAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "map_app"
    verbose_name = "Không gian xanh"

    def ready(self):
        from . import signals  # noqa: F401
