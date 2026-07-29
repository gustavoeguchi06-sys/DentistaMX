"""Testes de regressão para as falhas encontradas na auditoria de arquitetura.

Cada teste aqui corresponde a um achado concreto. Eles existem para que a falha
não volte silenciosamente numa alteração futura.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from clinic.models import Consulta, Paciente, Prontuario, StatusConsulta, TentativaLogin

from .base import SENHA_VALIDA, ClinicTestCase

User = get_user_model()


class RotaDeDiagnosticoTest(ClinicTestCase):
    """SEC-01: rota pública que criava conta com is_staff."""

    def test_rota_check_pages_nao_existe_mais(self):
        self.assertEqual(self.client.get('/check-pages/').status_code, 404)

    def test_nome_de_rota_removido_do_urlconf(self):
        with self.assertRaises(NoReverseMatch):
            reverse('check_pages')

    def test_nenhuma_requisicao_anonima_cria_usuario(self):
        antes = User.objects.count()
        for caminho in ['/check-pages/', '/', '/pacientes/', '/agenda/']:
            self.client.get(caminho)
        self.assertEqual(User.objects.count(), antes)


class ControleDeAcessoTest(ClinicTestCase):
    """Confirma que o RBAC segue válido após a refatoração."""

    def setUp(self):
        self.paciente_usuario = User.objects.create_user('paciente@example.com', password=SENHA_VALIDA)
        Paciente.objects.create(nome='Paciente Um', usuario=self.paciente_usuario)

    def test_paciente_nao_acessa_area_da_dentista(self):
        self.client.force_login(self.paciente_usuario)
        for nome in ['dashboard', 'pacientes', 'prontuarios', 'agenda', 'pacientes_export']:
            with self.subTest(rota=nome):
                self.assertEqual(self.client.get(reverse(nome)).status_code, 403)

    def test_anonimo_e_redirecionado_para_login(self):
        resposta = self.client.get(reverse('pacientes'))
        self.assertEqual(resposta.status_code, 302)
        self.assertIn('/login/', resposta.url)

    def test_paciente_so_enxerga_os_proprios_dados(self):
        outro = User.objects.create_user('outro@example.com', password=SENHA_VALIDA)
        Paciente.objects.create(nome='Fulano Reservado', usuario=outro)

        self.client.force_login(self.paciente_usuario)
        conteudo = self.client.get(reverse('portal_paciente')).content.decode()
        self.assertIn('Paciente Um', conteudo)
        self.assertNotIn('Fulano Reservado', conteudo)


class ExclusaoExigePostTest(ClinicTestCase):
    """SEC-03: exclusão respondia a GET, sem token CSRF."""

    def setUp(self):
        self.dentista_usuaria = User.objects.create_user('dra', password=SENHA_VALIDA, is_staff=True)
        self.client.force_login(self.dentista_usuaria)
        self.paciente = self.criar_paciente(nome='Alvo Teste')

    def test_get_nao_arquiva_paciente(self):
        resposta = self.client.get(reverse('paciente_arquivar', args=[self.paciente.pk]))
        self.assertEqual(resposta.status_code, 405)
        self.paciente.refresh_from_db()
        self.assertIsNone(self.paciente.arquivado_em)

    def test_post_arquiva_sem_destruir_historico(self):
        consulta = self.criar_consulta(paciente=self.paciente)
        Prontuario.objects.create(paciente=self.paciente, procedimento='Limpeza')

        resposta = self.client.post(reverse('paciente_arquivar', args=[self.paciente.pk]))
        self.assertEqual(resposta.status_code, 302)

        self.paciente.refresh_from_db()
        self.assertIsNotNone(self.paciente.arquivado_em)
        self.assertEqual(self.paciente.arquivado_por, self.dentista_usuaria)
        # DAT-01: o histórico clínico precisa sobreviver ao arquivamento.
        self.assertTrue(Consulta.objects.filter(pk=consulta.pk).exists())
        self.assertEqual(Prontuario.objects.filter(paciente=self.paciente).count(), 1)

    def test_paciente_arquivado_some_da_listagem(self):
        self.client.post(reverse('paciente_arquivar', args=[self.paciente.pk]))
        # Verifica a lista em si, não o HTML inteiro: o nome ainda aparece
        # (corretamente) na mensagem de confirmação da própria ação.
        pagina = self.client.get(reverse('pacientes')).context['pagina']
        self.assertEqual(list(pagina.object_list), [])

    def test_arquivar_revoga_acesso_ao_portal(self):
        paciente = self.criar_paciente(nome='Com Acesso', com_acesso=True)
        self.client.post(reverse('paciente_arquivar', args=[paciente.pk]))
        paciente.usuario.refresh_from_db()
        self.assertFalse(paciente.usuario.is_active)

    def test_get_nao_cancela_consulta(self):
        consulta = self.criar_consulta(paciente=self.paciente)
        resposta = self.client.get(reverse('consulta_cancelar', args=[consulta.pk]))
        self.assertEqual(resposta.status_code, 405)
        consulta.refresh_from_db()
        self.assertEqual(consulta.status, StatusConsulta.AGENDADA)

    def test_cancelar_preserva_a_consulta(self):
        consulta = self.criar_consulta(paciente=self.paciente)
        self.client.post(reverse('consulta_cancelar', args=[consulta.pk]))
        consulta.refresh_from_db()
        self.assertEqual(consulta.status, StatusConsulta.CANCELADA)

    def test_nao_existe_rota_para_excluir_prontuario(self):
        with self.assertRaises(NoReverseMatch):
            reverse('prontuario_delete')


class ProtecaoDoHistoricoTest(ClinicTestCase):
    """DAT-01: CASCADE apagava consultas e prontuários junto com o paciente."""

    def test_remocao_fisica_do_paciente_e_bloqueada_pelo_banco(self):
        from django.db.models import ProtectedError

        paciente = self.criar_paciente()
        Prontuario.objects.create(paciente=paciente, procedimento='Restauração')

        with self.assertRaises(ProtectedError):
            paciente.delete()


class LogoutTest(ClinicTestCase):
    """SEC-08: logout aceitava GET, então um prefetch desconectava a usuária."""

    def test_get_nao_desloga(self):
        usuario = User.objects.create_user('dra', password=SENHA_VALIDA, is_staff=True)
        self.client.force_login(usuario)
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 200)

    def test_post_desloga(self):
        usuario = User.objects.create_user('dra', password=SENHA_VALIDA, is_staff=True)
        self.client.force_login(usuario)
        self.client.post(reverse('logout'))
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 302)


class BloqueioDeLoginTest(ClinicTestCase):
    """SEC-04: o bloqueio por conta permitia travar a clínica inteira."""

    def setUp(self):
        self.usuario = User.objects.create_user('dra', password=SENHA_VALIDA, is_staff=True)

    def _errar_senha(self, vezes, ip='203.0.113.10'):
        for _ in range(vezes):
            self.client.post(
                reverse('login'),
                {'username': 'dra', 'password': 'errada'},
                REMOTE_ADDR=ip,
            )

    def test_bloqueia_apos_o_limite_no_mesmo_ip(self):
        self._errar_senha(5)
        resposta = self.client.post(
            reverse('login'),
            {'username': 'dra', 'password': SENHA_VALIDA},
            REMOTE_ADDR='203.0.113.10',
        )
        self.assertContains(resposta, 'Muitas tentativas')

    def test_ataque_de_outro_ip_nao_tranca_a_dentista(self):
        """O ponto central: o bloqueio precisa punir a origem, não a conta."""
        self._errar_senha(10, ip='198.51.100.66')  # atacante

        resposta = self.client.post(
            reverse('login'),
            {'username': 'dra', 'password': SENHA_VALIDA},
            REMOTE_ADDR='203.0.113.10',  # a dentista, de outro lugar
            follow=True,
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.context['user'].is_authenticated)

    def test_mensagem_nao_revela_se_a_conta_existe(self):
        inexistente = self.client.post(
            reverse('login'), {'username': 'ninguem', 'password': 'x'}, REMOTE_ADDR='203.0.113.1'
        )
        existente = self.client.post(
            reverse('login'), {'username': 'dra', 'password': 'x'}, REMOTE_ADDR='203.0.113.2'
        )
        self.assertContains(inexistente, 'Usuário ou senha inválidos')
        self.assertContains(existente, 'Usuário ou senha inválidos')

    def test_tentativas_ficam_registradas_para_auditoria(self):
        self._errar_senha(2)
        self.assertEqual(TentativaLogin.objects.filter(sucesso=False).count(), 2)


class AgendaTest(ClinicTestCase):
    """DOM-01: nada impedia dois atendimentos no mesmo horário."""

    def setUp(self):
        self.dentista = self.criar_dentista()
        self.quando = timezone.now() + timedelta(days=2)

    def test_recusa_sobreposicao_de_horario(self):
        from django.core.exceptions import ValidationError

        from clinic.services import agendar_consulta

        self.criar_consulta(dentista=self.dentista, quando=self.quando, duracao_min=60)

        conflitante = Consulta(
            paciente=self.criar_paciente(nome='Outro Paciente'),
            dentista=self.dentista,
            data_consulta=self.quando + timedelta(minutes=30),  # sobrepõe
            duracao_min=30,
        )
        with self.assertRaises(ValidationError):
            agendar_consulta(conflitante)

    def test_aceita_horario_livre_na_sequencia(self):
        from clinic.services import agendar_consulta

        self.criar_consulta(dentista=self.dentista, quando=self.quando, duracao_min=30)

        seguinte = Consulta(
            paciente=self.criar_paciente(nome='Outro Paciente'),
            dentista=self.dentista,
            data_consulta=self.quando + timedelta(minutes=30),  # começa quando a outra acaba
            duracao_min=30,
        )
        agendar_consulta(seguinte)
        self.assertIsNotNone(seguinte.pk)

    def test_consulta_cancelada_libera_o_horario(self):
        from clinic.services import agendar_consulta

        self.criar_consulta(
            dentista=self.dentista, quando=self.quando,
            duracao_min=30, status=StatusConsulta.CANCELADA,
        )
        nova = Consulta(
            paciente=self.criar_paciente(nome='Outro Paciente'),
            dentista=self.dentista,
            data_consulta=self.quando,
            duracao_min=30,
        )
        agendar_consulta(nova)
        self.assertIsNotNone(nova.pk)


class IntegridadeDeDadosTest(ClinicTestCase):
    """DAT-02: sem choices nem unique, o KPI do dashboard errava em silêncio."""

    def test_email_de_paciente_e_unico(self):
        from django.db.utils import IntegrityError

        self.criar_paciente(nome='Primeiro', email='mesmo@example.com')
        with self.assertRaises(IntegrityError):
            Paciente.objects.create(nome='Segundo', email='mesmo@example.com')

    def test_varios_pacientes_podem_ficar_sem_email(self):
        self.criar_paciente(nome='Sem Email Um')
        self.criar_paciente(nome='Sem Email Dois')
        self.assertEqual(Paciente.objects.filter(email__isnull=True).count(), 2)

    def test_status_invalido_e_recusado_na_validacao(self):
        from django.core.exceptions import ValidationError

        paciente = Paciente(nome='Teste', status='Concluida com acento errado')
        with self.assertRaises(ValidationError):
            paciente.full_clean()

    def test_kpi_do_dashboard_conta_o_status_correto(self):
        usuario = User.objects.create_user('dra', password=SENHA_VALIDA, is_staff=True)
        self.client.force_login(usuario)

        agora = timezone.now()
        self.criar_consulta(quando=agora - timedelta(hours=2), status=StatusConsulta.CONCLUIDA)
        self.criar_consulta(
            paciente=self.criar_paciente(nome='Outro'),
            quando=agora - timedelta(hours=1),
            status=StatusConsulta.CONCLUIDA,
        )
        resposta = self.client.get(reverse('dashboard'))
        self.assertEqual(resposta.context['concluidas_mes'], 2)


class AuditoriaTest(ClinicTestCase):
    """SEC-05: não havia como saber quem acessou um prontuário."""

    def setUp(self):
        self.usuario = User.objects.create_user('dra', password=SENHA_VALIDA, is_staff=True)
        self.client.force_login(self.usuario)

    def test_visualizar_ficha_gera_evento(self):
        from clinic.models import AcaoAuditoria, EventoAuditoria

        paciente = self.criar_paciente()
        self.client.get(reverse('paciente_detail', args=[paciente.pk]))

        evento = EventoAuditoria.objects.filter(acao=AcaoAuditoria.VISUALIZAR).first()
        self.assertIsNotNone(evento)
        self.assertEqual(evento.usuario, self.usuario)
        self.assertEqual(evento.objeto_id, str(paciente.pk))

    def test_exportar_csv_gera_evento(self):
        from clinic.models import AcaoAuditoria, EventoAuditoria

        self.client.get(reverse('pacientes_export'))
        self.assertTrue(EventoAuditoria.objects.filter(acao=AcaoAuditoria.EXPORTAR).exists())

    def test_evento_de_auditoria_e_imutavel(self):
        from django.core.exceptions import ValidationError

        from clinic.models import AcaoAuditoria, EventoAuditoria

        evento = EventoAuditoria.objects.create(acao=AcaoAuditoria.CRIAR, objeto_tipo='Paciente')
        evento.descricao = 'adulterado'
        with self.assertRaises(ValidationError):
            evento.save()
        with self.assertRaises(ValidationError):
            evento.delete()


class CadastroDePacienteTest(ClinicTestCase):
    """ARQ: cadastro precisa ser atômico e não deixar conta órfã."""

    def setUp(self):
        self.usuario = User.objects.create_user('dra', password=SENHA_VALIDA, is_staff=True)
        self.client.force_login(self.usuario)

    def _dados(self, **extra):
        base = {
            'nome': 'Novo Paciente',
            'data_nascimento': '10/05/1990',
            'telefone': '11999998888',
            'email': 'novo@example.com',
            'especialidade': 'Ortodontia',
            'status': 'ATIVO',
        }
        base.update(extra)
        return base

    def test_cadastro_cria_paciente_e_acesso(self):
        resposta = self.client.post(reverse('paciente_add'), self._dados())
        self.assertEqual(resposta.status_code, 302)

        paciente = Paciente.objects.get(email='novo@example.com')
        self.assertIsNotNone(paciente.usuario)
        self.assertTrue(paciente.usuario.perfil_seguranca.deve_trocar_senha)

    def test_email_duplicado_nao_deixa_conta_orfa(self):
        self.client.post(reverse('paciente_add'), self._dados())
        contas_antes = User.objects.count()

        resposta = self.client.post(reverse('paciente_add'), self._dados(nome='Outra Pessoa'))

        # Reexibe o formulário com erro no campo e-mail. A mensagem vem do
        # unique do model (barra antes de chegar ao serviço) — defesa em
        # profundidade, já que o serviço também recusaria.
        self.assertEqual(resposta.status_code, 200)
        self.assertIn('email', resposta.context['form'].errors)
        # O que de fato importa: nada foi criado pela metade.
        self.assertEqual(User.objects.count(), contas_antes)
        self.assertEqual(Paciente.objects.filter(nome='Outra Pessoa').count(), 0)

    def test_conta_de_usuario_existente_sem_paciente_e_recusada(self):
        """Caminho que só o serviço cobre: User existe, mas não há Paciente."""
        User.objects.create_user('avulso@example.com', password=SENHA_VALIDA)

        resposta = self.client.post(reverse('paciente_add'), self._dados(email='avulso@example.com'))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Já existe uma conta cadastrada com este e-mail.')
        self.assertEqual(Paciente.objects.filter(email='avulso@example.com').count(), 0)

    def test_senha_temporaria_exige_troca_no_primeiro_acesso(self):
        self.client.post(reverse('paciente_add'), self._dados())
        self.client.post(reverse('logout'))

        paciente = Paciente.objects.get(email='novo@example.com')
        paciente.usuario.set_password(SENHA_VALIDA)
        paciente.usuario.save()

        resposta = self.client.post(
            reverse('login'),
            {'username': 'novo@example.com', 'password': SENHA_VALIDA},
        )
        self.assertRedirects(resposta, reverse('trocar_senha'))


class PaginacaoTest(ClinicTestCase):
    """PER-01: as listagens carregavam a tabela inteira."""

    def test_listagem_de_pacientes_e_paginada(self):
        usuario = User.objects.create_user('dra', password=SENHA_VALIDA, is_staff=True)
        self.client.force_login(usuario)

        Paciente.objects.bulk_create(
            [Paciente(nome=f'Paciente {i:03d}') for i in range(30)]
        )
        pagina = self.client.get(reverse('pacientes')).context['pagina']
        self.assertEqual(len(pagina.object_list), 25)
        self.assertTrue(pagina.has_next())

    def test_busca_filtra_por_nome(self):
        usuario = User.objects.create_user('dra', password=SENHA_VALIDA, is_staff=True)
        self.client.force_login(usuario)

        self.criar_paciente(nome='Joana Prado')
        self.criar_paciente(nome='Carlos Lima')

        conteudo = self.client.get(reverse('pacientes'), {'q': 'joana'}).content.decode()
        self.assertIn('Joana Prado', conteudo)
        self.assertNotIn('Carlos Lima', conteudo)
