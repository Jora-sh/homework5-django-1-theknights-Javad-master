from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.utils.timesince import timesince
from .models import Notification

@login_required
def notification_list(request):
    """View for listing user's notifications"""
    notifications = Notification.objects.filter(recipient=request.user)
    
    # Handle JSON request for dropdown notifications
    if request.GET.get('format') == 'json':
        unread_count = notifications.filter(is_read=False).count()
        recent_notifications = notifications[:5]  # Get 5 most recent notifications
        
        notifications_data = []
        for notification in recent_notifications:
            notifications_data.append({
                'id': notification.id,
                'title': notification.title,
                'message': notification.message,
                'type': notification.notification_type,
                'is_read': notification.is_read,
                'created_at': timesince(notification.created_at) + ' ago'
            })
        
        return JsonResponse({
            'unread_count': unread_count,
            'notifications': notifications_data
        })
    
    # Handle regular page request
    paginator = Paginator(notifications, 10)  # Show 10 notifications per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'notifications/notification_list.html', {'page_obj': page_obj})

@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """API endpoint for marking a notification as read"""
    try:
        notification = Notification.objects.get(id=notification_id, recipient=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'status': 'success'})
    except Notification.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Notification not found'}, status=404)

@login_required
@require_POST
def mark_all_notifications_read(request):
    """API endpoint for marking all notifications as read"""
    Notification.objects.filter(recipient=request.user).update(is_read=True)
    return JsonResponse({'status': 'success'})
