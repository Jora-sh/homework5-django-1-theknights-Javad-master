from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from django.core.cache import cache
from django.conf import settings

from .models import Job, Application
from .forms import JobForm, ApplicationForm, JobSearchForm
from elasticsearch_dsl import Q as ESQ
from .documents import JobDocument

# Cache key patterns
JOB_LIST_CACHE_KEY = 'job_list_page_{}'
JOB_DETAIL_CACHE_KEY = 'job_detail_{}'


class EmployerRequiredMixin(UserPassesTestMixin):
    """Mixin to check if the user is an employer."""
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_employer


class StaffRequiredMixin(UserPassesTestMixin):
    """Mixin to check if the user is a staff member."""
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff


@method_decorator(cache_page(settings.CACHE_TTL), name='dispatch')
@method_decorator(ratelimit(key='ip', rate='100/h', method=['GET']), name='dispatch')
class JobListView(ListView):
    """View for listing all active jobs."""
    model = Job
    template_name = 'jobs/job_list.html'
    context_object_name = 'jobs'
    paginate_by = 10
    
    def get_queryset(self):
        """Return filtered jobs based on search criteria with caching."""
        # Create a cache key based on the search parameters
        cache_key = self._get_cache_key()
        queryset = cache.get(cache_key)
        
        if queryset is None:
            queryset = Job.objects.approved()
            
            # Get search parameters from GET request
            keyword = self.request.GET.get('keyword', '')
            location = self.request.GET.get('location', '')
            job_type = self.request.GET.get('job_type', '')
            salary = self.request.GET.get('salary', '')
            date_posted = self.request.GET.get('date_posted', '')
            
            # Apply filters if provided
            if keyword:
                queryset = queryset.filter(
                    Q(title__icontains=keyword) | 
                    Q(company__icontains=keyword) | 
                    Q(description__icontains=keyword)
                )
            
            # Cache the results for 15 minutes
            cache.set(cache_key, queryset, settings.CACHE_TTL)
        
        return queryset
    
    def _get_cache_key(self):
        """Generate a cache key based on the current request parameters."""
        params = []
        for key in sorted(self.request.GET.keys()):
            params.append(f"{key}:{self.request.GET[key]}")
        return f"job_list_{'_'.join(params)}"


@method_decorator(cache_page(settings.CACHE_TTL), name='dispatch')
@method_decorator(ratelimit(key='ip', rate='1000/h', method=['GET']), name='dispatch')
class JobDetailView(DetailView):
    """View for displaying job details."""
    model = Job
    template_name = 'jobs/job_detail.html'
    context_object_name = 'job'
    
    def get_object(self):
        """Get job object with caching."""
        job_id = self.kwargs.get('pk')
        cache_key = JOB_DETAIL_CACHE_KEY.format(job_id)
        job = cache.get(cache_key)
        
        if job is None:
            job = super().get_object()
            cache.set(cache_key, job, settings.CACHE_TTL)
        
        return job
    
    def get_queryset(self):
        """Return approved jobs or jobs owned by current user."""
        if self.request.user.is_authenticated and self.request.user.is_employer:
            # Employers can see their own jobs even if not approved
            return Job.objects.filter(
                Q(is_active=True, is_approved=True) | 
                Q(user=self.request.user)
            )
        elif self.request.user.is_authenticated and self.request.user.is_staff:
            # Staff can see all jobs
            return Job.objects.all()
        else:
            # Regular users can only see approved jobs
            return Job.objects.filter(is_active=True, is_approved=True)
    
    def get_context_data(self, **kwargs):
        """Add application form to context for job seekers."""
        context = super().get_context_data(**kwargs)
        
        # Add application form for job seekers who haven't applied yet
        if self.request.user.is_authenticated and self.request.user.is_seeker:
            # Check if user has already applied
            has_applied = Application.objects.filter(
                job=self.object,
                user=self.request.user
            ).exists()
            
            if not has_applied:
                context['application_form'] = ApplicationForm()
            
            context['has_applied'] = has_applied
        
        return context


class JobCreateView(LoginRequiredMixin, EmployerRequiredMixin, CreateView):
    """View for creating new job listings."""
    model = Job
    form_class = JobForm
    template_name = 'jobs/job_form.html'
    success_url = reverse_lazy('dashboard:posted_jobs')
    
    def form_valid(self, form):
        """Set the user before saving the form."""
        form.instance.user = self.request.user
        messages.success(self.request, _('Job posting created successfully! It will be visible to job seekers after admin approval.'))
        return super().form_valid(form)


