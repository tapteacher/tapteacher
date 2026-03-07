
@login_required(login_url='login_view')
def mark_chat_read(request):
    """API to mark all admin messages as read for the current user"""
    if request.method == 'POST':
        from .models import ChatMessage
        from django.http import JsonResponse
        ChatMessage.objects.filter(user=request.user, sender_is_admin=True, is_read=False).update(is_read=True)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)
