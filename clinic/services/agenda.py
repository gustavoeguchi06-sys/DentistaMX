import logging

from django.db import transaction

from clinic.models import AcaoAuditoria, StatusConsulta

from .auditoria import registrar_evento

logger = logging.getLogger('clinic')


@transaction.atomic
def agendar_consulta(consulta, *, request=None):
    """Persiste a consulta validando o domínio antes de gravar.

    `full_clean` dispara `Consulta.clean`, que recusa sobreposição de horário
    para a mesma dentista. A constraint equivalente no banco cobre a corrida
    entre duas requisições simultâneas.
    """
    consulta.full_clean(exclude=None)
    consulta.save()
    registrar_evento(
        request, AcaoAuditoria.CRIAR, objeto=consulta,
        descricao=(
            f'Consulta de {consulta.paciente.nome} com {consulta.dentista} '
            f'em {consulta.data_consulta:%d/%m/%Y %H:%M}.'
        ),
    )
    return consulta


@transaction.atomic
def cancelar_consulta(consulta, *, request=None, motivo=''):
    """Cancela em vez de apagar: a consulta cancelada é informação clínica.

    Mantê-la preserva o histórico de faltas e desmarcações, que é justamente o
    que se perde ao remover a linha do banco.
    """
    consulta.status = StatusConsulta.CANCELADA
    consulta.save(update_fields=['status'])
    registrar_evento(
        request, AcaoAuditoria.ALTERAR, objeto=consulta,
        descricao=f'Consulta cancelada. {motivo}'.strip(),
    )
    logger.info('consulta cancelada id=%s', consulta.pk)
    return consulta