class JobUpdateView(LoginRequiredMixin, EmployerRequiredMixin, UpdateView):
    """View for updating job listings."""
    model = Job
    form_class = JobForm
    template_name = 'jobs/job_form.html'
    pk_url_kwarg = 'job_id'
    success_url = reverse_lazy('dashboard:posted_jobs')
    
    def get_queryset(self):
        """Limit to jobs created by the current user."""
        return Job.objects.filter(user=self.request.user)
    
    def form_valid(self, form):
        """Reset approval status when job is updated."""
        if 'description' in form.changed_data or 'title' in form.changed_data or 'requirements' in form.changed_data:
            form.instance.is_approved = False
            messages.info(self.request, _('Your job posting has been updated and will require admin approval again.'))
        else:
            messages.success(self.request, _('Job posting updated successfully!'))
        return super().form_valid(form)


class JobDeleteView(LoginRequiredMixin, EmployerRequiredMixin, DeleteView):
    """View for deleting job listings."""
    model = Job
    template_name = 'jobs/job_confirm_delete.html'
    pk_url_kwarg = 'job_id'
    success_url = reverse_lazy('dashboard:posted_jobs')
    
    def get_queryset(self):
        """Limit to jobs created by the current user."""
        return Job.objects.filter(user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        """Add success message."""
        messages.success(request, _('Job posting deleted successfully!'))
        return super().delete(request, *args, **kwargs)


# Function-based views for additional functionality

def job_list(request):
    """Function-based view for job listings with pagination handling."""
    jobs_list = Job.objects.approved()
    search_form = JobSearchForm(request.GET or None)
    
    # Apply search filters if form is valid
    if search_form.is_valid():
        keyword = search_form.cleaned_data.get('keyword')
        location = search_form.cleaned_data.get('location')
        job_type = search_form.cleaned_data.get('job_type')
        salary = search_form.cleaned_data.get('salary')
        date_posted = search_form.cleaned_data.get('date_posted')
        
        if keyword:
            jobs_list = jobs_list.filter(
                Q(title__icontains=keyword) | 
                Q(company__icontains=keyword) | 
                Q(description__icontains=keyword)
            )
        
        if location:
            jobs_list = jobs_list.filter(location__icontains=location)
        
        if job_type:
            jobs_list = jobs_list.filter(job_type=job_type)
            
        if salary:
            jobs_list = jobs_list.filter(salary=salary)
        
        if date_posted:
            from datetime import datetime, timedelta
            days = int(date_posted)
            date_threshold = datetime.now() - timedelta(days=days)
            jobs_list = jobs_list.filter(created_at__gte=date_threshold)
    
    # Pagination
    paginator = Paginator(jobs_list, 10)
    page = request.GET.get('page')
    
    try:
        jobs = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        jobs = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page of results
        jobs = paginator.page(paginator.num_pages)
    
    return render(request, 'jobs/job_list.html', {
        'jobs': jobs,
        'search_form': search_form,
    })


def job_detail(request, job_id):
    """Function-based view for job details."""
    # Different queryset based on user role
    if request.user.is_authenticated:
        if request.user.is_employer:
            # Employers can see their own jobs even if not approved
            job_queryset = Job.objects.filter(
                Q(is_active=True, is_approved=True) | Q(user=request.user)
            )
        elif request.user.is_staff:
            # Staff can see all jobs
            job_queryset = Job.objects.all()
        else:
            # Job seekers can only see approved jobs
            job_queryset = Job.objects.filter(is_active=True, is_approved=True)
    else:
        # Anonymous users can only see approved jobs
        job_queryset = Job.objects.filter(is_active=True, is_approved=True)
    
    job = get_object_or_404(job_queryset, id=job_id)
    
    has_applied = False
    application_form = None
    
    # Check if user is authenticated and is a job seeker
    if request.user.is_authenticated and request.user.is_seeker:
        # Check if user has already applied
        has_applied = Application.objects.filter(
            job=job,
            user=request.user
        ).exists()
        
        # Create application form if not applied
        if not has_applied:
            if request.method == 'POST':
                application_form = ApplicationForm(request.POST, request.FILES)
                if application_form.is_valid():
                    application = application_form.save(commit=False)
                    application.job = job
                    application.user = request.user
                    application.save()
                    
                    from core.utils import send_application_notification_email
                    send_application_notification_email(application)
                    
                    messages.success(request, _('Application submitted successfully!'))
                    return redirect('jobs:job_detail', job_id=job.id)
            else:
                application_form = ApplicationForm()
    
    return render(request, 'jobs/job_detail.html', {
        'job': job,
        'has_applied': has_applied,
        'application_form': application_form,
    })


def apply_job(request, job_id):
    """View for applying to a job."""
    if not request.user.is_authenticated:
        messages.warning(request, _('Please log in to apply for jobs.'))
        return redirect('accounts:login')
    
    if not request.user.is_seeker:
        messages.warning(request, _('Only job seekers can apply for jobs.'))
        return redirect('jobs:job_detail', job_id=job_id)
    
    job = get_object_or_404(Job, id=job_id, is_active=True)
    
    # Check if already applied
    if Application.objects.filter(job=job, user=request.user).exists():
        messages.info(request, _('You have already applied for this job.'))
        return redirect('jobs:job_detail', job_id=job.id)
    
    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save(commit=False)
            application.job = job
            application.user = request.user
            application.save()
            
            from core.utils import send_application_notification_email
            send_application_notification_email(application)
            
            messages.success(request, _('Application submitted successfully!'))
            return redirect('jobs:job_detail', job_id=job.id)
    else:
        form = ApplicationForm()
    
    return render(request, 'jobs/apply_job.html', {
        'job': job,
        'form': form
    })


def post_job(request):
    """Function-based view for job creation."""
    if not request.user.is_authenticated:
        messages.warning(request, _('Please log in to post jobs.'))
        return redirect('accounts:login')
    
    if not request.user.is_employer:
        messages.warning(request, _('Only employers can post jobs.'))
        return redirect('jobs:job_list')
    
    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.user = request.user
            job.save()
            messages.success(request, _('Job posting created successfully!'))
            return redirect('dashboard:posted_jobs')
    else:
        form = JobForm()
    
    return render(request, 'jobs/job_form.html', {'form': form})


def edit_job(request, job_id):
    """Function-based view for job editing."""
    if not request.user.is_authenticated or not request.user.is_employer:
        messages.warning(request, _('Only employers can edit jobs.'))
        return redirect('jobs:job_list')
    
    job = get_object_or_404(Job, id=job_id, user=request.user)
    
    if request.method == 'POST':
        form = JobForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, _('Job posting updated successfully!'))
            return redirect('dashboard:posted_jobs')
    else:
        form = JobForm(instance=job)
    
    return render(request, 'jobs/job_form.html', {'form': form})


