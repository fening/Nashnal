from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.contrib import messages
from django.urls import reverse

class SessionTimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Get last activity time from session
            last_activity = request.session.get('last_activity')
            
            # Check if last_activity exists and if enough time has passed
            if last_activity:
                last_activity = timezone.datetime.fromisoformat(last_activity)
                if timezone.now() - last_activity > timedelta(hours=8):
                    # Clear session and logout user
                    logout(request)
                    messages.warning(request, 'Your session has expired due to inactivity. Please log in again.')
                    return redirect(reverse('login'))

            # Update last activity time
            request.session['last_activity'] = timezone.now().isoformat()

        response = self.get_response(request)
        return response
