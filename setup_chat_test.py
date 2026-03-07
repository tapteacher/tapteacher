import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tapteacher_project.settings')
django.setup()

from core.models import User, ChatMessage

def setup_chat_test():
    # Get test user (ID 6 from previous context, or fallback)
    try:
        user = User.objects.get(id=6) # Adjust ID if needed
    except User.DoesNotExist:
        user = User.objects.first()
        
    print(f"Setting up chat test for user: {user.email} (ID: {user.id})")
    
    # clear existing unread messages to start fresh? Maybe not, just pile on.
    # checking existing
    unread = ChatMessage.objects.filter(user=user, sender_is_admin=True, is_read=False).count()
    print(f"Current unread count: {unread}")
    
    # Create a new unread message from Admin
    msg = ChatMessage.objects.create(
        user=user,
        sender_is_admin=True,
        message_text="This is a test message to trigger blinking.",
        is_read=False
    )
    print(f"Created new unread message: ID {msg.id}")
    
    new_count = ChatMessage.objects.filter(user=user, sender_is_admin=True, is_read=False).count()
    print(f"New unread count: {new_count}")

if __name__ == '__main__':
    setup_chat_test()
