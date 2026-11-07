from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from django.views.generic import RedirectView

from map_app.portal_views import (
    PortalLoginView,
    password_reset_request_view,
    password_reset_resend_otp_view,
    password_reset_verify_view,
    register_view,
    resend_registration_otp_view,
    verify_registration_email_view,
)
from map_app.views import homepage_view

urlpatterns = [
    path("admin/", RedirectView.as_view(pattern_name="homepage_content", permanent=False), name="custom_admin"),
    path("login/", PortalLoginView.as_view(), name="login"),
    path("quen-mat-khau/", password_reset_request_view, name="password_reset_request"),
    path("quen-mat-khau/xac-thuc/", password_reset_verify_view, name="password_reset_verify"),
    path("quen-mat-khau/gui-lai-ma/", password_reset_resend_otp_view, name="password_reset_resend_otp"),
    path("dang-ky/", register_view, name="register"),
    path("dang-ky/xac-thuc-email/", verify_registration_email_view, name="verify_registration_email"),
    path("dang-ky/gui-lai-ma/", resend_registration_otp_view, name="resend_registration_otp"),
    path("quan-tri/", include("map_app.portal_urls")),
    path("map/", include("map_app.urls")),
    path("", homepage_view, name="home"),
    path("", include("django.contrib.auth.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
