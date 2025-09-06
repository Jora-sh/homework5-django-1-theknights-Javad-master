from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_ratelimit.decorators import ratelimit
from django.views.decorators.cache import cache_page

from .forms import UserRegistrationForm, EmployerRegistrationForm, SeekerRegistrationForm, LoginForm
from .models import User
from core.utils import send_verification_email, send_verification_success_email, generate_token
from core.tasks import generate_thumbnail_async, send_email_async
from rest_framework_simplejwt.tokens import RefreshToken
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys

def register(request):
    """View for selecting the type of registration (employer or job seeker)."""
    return render(request, 'accounts/register.html')


def employer_register(request):
    """View for employer registration."""
    if request.user.is_authenticated:
        return redirect('core:home')
    
    if request.method == 'POST':
        form = EmployerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Send welcome email with verification link
            send_verification_email(user, request)
            messages.success(
                request, 
                _('Registration successful! Please check your email to verify your account.')
            )
            return redirect('accounts:login')
    else:
        form = EmployerRegistrationForm()
    
    return render(request, 'accounts/employer_register.html', {'form': form})


def seeker_register(request):
    """View for job seeker registration."""
    if request.user.is_authenticated:
        return redirect('core:home')
    
    if request.method == 'POST':
        form = SeekerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Send welcome email with verification link
            send_verification_email(user, request)
            messages.success(
                request, 
                _('Registration successful! Please check your email to verify your account.')
            )
            return redirect('accounts:login')
    else:
        form = SeekerRegistrationForm()
    
    return render(request, 'accounts/seeker_register.html', {'form': form})


def verify_email(request, token):
    """View for email verification."""
    user = get_object_or_404(User, email_verification_token=token)
    if not user.email_verified:
        user.email_verified = True
        user.email_verification_token = None
        user.save()
        # Send verification success email
        send_verification_success_email(user)
        messages.success(request, _('Email verified successfully! You can now log in.'))
    else:
        messages.info(request, _('Email already verified. You can log in.'))
    
    return redirect('accounts:login')


@login_required
def resend_verification(request):
    """View for resending email verification."""
    if not request.user.email_verified:
        # Generate new token if needed
        if not request.user.email_verification_token:
            request.user.email_verification_token = generate_token()
            request.user.save()
        send_verification_email(request.user, request)
        messages.success(request, _('Verification email sent! Please check your inbox.'))
    else:
        messages.info(request, _('Your email is already verified.'))
    
    return redirect('accounts:profile')


def login_view(request):
    """View for user login.

    This view now issues JWT tokens (access + refresh) and stores them in HttpOnly cookies.
    Templates continue to post the email/password form to this view.
    """
    if request.user.is_authenticated:
        return redirect('core:home')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            # Authenticate credentials
            user = authenticate(request, username=email, password=password)
            
            if user is not None:
                if user.email_verified:
                    # Issue JWT tokens and set as HttpOnly cookies
                    refresh = RefreshToken.for_user(user)
                    access_token = str(refresh.access_token)
                    refresh_token = str(refresh)

                    next_page = request.GET.get('next', None)
                    if next_page:
                        response = redirect(next_page)
                    else:
                        if user.is_employer:
                            response = redirect('dashboard:employer_dashboard')
                        elif user.is_seeker:
                            response = redirect('dashboard:seeker_dashboard')
                        else:
                            response = redirect('core:home')

                    # Set cookies (HttpOnly) — adjust secure and samesite for your deployment
                    response.set_cookie('access_token', access_token, httponly=True, samesite='Lax', max_age=60*60)
                    response.set_cookie('refresh_token', refresh_token, httponly=True, samesite='Lax', max_age=7*24*60*60)

                    # Do not call Django session login (we use JWT now)
                    return response
                else:
                    messages.warning(
                        request, 
                        _('Please verify your email before logging in. <a href="{}">Resend verification email?</a>').format(
                            reverse('accounts:resend_verification')
                        )
                    )
            else:
                messages.error(request, _('Invalid email or password.'))
    else:
        form = LoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


@login_required
def profile(request):
    """View for user profile."""
    return render(request, 'accounts/profile.html')


