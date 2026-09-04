from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Role, UserProfile


@receiver(post_save, sender=User)
def ensure_user_profile(sender, instance, created, **kwargs):
    if created:
        guest = Role.objects.filter(name="Khách").first()
        UserProfile.objects.get_or_create(user=instance, defaults={"role": guest})
    else:
        UserProfile.objects.get_or_create(user=instance)
