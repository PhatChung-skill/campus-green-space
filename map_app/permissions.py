from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

ADMIN_ROLE_NAME = "Quản trị viên"


def get_role(user):
    if not user.is_authenticated:
        return None
    profile = getattr(user, "profile", None)
    return getattr(profile, "role", None) if profile else None


def user_has_perm(user, action, resource):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    role = get_role(user)
    if not role:
        return False
    return role.has_perm(action, resource)


def can_access_portal(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    role = get_role(user)
    return bool(role and role.can_access_portal)


def is_admin_user(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    role = get_role(user)
    return bool(role and role.name == ADMIN_ROLE_NAME)


def portal_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login')}?next={request.path}")
        if not can_access_portal(request.user):
            messages.error(request, "Bạn không có quyền truy cập trang quản lý.")
            return redirect("dashboard")
        return view_func(request, *args, **kwargs)

    return _wrapped


def perm_required(action, resource):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f"{reverse('login')}?next={request.path}")
            if not can_access_portal(request.user):
                messages.error(request, "Bạn không có quyền truy cập trang quản lý.")
                return redirect("dashboard")
            if not user_has_perm(request.user, action, resource):
                messages.error(request, "Bạn không đủ quyền thực hiện thao tác này.")
                return redirect("portal_home")
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


def nav_permissions(user):
    resources = [
        "users",
        "roles",
        "campus",
        "building",
        "floor",
        "room",
        "parking",
        "greenarea",
        "tree",
    ]
    return {res: user_has_perm(user, "view", res) for res in resources}
