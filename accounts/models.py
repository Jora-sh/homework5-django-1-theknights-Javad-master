from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
import os


def user_resume_upload_path(instance, filename):
    """Generate upload path for user resumes."""
    # Get the file extension
    ext = filename.split('.')[-1]
    # Create a unique filename
    filename = f"resume_user_{instance.id}_{instance.email.split('@')[0]}.{ext}"
    # Return the full path
    return os.path.join('user_resumes', filename)


def user_profile_image_path(instance, filename):
    """Generate upload path for user profile images."""
    # Get the file extension
    ext = filename.split('.')[-1]
    # Create a unique filename
    filename = f"profile_{instance.id}_{instance.email.split('@')[0]}.{ext}"
    # Return the full path
    return os.path.join('profile_images', filename)


def user_profile_thumbnail_path(instance, filename):
    """Generate upload path for user profile thumbnails."""
    # Get the file extension
    ext = filename.split('.')[-1]
    # Create a unique filename
    filename = f"thumbnail_{instance.id}_{instance.email.split('@')[0]}.{ext}"
    # Return the full path
    return os.path.join('profile_thumbnails', filename)


class CustomUserManager(BaseUserManager):
    """Custom user manager where email is the unique identifier."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('The Email must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    # Make email the unique identifier and required
    username = models.CharField(max_length=150, blank=True)
    email = models.EmailField(_('email address'), unique=True)
    
    # Role fields
    is_employer = models.BooleanField(default=False)
    is_seeker = models.BooleanField(default=False)
    
    # Email verification
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=100, blank=True, null=True)
    
    # Profile fields for job seekers
    resume = models.FileField(upload_to=user_resume_upload_path, blank=True, null=True)
    skills = models.TextField(blank=True, null=True)
    experience = models.TextField(blank=True, null=True)
    
    # Profile fields for employers
    company_name = models.CharField(max_length=100, blank=True, null=True)
    company_website = models.URLField(blank=True, null=True)
    
    # Common profile fields
    profile_image = models.ImageField(upload_to=user_profile_image_path, blank=True, null=True)
    profile_thumbnail = models.ImageField(upload_to=user_profile_thumbnail_path, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Set the email as the USERNAME_FIELD
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # Email is already required by default

    objects = CustomUserManager()

    def __str__(self):
        return self.email
