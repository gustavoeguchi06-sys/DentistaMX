from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from clinic.models import Consulta, Dentista, Paciente, StatusConsulta

User = get_user_model()

SENHA_VALIDA = 'SenhaForte!2026'


# ManifestStaticFilesStorage exige `collectstatic` antes de renderizar qualquer
# template. Nos testes isso só acrescentaria uma etapa de build sem cobrir nada.
@override_settings(
    STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}},
)
class ClinicTestCase(TestCase):
    """Base com os atores do domínio já montados."""

    def criar_dentista(self, nome='Dra. Ana'):
        return Dentista.objects.get_or_create(nome=nome)[0]

    def criar_usuaria_dentista(self, username='dra.ana', senha=SENHA_VALIDA):
        usuario = User.objects.create_user(username=username, password=senha, is_staff=True)
        self.criar_dentista().__class__.objects.filter(nome='Dra. Ana').update(usuario=usuario)
        return usuario

    def criar_paciente(self, nome='Paciente Teste', email=None, com_acesso=False):
        usuario = None
        if com_acesso:
            email = email or f'{nome.lower().replace(" ", ".")}@example.com'
            usuario = User.objects.create_user(username=email, email=email, password=SENHA_VALIDA)
        return Paciente.objects.create(nome=nome, email=email, usuario=usuario)

    def criar_consulta(self, paciente=None, dentista=None, quando=None, **extra):
        extra.setdefault('status', StatusConsulta.AGENDADA)
        return Consulta.objects.create(
            paciente=paciente or self.criar_paciente(),
            dentista=dentista or self.criar_dentista(),
            data_consulta=quando or timezone.now() + timedelta(days=1),
            **extra,
        )
