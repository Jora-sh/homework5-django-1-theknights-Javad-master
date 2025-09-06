from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, Count
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, FileResponse
import os

from jobs.models import Job, Application


@login_required
def dashboard(request):
    """Main dashboard view, redirects to appropriate dashboard based on user role."""
    if request.user.is_employer:
        return redirect('dashboard:employer_dashboard')
    elif request.user.is_seeker:
        return redirect('dashboard:seeker_dashboard')
    elif request.user.is_staff:
        return redirect('dashboard:admin_dashboard')
    else:
        messages.warning(request, _('Invalid user role.'))
        return redirect('core:home')


@login_required
def employer_dashboard(request):
    """Dashboard view for employers."""
    if not request.user.is_employer:
        messages.warning(request, _('You do not have access to this page.'))
        return redirect('core:home')
    
    jobs = Job.objects.filter(user=request.user).order_by('-created_at')
    
    # Get application statistics
    total_applications = 0
    application_stats = {}
    
    for job in jobs:
        job_applications = job.applications.count()
        total_applications += job_applications
        application_stats[job.id] = job_applications
    
    active_jobs = jobs.filter(is_active=True).count()
    approved_jobs = jobs.filter(is_active=True, is_approved=True).count()
    pending_jobs = jobs.filter(is_active=True, is_approved=False).count()
    
    return render(request, 'dashboard/employer_dashboard.html', {
        'jobs': jobs,
        'active_jobs': active_jobs,
        'approved_jobs': approved_jobs,
        'pending_jobs': pending_jobs,
        'total_jobs': jobs.count(),
        'total_applications': total_applications,
        'application_stats': application_stats,
    })


@login_required
def seeker_dashboard(request):
    """Dashboard view for job seekers."""
    if not request.user.is_seeker:
        messages.warning(request, _('You do not have access to this page.'))
        return redirect('core:home')
    
    applications = Application.objects.filter(user=request.user).order_by('-applied_at')
    
    # Get status counts
    pending = applications.filter(status='pending').count()
    reviewing = applications.filter(status='reviewing').count()
    shortlisted = applications.filter(status='shortlisted').count()
    rejected = applications.filter(status='rejected').count()
    accepted = applications.filter(status='accepted').count()
    
    return render(request, 'dashboard/seeker_dashboard.html', {
        'applications': applications,
        'total_applications': applications.count(),
        'pending': pending,
        'reviewing': reviewing,
        'shortlisted': shortlisted,
        'rejected': rejected,
        'accepted': accepted,
    })


@login_required
def applications(request):
    """View for all applications (for job seekers)."""
    if not request.user.is_seeker:
        messages.warning(request, _('You do not have access to this page.'))
        return redirect('core:home')
    
    applications = Application.objects.filter(user=request.user).order_by('-applied_at')
    return render(request, 'dashboard/applications.html', {'applications': applications})


@login_required
def job_applications(request, job_id):
    """View for applications for a specific job (for employers)."""
    if not request.user.is_employer:
        messages.warning(request, _('You do not have access to this page.'))
        return redirect('core:home')
    
    job = get_object_or_404(Job, id=job_id, user=request.user)
    applications = job.applications.all().order_by('-applied_at')
    
    # Get status counts
    pending = applications.filter(status='pending').count()
    reviewing = applications.filter(status='reviewing').count()
    shortlisted = applications.filter(status='shortlisted').count()
    rejected = applications.filter(status='rejected').count()
    accepted = applications.filter(status='accepted').count()
    
    return render(request, 'dashboard/job_applications.html', {
        'job': job,
        'applications': applications,
        'total_applications': applications.count(),
        'pending': pending,
        'reviewing': reviewing,
        'shortlisted': shortlisted,
        'rejected': rejected,
        'accepted': accepted,
    })


@login_required
def application_detail(request, application_id):
    """View for application details."""
    application = get_object_or_404(Application, id=application_id)
    
    # Check permission
    if request.user.is_seeker and application.user != request.user:
        messages.warning(request, _('You do not have access to this application.'))
        return redirect('dashboard:applications')
    
    if request.user.is_employer and application.job.user != request.user:
        messages.warning(request, _('You do not have access to this application.'))
        return redirect('dashboard:posted_jobs')
    
    # If employer is updating the status
    if request.user.is_employer and request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in [status[0] for status in Application.STATUS_CHOICES]:
            application.status = new_status
            application.save()
            
            # If it's an AJAX request, return JSON response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                status_display = dict(Application.STATUS_CHOICES)[new_status]
                badge_class = {
                    'pending': 'bg-warning text-dark',
                    'reviewing': 'bg-info',
                    'shortlisted': 'bg-primary',
                    'rejected': 'bg-danger',
                    'accepted': 'bg-success'
                }[new_status]
                
                return JsonResponse({
                    'success': True,
                    'message': _('Application status updated successfully.'),
                    'status': new_status,
                    'status_display': status_display,
                    'badge_class': badge_class
                })
            
            messages.success(request, _('Application status updated successfully.'))
            return redirect('dashboard:application_detail', application_id=application.id)
    
    return render(request, 'dashboard/application_detail.html', {'application': application})


