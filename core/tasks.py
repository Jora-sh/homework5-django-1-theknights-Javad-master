from celery import shared_task
from django.core.mail import send_mail
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
from django.conf import settings
from accounts.models import User
from jobs.models import Job
from datetime import datetime, timedelta

@shared_task
def send_email_async(subject, message, from_email, recipient_list, html_message=None, fail_silently=False):
    """Send email asynchronously using Celery."""
    send_mail(
        subject,
        message,
        from_email,
        recipient_list,
        html_message=html_message,
        fail_silently=fail_silently,
    )

@shared_task
def generate_thumbnail_async(user_id, profile_image_path):
    """Generate thumbnail asynchronously using Celery."""
    try:
        user = User.objects.get(id=user_id)
        with Image.open(profile_image_path) as img:
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Calculate aspect ratio to maintain proportions
            output_size = (150, 150)
            
            # Create a thumbnail maintaining aspect ratio
            img.thumbnail(output_size, Image.LANCZOS)
            
            # If the image is not square, crop it to make it square
            if img.size[0] != img.size[1]:
                min_size = min(img.size)
                left = (img.size[0] - min_size) // 2
                top = (img.size[1] - min_size) // 2
                right = left + min_size
                bottom = top + min_size
                img = img.crop((left, top, right, bottom))
            
            # Save the thumbnail
            thumb_io = BytesIO()
            img.save(thumb_io, format='JPEG', quality=85)
            thumb_io.seek(0)
            
            # Create the thumbnail file
            thumbnail = InMemoryUploadedFile(
                thumb_io,
                'ImageField',
                f"{user.id}_thumb.jpg",
                'image/jpeg',
                sys.getsizeof(thumb_io),
                None
            )
            
            # Save the thumbnail
            user.profile_thumbnail = thumbnail
            user.save()
            
    except User.DoesNotExist:
        pass
    except Exception as e:
        print(f"Error generating thumbnail: {str(e)}")

@shared_task
def cleanup_expired_jobs():
    """Clean up expired job listings."""
    expiry_date = datetime.now() - timedelta(days=30)  # Jobs older than 30 days
    Job.objects.filter(created_at__lt=expiry_date, status='expired').delete()

@shared_task
def update_job_status():
    """Update job listing status based on expiry date."""
    Job.objects.filter(
        expiry_date__lt=datetime.now(),
        status='active'
    ).update(status='expired')