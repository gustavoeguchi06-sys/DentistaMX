from django.contrib import admin

from .models import (
    Consulta,
    Dentista,
    EventoAuditoria,
    Paciente,
    PerfilSeguranca,
    Prontuario,
    TentativaLogin,
)


@admin.register(Dentista)
class DentistaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cro', 'ativo')
    list_filter = ('ativo',)
    search_fields = ('nome', 'cro')


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'email', 'especialidade', 'status', 'arquivado_em', 'data_cadastro')
    list_filter = ('status', 'arquivado_em')
    search_fields = ('nome', 'email', 'telefone')
    readonly_fields = ('data_cadastro', 'arquivado_em', 'arquivado_por')


@admin.register(Consulta)
class ConsultaAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'data_consulta', 'duracao_min', 'dentista', 'status')
    list_filter = ('status', 'dentista')
    search_fields = ('paciente__nome', 'procedimento')
    autocomplete_fields = ('paciente', 'dentista')
    date_hierarchy = 'data_consulta'


@admin.register(Prontuario)
class ProntuarioAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'data_registro', 'dentista', 'procedimento')
    list_filter = ('dentista',)
    search_fields = ('paciente__nome', 'procedimento')
    autocomplete_fields = ('paciente', 'dentista')
    readonly_fields = ('data_registro',)


@admin.register(PerfilSeguranca)
class PerfilSegurancaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'deve_trocar_senha')
    list_filter = ('deve_trocar_senha',)
    search_fields = ('usuario__username',)


class SomenteLeituraAdmin(admin.ModelAdmin):
    """Trilha de auditoria é append-only, inclusive para quem tem acesso ao admin."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TentativaLogin)
class TentativaLoginAdmin(SomenteLeituraAdmin):
    list_display = ('criado_em', 'username', 'ip', 'sucesso')
    list_filter = ('sucesso', 'criado_em')
    search_fields = ('username', 'ip')
    date_hierarchy = 'criado_em'


@admin.register(EventoAuditoria)
class EventoAuditoriaAdmin(SomenteLeituraAdmin):
    list_display = ('criado_em', 'usuario', 'acao', 'objeto_tipo', 'objeto_id', 'descricao')
    list_filter = ('acao', 'objeto_tipo', 'criado_em')
    search_fields = ('descricao', 'objeto_id', 'usuario__username')
    date_hierarchy = 'criado_em'
