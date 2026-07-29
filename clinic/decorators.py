from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def dentista_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied('Acesso restrito à dentista responsável pela clínica.')
        return view_func(request, *args, **kwargs)
    return wrapper


def paciente_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'paciente_perfil'):
            raise PermissionDenied('Acesso restrito ao portal do paciente.')
        return view_func(request, *args, **kwargs)
    return wrapper
