from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from clinic.models import Paciente, Consulta, EstoqueItem, TransacaoFinanceira, Prontuario

class Command(BaseCommand):
    help = 'Seed demo user and sample data for presentation'

    def handle(self, *args, **options):
        User = get_user_model()
        demo, created = User.objects.get_or_create(username='demo', defaults={'email':'demo@example.com','is_staff':True})
        if created or not demo.check_password('demo123'):
            demo.set_password('demo123')
            demo.save()
            self.stdout.write(self.style.SUCCESS('Created demo user demo/demo123'))
        else:
            self.stdout.write('Demo user exists')

        # create sample patients
        pacientes = [
            {'nome':'João Silva','data_nascimento':'1990-05-12','telefone':'(11) 99999-0001','especialidade':'Ortodontia'},
            {'nome':'Maria Souza','data_nascimento':'1985-09-22','telefone':'(11) 99999-0002','especialidade':'Endodontia'},
            {'nome':'Carlos Santos','data_nascimento':'1978-03-11','telefone':'(11) 99999-0003','especialidade':'Periodontia'},
        ]
        for p in pacientes:
            obj, created = Paciente.objects.get_or_create(nome=p['nome'], defaults={
                'data_nascimento':p['data_nascimento'],'telefone':p['telefone'],'email':'','especialidade':p['especialidade']
            })
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created paciente {obj.nome}"))

        # create estoque items
        estoque_items = [
            {'nome':'Luvas','quantidade':50,'unidade':'un','nivel_alerta':'Normal'},
            {'nome':'Máscaras','quantidade':30,'unidade':'un','nivel_alerta':'Normal'},
            {'nome':'Anestésico','quantidade':5,'unidade':'amp','nivel_alerta':'Baixo'},
        ]
        for item in estoque_items:
            obj, created = EstoqueItem.objects.get_or_create(nome=item['nome'], defaults={'quantidade':item['quantidade'],'unidade':item['unidade'],'nivel_alerta':item['nivel_alerta']})
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created estoque item {obj.nome}"))

        # create a consultation for first paciente
        paciente = Paciente.objects.first()
        if paciente:
            Consulta.objects.get_or_create(paciente=paciente, data_consulta=timezone.now() + timezone.timedelta(days=1), defaults={'procedimento':'Limpeza','dentista':'Dr. Demo','status':'Agendada'})
            self.stdout.write(self.style.SUCCESS('Created sample consulta'))

        # create financial transaction
        TransacaoFinanceira.objects.get_or_create(descricao='Pagamento de consulta', data_operacao=timezone.now(), defaults={'tipo':'Receita','valor':120.00,'categoria':'Consultas'})
        self.stdout.write(self.style.SUCCESS('Created sample transacao financeira'))

        # create prontuario
        if paciente:
            Prontuario.objects.get_or_create(paciente=paciente, defaults={'procedimento':'Avaliação inicial','observacoes':'Paciente com boa saúde bucal.'})
            self.stdout.write(self.style.SUCCESS('Created sample prontuario'))

        self.stdout.write(self.style.SUCCESS('Seeding complete'))
