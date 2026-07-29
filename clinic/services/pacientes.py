import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import get_random_string

from clinic.models import AcaoAuditoria, Paciente, PerfilSeguranca

from .auditoria import registrar_evento

logger = logging.getLogger('clinic')

User = get_user_model()

# Alfabeto sem caracteres ambíguos (0/O, 1/l/I): a senha é ditada por telefone
# com frequência.
SENHA_TEMP_ALFABETO = 'abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'


def gerar_senha_temporaria():
    return get_random_string(12, allowed_chars=SENHA_TEMP_ALFABETO)


class EmailJaCadastrado(Exception):
    """O e-mail informado já pertence a uma conta de acesso."""


@transaction.atomic
def registrar_paciente(paciente, *, request=None):
    """Cria o paciente e o acesso dele ao portal, de forma atômica.

    Sem a transação, uma falha depois de `create_user` deixaria uma conta órfã
    sem paciente associado — e o e-mail ficaria permanentemente bloqueado para
    um novo cadastro.
    """
    email = (paciente.email or '').strip().lower()
    if not email:
        raise ValueError('E-mail é obrigatório para criar o acesso do paciente.')

    # select_for_update não se aplica a uma linha inexistente; a garantia real
    # contra corrida vem do unique do banco (em User.username e Paciente.email),
    # e este teste só existe para produzir uma mensagem de erro amigável.
    if User.objects.filter(username__iexact=email).exists():
        raise EmailJaCadastrado(email)

    senha_temp = gerar_senha_temporaria()
    usuario = User.objects.create_user(username=email, email=email, password=senha_temp)
    PerfilSeguranca.objects.create(usuario=usuario, deve_trocar_senha=True)

    paciente.email = email
    paciente.usuario = usuario
    paciente.save()

    registrar_evento(
        request, AcaoAuditoria.CRIAR, objeto=paciente,
        descricao=f'Paciente cadastrado com acesso ao portal ({email}).',
    )
    return paciente, senha_temp


@transaction.atomic
def arquivar_paciente(paciente, *, usuario_responsavel, request=None):
    """Arquiva o cadastro em vez de apagá-lo.

    Consultas e prontuários permanecem íntegros: são registro clínico com prazo
    legal de guarda. O acesso ao portal é revogado desativando a conta, o que
    também preserva a autoria dos registros já feitos.
    """
    if paciente.arquivado:
        return paciente

    paciente.arquivado_em = timezone.now()
    paciente.arquivado_por = usuario_responsavel
    paciente.status = 'INATIVO'
    paciente.save(update_fields=['arquivado_em', 'arquivado_por', 'status'])

    if paciente.usuario_id:
        conta = paciente.usuario
        conta.is_active = False
        conta.save(update_fields=['is_active'])

    registrar_evento(
        request, AcaoAuditoria.ARQUIVAR, objeto=paciente,
        descricao=f'Cadastro arquivado e acesso revogado ({paciente.nome}).',
    )
    logger.info('paciente arquivado id=%s por=%s', paciente.pk, usuario_responsavel)
    return paciente


def enviar_credenciais(paciente, senha_temp, login_url):
    """Envia a senha temporária. Retorna True se o e-mail saiu.

    Chamado por `transaction.on_commit`: se a transação de cadastro falhar, o
    paciente não recebe credencial de uma conta que não existe.
    """
    corpo = (
        f'Olá, {paciente.nome}!\n\n'
        f'Sua conta no portal da MX Odontologia foi criada.\n\n'
        f'Acesse: {login_url}\n'
        f'Usuário (e-mail): {paciente.email}\n'
        f'Senha temporária: {senha_temp}\n\n'
        f'Por segurança, você precisará trocar essa senha no primeiro acesso.'
    )
    try:
        send_mail(
            'Seu acesso ao portal MX Odontologia',
            corpo,
            settings.DEFAULT_FROM_EMAIL,
            [paciente.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception('Falha ao enviar credenciais para paciente id=%s', paciente.pk)
        return False
    return True
