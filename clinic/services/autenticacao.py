import logging
import math
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate
from django.utils import timezone

from clinic.models import TentativaLogin

from .auditoria import ip_do_request

logger = logging.getLogger('clinic.security')


def _normalizar(username):
    return (username or '').strip().lower()


def registrar_tentativa(request, username, sucesso):
    return TentativaLogin.objects.create(
        username=_normalizar(username)[:254],
        ip=ip_do_request(request),
        sucesso=sucesso,
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
    )


def _falhas_recentes(request, username):
    return TentativaLogin.objects.falhas_recentes(
        ip=ip_do_request(request),
        username=_normalizar(username),
        minutos=settings.LOGIN_ATTEMPT_WINDOW_MINUTES,
    )


def esta_bloqueado(request, username):
    """Bloqueio contado por (IP, usuário), nunca só por conta.

    Contar apenas por conta permitiria a qualquer pessoa manter a dentista
    permanentemente fora do sistema errando a senha de propósito. Amarrando ao
    IP de origem, o ataque só afeta quem o está fazendo.
    """
    if not _normalizar(username):
        return False
    return _falhas_recentes(request, username).count() >= settings.LOGIN_MAX_ATTEMPTS


def minutos_restantes_de_bloqueio(request, username):
    ultima = _falhas_recentes(request, username).order_by('-criado_em').first()
    if not ultima:
        return 0
    liberacao = ultima.criado_em + timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)
    restante = (liberacao - timezone.now()).total_seconds()
    return max(1, math.ceil(restante / 60)) if restante > 0 else 0


def autenticar(request, username, password):
    """Autentica registrando a tentativa.

    Retorna (usuario, motivo). `motivo` é 'bloqueado' ou 'credenciais' quando o
    login não acontece — e a view traduz ambos para a MESMA mensagem, para não
    revelar quais contas existem.
    """
    if esta_bloqueado(request, username):
        logger.warning(
            'login bloqueado por excesso de tentativas usuario=%s ip=%s',
            _normalizar(username), ip_do_request(request),
        )
        return None, 'bloqueado'

    usuario = authenticate(request, username=username, password=password)
    registrar_tentativa(request, username, sucesso=usuario is not None)

    if usuario is None:
        logger.info(
            'login falhou usuario=%s ip=%s',
            _normalizar(username), ip_do_request(request),
        )
        return None, 'credenciais'

    logger.info('login ok usuario=%s ip=%s', usuario.get_username(), ip_do_request(request))
    return usuario, ''
