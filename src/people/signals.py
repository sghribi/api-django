from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from people import tasks
from .models import Person
from authentication.models import Role


@receiver(pre_save, sender=Person, dispatch_uid="person_ensure_has_role")
def ensure_has_role(sender, instance, raw, **kwargs):
    if not raw and instance.role_id is None:
        role = Role.objects.create(type=Role.PERSON_ROLE)
        instance.role = role


@receiver(post_save, sender=Person, dispatch_uid="person_update_mailtrain")
def update_mailtrain(sender, instance, raw, **kwargs):
    tasks.update_mailtrain.delay(instance)
