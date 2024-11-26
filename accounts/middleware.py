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
            current_time = timezone.now()
            last_activity = request.session.get('last_activity')
            
            if last_activity:
                last_activity = timezone.datetime.fromisoformat(last_activity)
                if (current_time - last_activity).seconds > 8 * 3600:  # 8 hours
                    logout(request)
                    return redirect('accounts:logged_out')  # Changed from login to logged_out
            
            request.session['last_activity'] = current_time.isoformat()

        return self.get_response(request)
