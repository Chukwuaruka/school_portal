from django.http import HttpResponseForbidden
from functools import wraps

def role_required(required_role):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            if user.is_authenticated and user.role == required_role:
                return view_func(request, *args, **kwargs)
            return HttpResponseForbidden("You do not have permission to access this page.")
        return _wrapped_view
    return decorator

# Shorthand decorators for ease of use
student_required = role_required('student')
teacher_required = role_required('teacher')
admin_required   = role_required('admin')

