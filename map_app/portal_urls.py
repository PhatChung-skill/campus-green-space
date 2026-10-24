from django.urls import path

from . import portal_views

urlpatterns = [
    path("", portal_views.portal_home, name="portal_home"),
    path("noi-dung-trang-chu/", portal_views.homepage_content_view, name="homepage_content"),
    path("noi-dung-trang-chu/them/<slug:kind>/", portal_views.homepage_block_create_view, name="homepage_block_create"),
    path("noi-dung-trang-chu/<int:pk>/sua/", portal_views.homepage_block_edit_view, name="homepage_block_edit"),
    path("noi-dung-trang-chu/<int:pk>/xoa/", portal_views.homepage_block_delete_view, name="homepage_block_delete"),
    path(
        "api/hinh-hoc/<slug:entity>/<int:pk>/",
        portal_views.parent_geom,
        name="portal_parent_geom",
    ),
    path(
        "api/context/<slug:entity>/",
        portal_views.entity_context_geojson,
        name="portal_entity_context",
    ),
    path("api/buildings/", portal_views.filter_buildings, name="portal_filter_buildings"),
    path("api/floors/",    portal_views.filter_floors,    name="portal_filter_floors"),
    path("nguoi-dung/", portal_views.user_list, name="portal_users"),
    path("nguoi-dung/them/", portal_views.user_create, name="portal_user_create"),
    path("nguoi-dung/<int:pk>/sua/", portal_views.user_update, name="portal_user_edit"),
    path("nguoi-dung/<int:pk>/xoa/", portal_views.user_delete, name="portal_user_delete"),
    path("vai-tro/", portal_views.role_list, name="portal_roles"),
    path("vai-tro/them/", portal_views.role_create, name="portal_role_create"),
    path("vai-tro/<int:pk>/sua/", portal_views.role_update, name="portal_role_edit"),
    path("vai-tro/<int:pk>/xoa/", portal_views.role_delete, name="portal_role_delete"),
    path("<slug:entity>/", portal_views.entity_list, name="portal_entity_list"),
    path("<slug:entity>/them/", portal_views.entity_create, name="portal_entity_create"),
    path("<slug:entity>/<int:pk>/sua/", portal_views.entity_update, name="portal_entity_edit"),
    path("<slug:entity>/<int:pk>/xoa/", portal_views.entity_delete, name="portal_entity_delete"),
]
