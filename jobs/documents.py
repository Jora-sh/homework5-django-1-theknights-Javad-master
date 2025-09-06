from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry
from .models import Job

@registry.register_document
class JobDocument(Document):
    """Elasticsearch document for Job model."""
    
    user = fields.ObjectField(properties={
        'id': fields.IntegerField(),
        'username': fields.TextField(),
        'email': fields.TextField(),
    })
    
    class Index:
        name = 'jobs'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0,
        }
    
    class Django:
        model = Job
        fields = [
            'id',
            'title',
            'company',
            'description',
            'requirements',
            'location',
            'job_type',
            'salary',
            'is_active',
            'is_approved',
            'created_at',
            'updated_at',
        ]
        
        # Only index active and approved jobs
        def get_queryset(self):
            return self.django.model.objects.filter(
                is_active=True,
                is_approved=True
            )
