from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site
from django.utils.html import strip_tags
from notifications.models import Notification
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

def notify_admin_pending_jobs(admin_user, pending_jobs, request=None):
    """Send notification to admin about pending job approvals."""
    if not pending_jobs.exists():
        return
    
    send_notification(
        user=admin_user,
        title='Jobs Pending Approval',
        message=f'There are {pending_jobs.count()} jobs pending your approval.',
        notification_type='info',
        template='emails/pending_jobs_notification.html',
        pending_jobs=pending_jobs[:5],  # Limit to 5 most recent
        pending_count=pending_jobs.count(),
        request=request
    )

def notify_employer_application(employer, application, request=None):
    """Send notification to employer about new job application."""
    send_notification(
        user=employer,
        title='New Job Application Received',
        message=f'New application received for "{application.job.title}" from {application.user.get_full_name()}',
        notification_type='job_application',
        template='emails/new_application_notification.html',
        job=application.job,
        application=application,
        applicant=application.user,
        request=request
    )

def notify_application_status_update(application, request=None):
    """Send notification to job seeker about application status update."""
    send_notification(
        user=application.user,
        title='Application Status Updated',
        message=f'Your application for "{application.job.title}" has been updated.',
        notification_type='application_status',
        template='emails/application_status_update.html',
        job=application.job,
        application=application,
        status=application.status,
        request=request
    )

def notify_job_status_update(job, is_approved, feedback=None, request=None):
    """Send notification to employer about job approval/rejection."""
    status = 'approved' if is_approved else 'rejected'
    notification_type = 'job_approved' if is_approved else 'job_rejected'
    title = 'Job Posting Approved' if is_approved else 'Job Posting Rejected'
    message = f'Your job posting "{job.title}" has been {status}.'
    
    send_notification(
        user=job.user,
        title=title,
        message=message,
        notification_type=notification_type,
        template='emails/job_approval_notification.html',
        job=job,
        status=status,
        feedback=feedback,
        request=request
    )

def clean_old_notifications(days=30):
    """Clean up old read notifications."""
    cutoff_date = timezone.now() - timedelta(days=days)
    Notification.objects.filter(
        Q(created_at__lt=cutoff_date),
        Q(is_read=True)
    ).delete()

def get_site_url(request=None):
    """Get the full site URL."""
    if request:
        return f"{request.scheme}://{request.get_host()}"
    return settings.SITE_URL

def send_notification(user, title, message, notification_type='info', **kwargs):
    """
    Send both email and in-app notification to a user.
    
    Args:
        user: The user to notify
        title: Notification title
        message: Notification message
        notification_type: Type of notification (from Notification.NOTIFICATION_TYPES)
        **kwargs: Additional context for the email template
            - template: Email template to use
            - job: Job instance related to the notification
            - application: Application instance related to the notification
            - status: Status string for job/application updates
            - feedback: Feedback message for job rejections
            - request: Request object for generating absolute URLs
    """
    template = kwargs.get('template', 'emails/notifications/generic.html')
    # Create in-app notification
    Notification.objects.create(
        recipient=user,
        title=title,
        message=message,
        notification_type=notification_type
    )
    
    # Create in-app notification
    notification = Notification.objects.create(
        recipient=user,
        title=title,
        message=message,
        notification_type=notification_type
    )

    # Base context for all email templates
    context = {
        'user': user,
        'title': title,
        'message': message,
        'site_url': get_site_url(kwargs.get('request')),
        'site_name': 'Job Portal',
    }

    # Add all additional kwargs to context
    context.update({k: v for k, v in kwargs.items() if k != 'template' and k != 'request'})

    # Status-specific context
    if notification_type in ['job_approved', 'job_rejected']:
        context['status'] = 'approved' if notification_type == 'job_approved' else 'rejected'
        context['status_display'] = 'Approved' if notification_type == 'job_approved' else 'Rejected'
        context['status_class'] = 'success' if notification_type == 'job_approved' else 'danger'
    
    elif notification_type == 'job_application':
        status = kwargs.get('status', 'pending')
        status_display_map = {
            'pending': 'Pending Review',
            'reviewing': 'Under Review',
            'shortlisted': 'Shortlisted',
            'accepted': 'Accepted',
            'rejected': 'Rejected'
        }
        status_class_map = {
            'pending': 'warning',
            'reviewing': 'info',
            'shortlisted': 'info',
            'accepted': 'success',
            'rejected': 'danger'
        }
        context.update({
            'status': status,
            'status_display': status_display_map.get(status, status.title()),
            'status_class': status_class_map.get(status, 'info')
        })

    # Render email templates
    html_message = render_to_string(template, context)
    plain_message = strip_tags(html_message)
    
    # Send email
    send_mail(
        subject=title,
        message=plain_message,
        html_message=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )

def notify_job_application(application):
    """Send notification for new job application"""
    # Notify employer
    send_notification(
        user=application.job.user,
        title=f"New application for {application.job.title}",
        message=f"{application.user.get_full_name()} has applied for your job posting.",
        notification_type='job_application',
        job=application.job,
        action_url=f"{settings.SITE_URL}{reverse('dashboard:application_detail', args=[application.id])}"
    )
    
    # Notify applicant
    send_notification(
        user=application.user,
        title=f"Application submitted for {application.job.title}",
        message="Your application has been successfully submitted and is under review.",
        notification_type='job_application',
        job=application.job,
        action_url=f"{settings.SITE_URL}{reverse('jobs:job_detail', args=[application.job.id])}"
    )

def notify_job_status_update(application, status):
    """Send notification for job application status update"""
    status_messages = {
        'approved': 'Your job application has been approved!',
        'rejected': 'Unfortunately, your job application was not selected.',
        'under_review': 'Your application is currently under review.',
        'shortlisted': 'Congratulations! Your application has been shortlisted.',
    }
    
    notification_types = {
        'approved': 'success',
        'rejected': 'error',
        'under_review': 'info',
        'shortlisted': 'success',
    }
    
    if status in status_messages:
        send_notification(
            user=application.user,
            title=f"Application Status Update - {application.job.title}",
            message=status_messages[status],
            notification_type=notification_types[status],
            job=application.job,
            action_url=f"{settings.SITE_URL}{reverse('jobs:job_detail', args=[application.job.id])}"
        )

def notify_job_approval_status(job, is_approved):
    """Send notification for job posting approval status"""
    if is_approved:
        send_notification(
            user=job.user,
            title="Job Posting Approved",
            message=f"Your job posting for {job.title} has been approved and is now live.",
            notification_type='job_approved',
            job=job,
            action_url=f"{settings.SITE_URL}{reverse('jobs:job_detail', args=[job.id])}"
        )
    else:
        send_notification(
            user=job.user,
            title="Job Posting Not Approved",
            message=f"Your job posting for {job.title} was not approved. Please review and update the posting.",
            notification_type='job_rejected',
            job=job,
            action_url=f"{settings.SITE_URL}{reverse('dashboard:edit_job', args=[job.id])}"
        )
