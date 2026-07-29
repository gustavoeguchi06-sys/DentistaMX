from datetime import date, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class StatusPaciente(models.TextChoices):
    ATIVO = 'ATIVO', 'Ativo'
    INATIVO = 'INATIVO', 'Inativo'


class StatusConsulta(models.TextChoices):
    AGENDADA = 'AGENDADA', 'Agendada'
    CONFIRMADA = 'CONFIRMADA', 'Confirmada'
    CONCLUIDA = 'CONCLUIDA', 'Concluída'
    CANCELADA = 'CANCELADA', 'Cancelada'


class Dentista(models.Model):
    """Profissional responsável pelo atendimento.

    Existe como entidade, e não como texto livre na consulta, para que o filtro
    da agenda não trate "Dra. Ana", "Ana Silva" e "ana silva" como três pessoas
    diferentes — e para que a clínica possa crescer para mais de uma
    profissional sem alteração de modelagem.
    """

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='dentista_perfil',
    )
    nome = models.CharField(max_length=120, unique=True)
    cro = models.CharField('CRO', max_length=30, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'dentista'
        verbose_name_plural = 'dentistas'

    def __str__(self):
        return self.nome


class PacienteQuerySet(models.QuerySet):
    def ativos(self):
        return self.filter(arquivado_em__isnull=True)

    def arquivados(self):
        return self.filter(arquivado_em__isnull=False)


class Paciente(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='paciente_perfil',
    )
    nome = models.CharField(max_length=255, db_index=True)
    data_nascimento = models.DateField(null=True, blank=True)
    telefone = models.CharField(max_length=50, blank=True)
    # O e-mail é a identidade de acesso ao portal, então precisa ser único no
    # banco: validar apenas no formulário deixa passar duas requisições
    # simultâneas. NULL é permitido (e vários NULLs não colidem) para pacientes
    # cadastrados sem acesso ao portal.
    email = models.EmailField(max_length=255, unique=True, null=True, blank=True)
    especialidade = models.CharField(max_length=120, blank=True)
    status = models.CharField(
        max_length=20,
        choices=StatusPaciente.choices,
        default=StatusPaciente.ATIVO,
        db_index=True,
    )
    data_cadastro = models.DateTimeField(auto_now_add=True, db_index=True)

    # --- Arquivamento (soft delete) -----------------------------------------
    # Prontuário odontológico tem prazo legal de guarda e é dado sensível de
    # saúde sob a LGPD. Um clique na listagem não pode destruir histórico
    # clínico: o registro é arquivado, com autoria e data.
    arquivado_em = models.DateTimeField(null=True, blank=True, db_index=True)
    arquivado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='pacientes_arquivados',
    )

    objects = PacienteQuerySet.as_manager()

    class Meta:
        ordering = ['-data_cadastro']
        indexes = [
            models.Index(fields=['arquivado_em', '-data_cadastro'], name='clinic_paci_arq_cad_idx'),
        ]
        verbose_name = 'paciente'
        verbose_name_plural = 'pacientes'

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        # Normaliza string vazia para NULL: com unique=True, dois pacientes sem
        # e-mail gravados como '' colidiriam.
        if not self.email:
            self.email = None
        super().save(*args, **kwargs)

    @property
    def arquivado(self):
        return self.arquivado_em is not None

    @property
    def idade(self):
        if not self.data_nascimento:
            return ''
        hoje = date.today()
        nasc = self.data_nascimento
        return hoje.year - nasc.year - ((hoje.month, hoje.day) < (nasc.month, nasc.day))


class ConsultaQuerySet(models.QuerySet):
    def ativas(self):
        return self.exclude(status=StatusConsulta.CANCELADA)

    def do_dia(self, dia):
        return self.filter(data_consulta__date=dia)


class Consulta(models.Model):
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.PROTECT,
        related_name='consultas',
    )
    dentista = models.ForeignKey(
        Dentista,
        on_delete=models.PROTECT,
        related_name='consultas',
    )
    data_consulta = models.DateTimeField(db_index=True)
    duracao_min = models.PositiveIntegerField('duração (min)', default=30)
    procedimento = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20,
        choices=StatusConsulta.choices,
        default=StatusConsulta.AGENDADA,
        db_index=True,
    )
    observacoes = models.TextField(blank=True)

    objects = ConsultaQuerySet.as_manager()

    class Meta:
        ordering = ['-data_consulta']
        indexes = [
            models.Index(fields=['data_consulta', 'status'], name='clinic_cons_data_stat_idx'),
            models.Index(fields=['dentista', 'data_consulta'], name='clinic_cons_dent_data_idx'),
        ]
        constraints = [
            # Rede de proteção no banco contra colisão exata de horário. A
            # sobreposição parcial é validada em clean(), que enxerga a duração.
            models.UniqueConstraint(
                fields=['dentista', 'data_consulta'],
                condition=~models.Q(status='CANCELADA'),
                name='consulta_horario_unico_por_dentista',
            ),
        ]
        verbose_name = 'consulta'
        verbose_name_plural = 'consultas'

    def __str__(self):
        return f'{self.paciente.nome} - {self.data_consulta:%d/%m/%Y %H:%M}'

    @property
    def fim(self):
        return self.data_consulta + timedelta(minutes=self.duracao_min or 0)

    def conflitos(self):
        """Consultas da mesma dentista que se sobrepõem a esta."""
        if not self.data_consulta or not self.dentista_id:
            return Consulta.objects.none()
        qs = (
            Consulta.objects
            .filter(dentista_id=self.dentista_id)
            .exclude(status=StatusConsulta.CANCELADA)
            .filter(data_consulta__lt=self.fim)
        )
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        # Sobreposição: o outro atendimento termina depois do início deste.
        return [c for c in qs if c.fim > self.data_consulta]

    def clean(self):
        super().clean()
        if self.status == StatusConsulta.CANCELADA:
            return
        conflitos = self.conflitos()
        if conflitos:
            outra = conflitos[0]
            raise ValidationError({
                'data_consulta': (
                    f'{self.dentista} já tem atendimento das '
                    f'{outra.data_consulta:%H:%M} às {outra.fim:%H:%M} nesse dia.'
                )
            })


