import threading
from django.utils.deprecation import MiddlewareMixin
from .models import UserActivity

# Thread local storage
_thread_locals = threading.local()

def get_current_request():
    """Returns the current request object for this thread"""
    return getattr(_thread_locals, 'request', None)

class UserActivityMiddleware(MiddlewareMixin):
    def process_request(self, request):
        """Store request in thread local storage"""
        _thread_locals.request = request
        
        if request.user.is_authenticated:
            # Skip certain paths where we don't want to track activity
            skip_paths = ['/static/', '/media/', '/favicon.ico', '/admin/jsi18n/']
            if not any(path in request.path for path in skip_paths) and not request.path.startswith('/admin/jsi18n/'):
                UserActivity.objects.create(
                    user=request.user,
                    action='view',
                    action_details=f'Viewed page: {request.path}',
                    ip_address=self.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )

    def process_response(self, request, response):
        """Clear thread local storage"""
        if hasattr(_thread_locals, 'request'):
            del _thread_locals.request
        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')
