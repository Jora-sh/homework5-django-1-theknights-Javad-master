from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('employer/', views.employer_dashboard, name='employer_dashboard'),
    path('seeker/', views.seeker_dashboard, name='seeker_dashboard'),
    path('applications/', views.applications, name='applications'),
    path('applications/<int:application_id>/', views.application_detail, name='application_detail'),
    path('applications/<int:application_id>/resume/', views.serve_resume, name='serve_resume'),
    path('posted-jobs/', views.posted_jobs, name='posted_jobs'),
    path('jobs/<int:job_id>/applications/', views.job_applications, name='job_applications'),
    
    # Admin moderation views
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/jobs/', views.job_moderation, name='job_moderation'),
    path('admin/jobs/<int:job_id>/', views.job_approval, name='job_approval'),
] 