@login_required
def edit_profile(request):
    """View for editing user profile."""
    if request.method == 'POST':
        # Get form data
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone = request.POST.get('phone')
        
        # Update basic info
        if first_name and last_name:
            request.user.first_name = first_name
            request.user.last_name = last_name
            
            if phone:
                request.user.phone = phone
                
            # Handle profile image upload
            profile_image = request.FILES.get('profile_image')
            if profile_image:
                # Check file extension
                ext = profile_image.name.split('.')[-1].lower()
                valid_extensions = ['jpg', 'jpeg', 'png', 'gif']
                
                if ext not in valid_extensions:
                    messages.error(request, _('Invalid file format. Only JPG, JPEG, PNG, and GIF files are allowed.'))
                    return render(request, 'accounts/edit_profile.html')
                
                # Check file size (2 MB limit)
                if profile_image.size > 2 * 1024 * 1024:
                    messages.error(request, _('File size too large. Maximum size is 2 MB.'))
                    return render(request, 'accounts/edit_profile.html')
                
                # Delete old profile image and thumbnail if they exist
                if request.user.profile_image:
                    request.user.profile_image.delete(save=False)
                if request.user.profile_thumbnail:
                    request.user.profile_thumbnail.delete(save=False)
                
                request.user.profile_image = profile_image
                request.user.save()
                
                # Generate thumbnail asynchronously
                generate_thumbnail_async.delay(
                    request.user.id,
                    request.user.profile_image.path
                )
            
            # Update role-specific fields
            if request.user.is_seeker:
                # Handle resume upload
                resume = request.FILES.get('resume')
                if resume:
                    # Check file extension
                    ext = resume.name.split('.')[-1].lower()
                    valid_extensions = ['pdf', 'doc', 'docx']
                    
                    if ext not in valid_extensions:
                        messages.error(request, _('Invalid file format. Only PDF, DOC, and DOCX files are allowed.'))
                        return render(request, 'accounts/edit_profile.html')
                    
                    # Check file size (2 MB limit)
                    if resume.size > 2 * 1024 * 1024:
                        messages.error(request, _('File size too large. Maximum size is 2 MB.'))
                        return render(request, 'accounts/edit_profile.html')
                    
                    request.user.resume = resume
                
                # Update other seeker fields
                skills = request.POST.get('skills')
                experience = request.POST.get('experience')
                
                if skills:
                    request.user.skills = skills
                
                if experience:
                    request.user.experience = experience
                
            elif request.user.is_employer:
                # Update employer fields
                company_name = request.POST.get('company_name')
                company_website = request.POST.get('company_website')
                
                if company_name:
                    request.user.company_name = company_name
                
                if company_website:
                    request.user.company_website = company_website
            
            # Save all changes
            request.user.save()
            messages.success(request, _('Profile updated successfully!'))
            return redirect('accounts:profile')
        else:
            messages.error(request, _('First name and last name are required.'))
    
    return render(request, 'accounts/edit_profile.html')


def logout_view(request):
    """Handle logout for both JWT and session-based authentication."""
    # Handle JWT token logout
    refresh_token = request.COOKIES.get('refresh_token') or request.POST.get('refresh')
    if refresh_token:
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            pass

    # Handle session-based authentication logout
    logout(request)  # This will clear the session

    # Clear all relevant cookies and session data
    response = redirect('accounts:login')
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')
    
    # Add success message
    messages.success(request, _('You have been successfully logged out.'))
    
    return response


def social_auth_role_selection(request):
    """View for selecting role during social authentication."""
    # Get the partial pipeline data from the session
    partial_token = request.session.get('partial_pipeline_token')
    if not partial_token:
        return redirect('accounts:login')

    if request.method == 'POST':
        role = request.POST.get('role')
        if role in ['seeker', 'employer']:
            # Store the role in the session for the pipeline to use
            request.session['social_auth_role'] = role
            # Continue the pipeline
            backend = request.session.get('partial_pipeline_backend')
            return redirect('social:complete', backend=backend)

    return render(request, 'accounts/role_selection.html', {
        'partial_token': partial_token
    })
