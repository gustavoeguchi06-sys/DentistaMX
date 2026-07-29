import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from clinic.models import Dentista, PerfilSeguranca

User = get_user_model()


class Command(BaseCommand):
    help = 'Cria ou atualiza a conta de acesso de uma dentista da clínica.'

    def add_arguments(self, parser):
        parser.add_argument('--username', help='Nome de usuário para login')
        parser.add_argument('--email', help='E-mail (usado na recuperação de senha)')
        parser.add_argument('--nome', help='Nome completo da dentista')
        parser.add_argument('--cro', help='Número do CRO', default='')

    @transaction.atomic
    def handle(self, *args, **options):
        username = (options.get('username') or input('Usuário de login: ')).strip()
        if not username:
            raise CommandError('Usuário é obrigatório.')

        email = (options.get('email') or input('E-mail (para recuperação de senha): ')).strip()
        if not email:
            raise CommandError('E-mail é obrigatório para permitir recuperação de senha.')

        nome_completo = (options.get('nome') or input('Nome completo: ')).strip()
        if not nome_completo:
            raise CommandError('Nome completo é obrigatório para identificar a profissional na agenda.')

        cro = (options.get('cro') or '').strip()

        senha = getpass.getpass('Senha: ')
        if senha != getpass.getpass('Confirme a senha: '):
            raise CommandError('As senhas não coincidem.')

        try:
            validate_password(senha)
        except ValidationError as exc:
            raise CommandError('Senha inválida: ' + ' '.join(exc.messages))

        usuario, criado = User.objects.get_or_create(username=username, defaults={'email': email})
        usuario.email = email
        usuario.is_staff = True
        usuario.is_active = True
        partes = nome_completo.split(' ', 1)
        usuario.first_name = partes[0]
        usuario.last_name = partes[1] if len(partes) > 1 else ''
        usuario.set_password(senha)
        usuario.save()

        PerfilSeguranca.objects.update_or_create(
            usuario=usuario,
            defaults={'deve_trocar_senha': False},
        )

        # A dentista precisa existir como entidade para ser vinculada às
        # consultas — sem isso, a agenda não teria a quem atribuir atendimentos.
        dentista, _ = Dentista.objects.update_or_create(
            nome=nome_completo,
            defaults={'usuario': usuario, 'cro': cro, 'ativo': True},
        )

        acao = 'criada' if criado else 'atualizada'
        self.stdout.write(self.style.SUCCESS(
            f'Conta "{username}" {acao} e vinculada à dentista "{dentista.nome}".'
        ))
