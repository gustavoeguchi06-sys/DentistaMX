from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from clinic.models import Consulta, Dentista, Paciente, Prontuario, StatusConsulta


class Command(BaseCommand):
    help = 'Cria pacientes, consultas e prontuários de exemplo para apresentação/testes.'

    @transaction.atomic
    def handle(self, *args, **options):
        # Dados de demonstração nunca devem alcançar um banco de produção: seria
        # impossível distinguir paciente fictício de paciente real depois.
        from django.conf import settings
        if not settings.DEBUG:
            raise CommandError(
                'seed_demo só roda com DEBUG=True. Em produção este comando criaria '
                'pacientes fictícios indistinguíveis dos reais.'
            )

        dentista, _ = Dentista.objects.get_or_create(
            nome='Dra. Responsável',
            defaults={'cro': 'CRO-SP 00000'},
        )

        exemplos = [
            ('João Silva', '1990-05-12', '11999990001', 'joao.demo@example.com', 'Ortodontia'),
            ('Maria Souza', '1985-09-22', '11999990002', 'maria.demo@example.com', 'Endodontia'),
            ('Carlos Santos', '1978-03-11', '11999990003', 'carlos.demo@example.com', 'Periodontia'),
        ]
        for nome, nascimento, telefone, email, especialidade in exemplos:
            paciente, criado = Paciente.objects.get_or_create(
                nome=nome,
                defaults={
                    'data_nascimento': nascimento,
                    'telefone': telefone,
                    'email': email,
                    'especialidade': especialidade,
                },
            )
            if criado:
                self.stdout.write(self.style.SUCCESS(f'Paciente de exemplo criado: {paciente.nome}'))

        paciente = Paciente.objects.ativos().first()
        if paciente:
            quando = (timezone.now() + timedelta(days=1)).replace(minute=0, second=0, microsecond=0)
            Consulta.objects.get_or_create(
                paciente=paciente,
                dentista=dentista,
                data_consulta=quando,
                defaults={
                    'procedimento': 'Limpeza',
                    'status': StatusConsulta.AGENDADA,
                    'duracao_min': 30,
                },
            )
            Prontuario.objects.get_or_create(
                paciente=paciente,
                procedimento='Avaliação inicial',
                defaults={
                    'dentista': dentista,
                    'observacoes': 'Paciente com boa saúde bucal.',
                },
            )
            self.stdout.write(self.style.SUCCESS('Consulta e prontuário de exemplo criados.'))

        self.stdout.write(self.style.SUCCESS(
            'Seed concluído. Use "python manage.py criar_dentista" para criar o login da dentista.'
        ))
