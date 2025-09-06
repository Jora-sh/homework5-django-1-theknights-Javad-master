from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Job, Application


class JobForm(forms.ModelForm):
    """Form for creating/editing job listings."""
    
    class Meta:
        model = Job
        fields = ['title', 'company', 'description', 'requirements', 'location', 'job_type', 'salary', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Job Title'}),
            'company': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company Name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Job Description', 'rows': 5}),
            'requirements': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Job Requirements', 'rows': 5}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Job Location'}),
            'job_type': forms.Select(attrs={'class': 'form-control'}),
            'salary': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ApplicationForm(forms.ModelForm):
    """Form for job applications."""
    
    class Meta:
        model = Application
        fields = ['resume', 'cover_letter']
        widgets = {
            'cover_letter': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Cover Letter', 'rows': 4}),
            'resume': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def clean_resume(self):
        """Validate resume file type and size."""
        resume = self.cleaned_data.get('resume')
        
        # Check if a file was uploaded
        if resume:
            # Check file extension
            ext = resume.name.split('.')[-1].lower()
            valid_extensions = ['pdf', 'doc', 'docx']
            
            if ext not in valid_extensions:
                raise forms.ValidationError(
                    _('Invalid file format. Only PDF, DOC, and DOCX files are allowed.')
                )
            
            # Check file size (2 MB limit)
            if resume.size > 2 * 1024 * 1024:
                raise forms.ValidationError(
                    _('File size too large. Maximum size is 2 MB.')
                )
        
        return resume


class JobSearchForm(forms.Form):
    """Form for searching jobs."""
    keyword = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Job title, company, or keywords'})
    )
    location = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City, state, or zip code'})
    )
    job_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Types')] + list(Job.JOB_TYPE_CHOICES),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    salary = forms.ChoiceField(
        required=False,
        choices=[('', 'All Salaries')] + list(Job.SALARY_CHOICES),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    date_posted = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Any time'),
            ('1', 'Last 24 hours'),
            ('7', 'Last week'),
            ('30', 'Last month'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    ) 