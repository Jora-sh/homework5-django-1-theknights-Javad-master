from django.shortcuts import render
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import render_to_string
from jobs.models import Job


def home(request):
    """Home page view showing recent jobs."""
    # Try using a different template rendering approach
    recent_jobs = Job.objects.filter(is_active=True).order_by('-created_at')[:5]
    
    try:
        # Try to render with template
        return render(request, 'core/home.html', {'recent_jobs': recent_jobs})
    except Exception as e:
        # If template rendering fails, return a basic response with error message
        error_message = f"Template error: {str(e)}"
        return HttpResponse(f"<html><body><h1>Job Portal</h1><p>{error_message}</p></body></html>")


def about(request):
    """About page view."""
    return render(request, 'core/about.html')


def contact(request):
    """Contact page view."""
    return render(request, 'core/contact.html')
