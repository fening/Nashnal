from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST
from django.shortcuts import redirect
from functools import wraps

def regular_user_required(view_func):
    """Ensure the user is a regular user (not supervisor or superuser)"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'Supervisor'):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def supervisor_required(view_func):
    """Ensure the user is a supervisor"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request.user, 'role') or request.user.role != 'Supervisor':
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def superuser_required(view_func):
    """Ensure the user is a superuser"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def supervisor_or_superuser_required(view_func):
    """Ensure the user is either a supervisor or superuser"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        is_supervisor = hasattr(request.user, 'role') and request.user.role == 'Supervisor'
        if not (request.user.is_superuser or is_supervisor):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def post_only_regular_user(view_func):
    """Combined decorator for POST-only views requiring regular user access"""
    return login_required(require_POST(regular_user_required(view_func)))

def post_only_supervisor(view_func):
    """Combined decorator for POST-only views requiring supervisor access"""
    return login_required(require_POST(supervisor_required(view_func)))

def post_only_superuser(view_func):
    """Combined decorator for POST-only views requiring superuser access"""
    return login_required(require_POST(superuser_required(view_func)))

def post_only_supervisor_or_superuser(view_func):
    """Combined decorator for POST-only views requiring either supervisor or superuser access"""
    return login_required(require_POST(supervisor_or_superuser_required(view_func)))
