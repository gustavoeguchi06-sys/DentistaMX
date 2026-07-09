from django.contrib import admin
from .models import (
    Paciente,
    Consulta,
    Prontuario,
    EstoqueItem,
    TransacaoFinanceira,
    Relatorio,
    Usuario,
)


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'especialidade', 'status', 'data_cadastro')
    search_fields = ('nome', 'email', 'telefone')


@admin.register(Consulta)
class ConsultaAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'data_consulta', 'dentista', 'status')
    list_filter = ('status', 'dentista')
    search_fields = ('paciente__nome', 'procedimento')


@admin.register(Prontuario)
class ProntuarioAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'data_registro', 'procedimento')
    search_fields = ('paciente__nome', 'procedimento')


@admin.register(EstoqueItem)
class EstoqueItemAdmin(admin.ModelAdmin):
    list_display = ('nome', 'quantidade', 'unidade', 'nivel_alerta')
    list_filter = ('nivel_alerta',)
    search_fields = ('nome',)


@admin.register(TransacaoFinanceira)
class TransacaoFinanceiraAdmin(admin.ModelAdmin):
    list_display = ('data_operacao', 'descricao', 'tipo', 'valor')
    list_filter = ('tipo', 'categoria')
    search_fields = ('descricao',)


@admin.register(Relatorio)
class RelatorioAdmin(admin.ModelAdmin):
    list_display = ('nome', 'periodo', 'status', 'data_geracao')
    list_filter = ('status',)


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('nome', 'email', 'funcao', 'status', 'ultimo_login')
    search_fields = ('nome', 'email')
