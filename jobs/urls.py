from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    # Class-based views
    path('list/', views.JobListView.as_view(), name='job_list_cbv'),
    path('detail/<int:job_id>/', views.JobDetailView.as_view(), name='job_detail_cbv'),
    path('create/', views.JobCreateView.as_view(), name='job_create'),
    path('update/<int:job_id>/', views.JobUpdateView.as_view(), name='job_update'),
    path('delete/<int:job_id>/', views.JobDeleteView.as_view(), name='job_delete'),
    
    # Function-based views
    path('', views.job_list, name='job_list'),
    path('<int:job_id>/', views.job_detail, name='job_detail'),
    path('post/', views.post_job, name='post_job'),
    path('edit/<int:job_id>/', views.edit_job, name='edit_job'),
    path('delete/<int:job_id>/', views.delete_job, name='delete_job'),
    path('apply/<int:job_id>/', views.apply_job, name='apply_job'),
    path('search/', views.search_jobs, name='search_jobs'),
    path('elasticsearch/', views.JobSearchView.as_view(), name='job_search_elastic'),
] 