@login_required
def posted_jobs(request):
    """View for all jobs posted by an employer."""
    if not request.user.is_employer:
        messages.warning(request, _('You do not have access to this page.'))
        return redirect('core:home')
    
    jobs = Job.objects.filter(user=request.user).order_by('-created_at')
    
    # Get application statistics
    total_applications = 0
    application_stats = {}
    
    for job in jobs:
        job_applications = job.applications.count()
        total_applications += job_applications
        application_stats[job.id] = job_applications
    
    return render(request, 'dashboard/posted_jobs.html', {
        'jobs': jobs,
        'total_applications': total_applications,
        'application_stats': application_stats,
    })


@staff_member_required
def admin_dashboard(request):
    """Dashboard view for admins."""
    # Get job statistics
    total_jobs = Job.objects.count()
    active_jobs = Job.objects.filter(is_active=True).count()
    pending_approval = Job.objects.filter(is_active=True, is_approved=False).count()
    approved_jobs = Job.objects.filter(is_active=True, is_approved=True).count()
    
    # Get application statistics
    total_applications = Application.objects.count()
    pending_applications = Application.objects.filter(status='pending').count()
    accepted_applications = Application.objects.filter(status='accepted').count()
    
    # Get top employers
    top_employers = Job.objects.values('user__email', 'user__first_name', 'user__last_name', 'user__company_name') \
        .annotate(job_count=Count('id')) \
        .order_by('-job_count')[:5]
    
    # Recent jobs pending approval
    pending_jobs = Job.objects.filter(is_active=True, is_approved=False).order_by('-created_at')[:10]
    
    return render(request, 'dashboard/admin_dashboard.html', {
        'total_jobs': total_jobs,
        'active_jobs': active_jobs,
        'pending_approval': pending_approval,
        'approved_jobs': approved_jobs,
        'total_applications': total_applications,
        'pending_applications': pending_applications,
        'accepted_applications': accepted_applications,
        'top_employers': top_employers,
        'pending_jobs': pending_jobs,
    })


@staff_member_required
def job_moderation(request):
    """View for job moderation."""
    # Get filtering and search parameters
    status = request.GET.get('status', 'pending')
    search_query = request.GET.get('q', '')
    
    # Base queryset
    if status == 'approved':
        jobs = Job.objects.filter(is_approved=True)
    elif status == 'all':
        jobs = Job.objects.all()
    else:  # Default to pending
        jobs = Job.objects.filter(is_active=True, is_approved=False)
    
    # Apply search if provided
    if search_query:
        jobs = jobs.filter(
            Q(title__icontains=search_query) |
            Q(company__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    
    jobs = jobs.order_by('-created_at')
    
    return render(request, 'dashboard/job_moderation.html', {
        'jobs': jobs,
        'status': status,
        'search_query': search_query,
    })


@staff_member_required
def job_approval(request, job_id):
    """View to approve or reject a job."""
    job = get_object_or_404(Job, id=job_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            job.is_approved = True
            job.save()
            messages.success(request, _(f'Job "{job.title}" has been approved.'))
        elif action == 'reject':
            job.is_approved = False
            job.save()
            messages.success(request, _(f'Job "{job.title}" has been rejected.'))
        
        return redirect('dashboard:job_moderation')
    
    return render(request, 'dashboard/job_approval.html', {
        'job': job,
    })


@login_required
def serve_resume(request, application_id):
    """Serve resume file with proper headers for preview."""
    application = get_object_or_404(Application, id=application_id)
    
    # Check permission
    if request.user.is_seeker and application.user != request.user:
        messages.warning(request, _('You do not have access to this resume.'))
        return redirect('dashboard:applications')
    
    if request.user.is_employer and application.job.user != request.user:
        messages.warning(request, _('You do not have access to this resume.'))
        return redirect('dashboard:posted_jobs')
    
    # Get the file path
    file_path = application.resume.path
    
    # Check if file exists
    if not os.path.exists(file_path):
        messages.error(request, _('Resume file not found.'))
        return redirect('dashboard:application_detail', application_id=application.id)
    
    # Serve the file with inline content disposition
    response = FileResponse(open(file_path, 'rb'))
    response['Content-Type'] = 'application/pdf'
    response['Content-Disposition'] = 'inline; filename="{}"'.format(os.path.basename(file_path))
    return response
