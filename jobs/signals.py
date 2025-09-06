from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Job, Application
from notifications.utils import notify_job_application, notify_job_status_update, notify_job_approval_status

@receiver(post_save, sender=Job)
def job_post_save(sender, instance, created, **kwargs):
    """Handle notifications when a job is saved"""
    if not created and hasattr(instance, 'tracker'):
        # Check if is_approved status changed
        if instance.tracker.has_changed('is_approved'):
            notify_job_approval_status(instance, instance.is_approved)

@receiver(post_save, sender=Application)
def job_application_post_save(sender, instance, created, **kwargs):
    """Handle notifications when a job application is saved"""
    if created:
        # New application
        notify_job_application(instance)
    elif hasattr(instance, 'tracker'):
        # Status update
        if instance.tracker.has_changed('status'):
            notify_job_status_update(instance, instance.status)
