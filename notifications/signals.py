from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import UserActivity
from .utils import send_notification, notify_employer_application, notify_application_status_update, notify_job_status_update
from jobs.models import Job, Application

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    # Create login activity log
    UserActivity.objects.create(
        user=user,
        action='login',
        action_details=f'User logged in at {timezone.now()}',
        ip_address=request.META.get('REMOTE_ADDR', ''),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    # Create welcome back notification
    send_notification(
        user=user,
        title='Welcome Back!',
        message=f'You have successfully logged in at {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}',
        notification_type='info',
        template='emails/welcome_back.html'
    )

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    if user:  # Check if user exists (not AnonymousUser)
        UserActivity.objects.create(
            user=user,
            action='logout',
            action_details=f'User logged out at {timezone.now()}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

# Job-related signals
@receiver(post_save, sender=Job)
def handle_job_actions(sender, instance, created, **kwargs):
    if created:
        # Log job creation
        UserActivity.objects.create(
            user=instance.user,
            action='create',
            action_details=f'Created job posting: {instance.title}',
            ip_address='system',  # Since this is a system event
            user_agent='system'
        )
        
        send_notification(
            user=instance.user,
            title='Job Posted Successfully',
            message=f'Your job posting "{instance.title}" has been created and is pending approval.',
            notification_type='success',
            template='emails/job_approval_notification.html',
            job=instance,
            status='pending',
            status_class='warning'
        )

    # When job approval status changes
    if instance.tracker.has_changed('is_approved'):
        notify_job_status_update(instance, instance.is_approved)

@receiver(post_save, sender=Application)
def handle_job_application(sender, instance, created, **kwargs):
    if created:
        # Log application submission
        UserActivity.objects.create(
            user=instance.user,
            action='create',
            action_details=f'Applied for job: {instance.job.title}',
            ip_address='system',
            user_agent='system'
        )
        
        # Notify applicant
        send_notification(
            user=instance.user,
            title='Application Submitted',
            message=f'Your application for "{instance.job.title}" has been submitted successfully.',
            notification_type='success',
            template='emails/application_status_update.html',
            job=instance.job,
            application=instance,
            status='pending'
        )
        
        # Notify employer
        notify_employer_application(instance.job.user, instance)
    
    # When application status changes
    if instance.tracker.has_changed('status'):
        notify_application_status_update(instance)

