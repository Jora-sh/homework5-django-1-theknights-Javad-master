from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from core.utils import send_verification_email

User = get_user_model()

@receiver(post_save, sender=User)
def send_email_verification(sender, instance, created, **kwargs):
    """Send email verification to new users."""
    if created and not instance.email_verified and not instance.is_superuser:
        # Only send verification if user is newly created, not verified, and not a superuser
        send_verification_email(instance) 