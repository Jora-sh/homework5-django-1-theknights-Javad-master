import uuid
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse
from .tasks import send_email_async

def generate_token():
    """Generate a unique token for email verification."""
    return uuid.uuid4().hex


def send_verification_email(user, request=None):
    """Send email verification to user."""
    # Generate token if not already present
    if not user.email_verification_token:
        user.email_verification_token = generate_token()
        user.save()
    
    # Generate verification URL
    verification_url = f"{settings.SITE_URL}{reverse('accounts:verify_email', args=[user.email_verification_token])}"
    
    # Render email template
    html_message = render_to_string('emails/welcome_email.html', {
        'user': user,
        'verification_url': verification_url,
    })
    
    # Send email
    subject = 'Welcome to Job Portal - Verify Your Email'
    message = f'Hi {user.first_name},\n\nWelcome to Job Portal! Please verify your email by clicking on the following link: {verification_url}'
    
    return send_email_async(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )


def send_verification_success_email(user):
    """Send verification success email to user."""
    html_message = render_to_string('emails/verification_success.html', {
        'user': user,
        'site_url': settings.SITE_URL,
    })
    
    subject = 'Email Verified - Welcome to Job Portal!'
    message = f'Hi {user.first_name},\n\nYour email has been successfully verified. Welcome to Job Portal!'
    
    return send_email_async(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )


def send_application_notification_email(application):
    """Send email to employer when a job seeker applies to their job."""
    html_message = render_to_string('emails/application_notification.html', {
        'application': application,
        'job': application.job,
        'employer': application.job.user,
        'applicant': application.user,
        'site_url': settings.SITE_URL,
    })
    
    subject = f'New application for your job: {application.job.title}'
    message = f'Hi {application.job.user.first_name},\n\nYou have received a new application for the job: {application.job.title} from {application.user.first_name} {application.user.last_name}.'
    
    # Create email message
    email = EmailMessage(
        subject=subject,
        body=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[application.job.user.email],
    )
    email.content_subtype = "html"
    
    # Attach resume if available
    if application.resume:
        email.attach_file(application.resume.path)
    
    return email.send(fail_silently=False) 