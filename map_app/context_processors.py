from .permissions import can_access_portal, get_role, nav_permissions


def portal(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {
            "can_access_portal": False,
            "user_role_name": "",
        }
    role = get_role(user)
    return {
        "can_access_portal": can_access_portal(user),
        "user_role_name": role.name if role else ("Superuser" if user.is_superuser else "Chưa gán vai trò"),
        "nav_perms": nav_permissions(user) if can_access_portal(user) else {},
    }
