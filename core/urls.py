from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from django.views.generic import RedirectView

from map_app.portal_views import PortalLoginView, register_view

urlpatterns = [
    path("admin/", RedirectView.as_view(pattern_name="portal_home", permanent=False)),
    path("login/", PortalLoginView.as_view(), name="login"),
    path("dang-ky/", register_view, name="register"),
    path("quan-tri/", include("map_app.portal_urls")),
    path("map/", include("map_app.urls")),
    path("", include("django.contrib.auth.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
