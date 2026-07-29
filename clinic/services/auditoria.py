import logging

from clinic.models import EventoAuditoria

logger = logging.getLogger('clinic.audit')


def ip_do_request(request):
    """IP de origem, considerando o proxy reverso do provedor de hospedagem.

    X-Forwarded-For é controlado pelo cliente e pode ser forjado; por isso ele
    serve para diagnóstico e para agrupar tentativas de login, nunca como única
    prova de identidade.
    """
    encaminhado = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if encaminhado:
        return encaminhado.split(',')[0].strip() or None
    return request.META.get('REMOTE_ADDR') or None


def registrar_evento(request, acao, objeto=None, descricao='', objeto_tipo=None, objeto_id=None):
    """Grava um evento na trilha de auditoria e no log da aplicação.

    A auditoria nunca pode derrubar a operação que ela observa: se a gravação
    falhar, o erro é logado e a requisição segue.
    """
    usuario = getattr(request, 'user', None)
    if usuario is not None and not usuario.is_authenticated:
        usuario = None

    if objeto is not None:
        objeto_tipo = objeto_tipo or objeto.__class__.__name__
        objeto_id = objeto_id or str(getattr(objeto, 'pk', '') or '')

    try:
        evento = EventoAuditoria.objects.create(
            usuario=usuario,
            acao=acao,
            objeto_tipo=objeto_tipo or '',
            objeto_id=objeto_id or '',
            descricao=descricao[:255],
            ip=ip_do_request(request) if request is not None else None,
        )
    except Exception:  # pragma: no cover - defensivo
        logger.exception('Falha ao gravar evento de auditoria (%s %s)', acao, objeto_tipo)
        return None

    logger.info(
        'auditoria acao=%s tipo=%s id=%s usuario=%s ip=%s %s',
        acao, objeto_tipo, objeto_id, usuario, evento.ip, descricao,
    )
    return evento
