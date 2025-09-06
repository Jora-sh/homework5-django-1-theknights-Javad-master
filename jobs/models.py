from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.urls import reverse
from model_utils import FieldTracker
import os

User = get_user_model()


class JobManager(models.Manager):
    """Custom manager for Job model to query active jobs."""
    
    def active(self):
        """Return only active job listings."""
        return self.filter(is_active=True)

    def approved(self):
        """Return only approved and active job listings."""
        return self.filter(is_active=True, is_approved=True)


def resume_upload_path(instance, filename):
    """Generate upload path for resumes."""
    # Get the file extension
    ext = filename.split('.')[-1]
    # Create a unique filename using the job ID, user ID, and timestamp
    filename = f"resume_job_{instance.job.id}_user_{instance.user.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}.{ext}"
    # Return the full path
    return os.path.join('resumes', filename)


class Job(models.Model):
    """Model for job listings."""
    SALARY_CHOICES = (
        ('negotiable', _('Negotiable')),
        ('10000-30000', '$10,000 - $30,000'),
        ('30000-50000', '$30,000 - $50,000'),
        ('50000-70000', '$50,000 - $70,000'),
        ('70000-90000', '$70,000 - $90,000'),
        ('90000-110000', '$90,000 - $110,000'),
        ('110000-130000', '$110,000 - $130,000'),
        ('130000+', '$130,000+'),
    )
    
    JOB_TYPE_CHOICES = (
        ('full_time', _('Full Time')),
        ('part_time', _('Part Time')),
        ('contract', _('Contract')),
        ('internship', _('Internship')),
        ('freelance', _('Freelance')),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posted_jobs')
    title = models.CharField(max_length=100)
    company = models.CharField(max_length=100)
    description = models.TextField()
    requirements = models.TextField()
    location = models.CharField(max_length=100)
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES, default='full_time')
    salary = models.CharField(max_length=20, choices=SALARY_CHOICES, default='negotiable')
    is_active = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=False, help_text=_('Job must be approved by admin before it is visible to job seekers'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Use custom manager
    objects = JobManager()
    
    # Field tracker for monitoring changes
    tracker = FieldTracker()
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('jobs:job_detail', args=[self.id])


class Application(models.Model):
    """Model for job applications."""
    STATUS_CHOICES = (
        ('pending', _('Pending')),
        ('reviewing', _('Reviewing')),
        ('shortlisted', _('Shortlisted')),
        ('rejected', _('Rejected')),
        ('accepted', _('Accepted')),
    )
    
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    resume = models.FileField(upload_to=resume_upload_path)
    cover_letter = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Field tracker for monitoring changes
    tracker = FieldTracker()
    
    # Field tracker for monitoring changes
    tracker = FieldTracker()
    
    class Meta:
        unique_together = ('job', 'user')
        ordering = ['-applied_at']
    
    def __str__(self):
        return f"{self.user.email} applied to {self.job.title}"
    
    def get_absolute_url(self):
        return reverse('dashboard:application_detail', args=[self.id])
