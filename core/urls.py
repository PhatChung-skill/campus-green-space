from django.urls import include, path
from django.views.generic import RedirectView

from map_app.portal_views import PortalLoginView

urlpatterns = [
    path("admin/", RedirectView.as_view(pattern_name="portal_home", permanent=False)),
    path("login/", PortalLoginView.as_view(), name="login"),
    path("quan-tri/", include("map_app.portal_urls")),
    path("map/", include("map_app.urls")),
    path("", include("django.contrib.auth.urls")),
]
