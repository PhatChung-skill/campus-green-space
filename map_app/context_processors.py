from .permissions import can_access_portal, get_role, is_admin_user, nav_permissions
from .models import HomepageBlock


def portal(request):
    user = getattr(request, "user", None)
    site_brand = HomepageBlock.objects.filter(kind=HomepageBlock.Kind.HEADER, is_active=True).first()
    if not user or not user.is_authenticated:
        return {
            "can_access_portal": False,
            "is_admin_role": False,
            "user_role_name": "",
            "site_brand": site_brand,
        }
    role = get_role(user)
    return {
        "can_access_portal": can_access_portal(user),
        "is_admin_role": is_admin_user(user),
        "user_role_name": role.name if role else ("Superuser" if user.is_superuser else "Chưa gán vai trò"),
        "nav_perms": nav_permissions(user) if can_access_portal(user) else {},
        "site_brand": site_brand,
    }
