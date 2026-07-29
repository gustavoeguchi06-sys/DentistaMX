from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from clinic.models import Dentista

User = get_user_model()

# Contas de teste/diagnóstico que já existiram no projeto. Se alguma reaparecer
# num ambiente publicado, é sinal de que um script de desenvolvimento rodou
# contra a produção.
NOMES_SUSPEITOS = {
    '_diagnostico_interno',
    'demo',
    'preview',
    'teste',
    'test',
    'admin',
    'checkuser123',
}


class Command(BaseCommand):
    help = (
        'Lista as contas com privilégio administrativo e sinaliza as que não '
        'correspondem a uma dentista cadastrada. Use --strict no CI/deploy para '
        'falhar quando houver conta inesperada.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--strict',
            action='store_true',
            help='Encerra com código 1 se encontrar conta administrativa suspeita.',
        )

    def handle(self, *args, **options):
        contas = User.objects.filter(is_staff=True).order_by('username')
        vinculadas = set(
            Dentista.objects.filter(usuario__isnull=False).values_list('usuario__username', flat=True)
        )

        if not contas:
            self.stdout.write(self.style.WARNING('Nenhuma conta administrativa encontrada.'))
            return

        suspeitas = []
        self.stdout.write(f'{len(contas)} conta(s) com acesso administrativo:\n')

        for conta in contas:
            marcadores = []
            if conta.username.lower() in NOMES_SUSPEITOS:
                marcadores.append('NOME DE TESTE')
            if conta.username not in vinculadas and not conta.is_superuser:
                marcadores.append('sem dentista vinculada')
            if not conta.last_login:
                marcadores.append('nunca acessou')

            if marcadores:
                suspeitas.append(conta)
                self.stdout.write(self.style.ERROR(
                    f'  [!] {conta.username:30} {", ".join(marcadores)}'
                ))
            else:
                self.stdout.write(self.style.SUCCESS(f'  [ok] {conta.username}'))

        if not suspeitas:
            self.stdout.write(self.style.SUCCESS('\nNenhuma conta suspeita.'))
            return

        self.stdout.write(self.style.WARNING(
            f'\n{len(suspeitas)} conta(s) merecem revisão. Para remover o acesso:\n'
            '  python manage.py shell -c "'
            'from django.contrib.auth import get_user_model; '
            "get_user_model().objects.filter(username='NOME').update(is_staff=False, is_active=False)\""
        ))

        if options['strict']:
            raise SystemExit(1)
