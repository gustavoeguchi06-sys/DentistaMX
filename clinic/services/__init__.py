"""Camada de aplicação.

As views cuidam de HTTP (ler request, escolher template, redirecionar). Toda
regra de negócio que envolve mais de uma tabela, transação ou efeito externo
— criar acesso de paciente, arquivar cadastro, agendar consulta — vive aqui,
onde pode ser testada sem passar por uma requisição.
"""

from .agenda import agendar_consulta, cancelar_consulta
from .auditoria import ip_do_request, registrar_evento
from .autenticacao import (
    autenticar,
    minutos_restantes_de_bloqueio,
    registrar_tentativa,
    esta_bloqueado,
)
from .pacientes import arquivar_paciente, registrar_paciente

__all__ = [
    'agendar_consulta',
    'cancelar_consulta',
    'registrar_evento',
    'ip_do_request',
    'autenticar',
    'esta_bloqueado',
    'minutos_restantes_de_bloqueio',
    'registrar_tentativa',
    'registrar_paciente',
    'arquivar_paciente',
]