def delete_job(request, job_id):
    """Function-based view for job deletion."""
    if not request.user.is_authenticated or not request.user.is_employer:
        messages.warning(request, _('Only employers can delete jobs.'))
        return redirect('jobs:job_list')
    
    job = get_object_or_404(Job, id=job_id, user=request.user)
    
    if request.method == 'POST':
        job.delete()
        messages.success(request, _('Job posting deleted successfully!'))
        return redirect('dashboard:posted_jobs')
    
    return render(request, 'jobs/job_confirm_delete.html', {'job': job})


def search_jobs(request):
    """View for searching jobs."""
    jobs = Job.objects.approved()
    search_form = JobSearchForm(request.GET or None)
    
    if search_form.is_valid():
        keyword = search_form.cleaned_data.get('keyword')
        location = search_form.cleaned_data.get('location')
        job_type = search_form.cleaned_data.get('job_type')
        salary = search_form.cleaned_data.get('salary')
        date_posted = search_form.cleaned_data.get('date_posted')
        
        if keyword:
            jobs = jobs.filter(
                Q(title__icontains=keyword) | 
                Q(company__icontains=keyword) | 
                Q(description__icontains=keyword)
            )
        
        if location:
            jobs = jobs.filter(location__icontains=location)
        
        if job_type:
            jobs = jobs.filter(job_type=job_type)
            
        if salary:
            jobs = jobs.filter(salary=salary)
        
        if date_posted:
            from datetime import datetime, timedelta
            days = int(date_posted)
            date_threshold = datetime.now() - timedelta(days=days)
            jobs = jobs.filter(created_at__gte=date_threshold)
    
    # Pagination
    paginator = Paginator(jobs, 10)
    page = request.GET.get('page')
    
    try:
        jobs = paginator.page(page)
    except PageNotAnInteger:
        jobs = paginator.page(1)
    except EmptyPage:
        jobs = paginator.page(paginator.num_pages)
    
    return render(request, 'jobs/search_results.html', {
        'jobs': jobs,
        'search_form': search_form,
    })


class JobSearchView(ListView):
    """View for searching jobs using Elasticsearch."""
    model = Job
    template_name = 'jobs/job_search.html'
    context_object_name = 'jobs'
    paginate_by = 10
    
    def get_queryset(self):
        """Return search results from Elasticsearch."""
        query = self.request.GET.get('q', '')
        location = self.request.GET.get('location', '')
        job_type = self.request.GET.get('job_type', '')
        
        # Base search query
        search = JobDocument.search()
        
        if query:
            # Multi-match query across multiple fields
            search = search.query(
                ESQ('multi_match',
                    query=query,
                    fields=['title^3', 'company^2', 'description', 'requirements'],
                    fuzziness='AUTO'
                )
            )
        
        # Add filters
        if location:
            search = search.filter('match', location=location)
        if job_type:
            search = search.filter('term', job_type=job_type)
        
        # Add sorting
        search = search.sort('-created_at')
        
        # Execute search
        response = search.execute()
        
        return response

    def get_context_data(self, **kwargs):
        """Add search form to context."""
        context = super().get_context_data(**kwargs)
        context['search_form'] = JobSearchForm(self.request.GET)
        return context