class Prontuario(models.Model):
    # PROTECT e não CASCADE: o histórico clínico não pode ser destruído como
    # efeito colateral da remoção do cadastro do paciente.
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.PROTECT,
        related_name='prontuarios',
    )
    dentista = models.ForeignKey(
        Dentista,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='prontuarios',
    )
    data_registro = models.DateTimeField(auto_now_add=True, db_index=True)
    procedimento = models.CharField(max_length=255, blank=True)
    observacoes = models.TextField(blank=True)

    class Meta:
        ordering = ['-data_registro']
        indexes = [
            models.Index(fields=['paciente', '-data_registro'], name='clinic_pron_pac_data_idx'),
        ]
        verbose_name = 'prontuário'
        verbose_name_plural = 'prontuários'

    def __str__(self):
        return f'Prontuário de {self.paciente.nome} - {self.data_registro:%d/%m/%Y}'


class PerfilSeguranca(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='perfil_seguranca',
    )
    deve_trocar_senha = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'perfil de segurança'
        verbose_name_plural = 'perfis de segurança'

    def __str__(self):
        return f'Segurança de {self.usuario}'


class TentativaLoginQuerySet(models.QuerySet):
    def falhas_recentes(self, ip, username, minutos):
        desde = timezone.now() - timedelta(minutes=minutos)
        return self.filter(
            ip=ip,
            username=username,
            sucesso=False,
            criado_em__gte=desde,
        )


class TentativaLogin(models.Model):
    """Registro de cada tentativa de autenticação.

    Serve a dois propósitos: alimentar o bloqueio por (IP, usuário) — que
    funciona mesmo com vários workers do gunicorn, ao contrário de um contador
    em memória — e manter a trilha de acessos exigida para dado sensível.
    """

    username = models.CharField(max_length=254, db_index=True)
    ip = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    sucesso = models.BooleanField(default=False)
    user_agent = models.CharField(max_length=255, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = TentativaLoginQuerySet.as_manager()

    class Meta:
        ordering = ['-criado_em']
        indexes = [
            models.Index(fields=['ip', 'username', '-criado_em'], name='clinic_tent_ip_user_idx'),
        ]
        verbose_name = 'tentativa de login'
        verbose_name_plural = 'tentativas de login'

    def __str__(self):
        resultado = 'sucesso' if self.sucesso else 'falha'
        return f'{self.username} ({self.ip}) - {resultado}'


class AcaoAuditoria(models.TextChoices):
    VISUALIZAR = 'VISUALIZAR', 'Visualizou'
    CRIAR = 'CRIAR', 'Criou'
    ALTERAR = 'ALTERAR', 'Alterou'
    ARQUIVAR = 'ARQUIVAR', 'Arquivou'
    EXPORTAR = 'EXPORTAR', 'Exportou'


class EventoAuditoria(models.Model):
    """Trilha append-only de acesso a dado clínico.

    Sem isto é impossível responder quem visualizou, alterou ou arquivou um
    prontuário — informação exigida para prestação de contas sobre tratamento
    de dado pessoal sensível de saúde.
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='eventos_auditoria',
    )
    acao = models.CharField(max_length=20, choices=AcaoAuditoria.choices, db_index=True)
    objeto_tipo = models.CharField(max_length=60, db_index=True)
    objeto_id = models.CharField(max_length=40, blank=True)
    descricao = models.CharField(max_length=255, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-criado_em']
        indexes = [
            models.Index(fields=['objeto_tipo', 'objeto_id', '-criado_em'], name='clinic_even_obj_idx'),
        ]
        verbose_name = 'evento de auditoria'
        verbose_name_plural = 'eventos de auditoria'

    def __str__(self):
        return f'{self.criado_em:%d/%m/%Y %H:%M} {self.usuario} {self.acao} {self.objeto_tipo}'

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError('Evento de auditoria é imutável e não pode ser alterado.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('Evento de auditoria não pode ser removido.')
