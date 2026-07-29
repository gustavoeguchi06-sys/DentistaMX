import csv
import logging

from django import forms
from django.contrib import messages
from django.contrib.auth import (
    get_user_model,
    login as auth_login,
    logout as auth_logout,
    update_session_auth_hash,
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from . import services
from .decorators import dentista_required, paciente_required
from .forms import ConsultaForm, PacienteForm, ProntuarioForm
from .models import (
    AcaoAuditoria,
    Consulta,
    Paciente,
    PerfilSeguranca,
    Prontuario,
    StatusConsulta,
)

logger = logging.getLogger('clinic')

User = get_user_model()

TAMANHO_PAGINA = 25

# Mensagem única para qualquer falha de login. Diferenciar "usuário não existe"
# de "senha errada" — ou revelar que uma conta está bloqueada — entrega ao
# atacante a lista de contas válidas do sistema.
ERRO_LOGIN_GENERICO = 'Usuário ou senha inválidos.'


def _redirect_pos_login(user):
    if user.is_staff:
        return redirect('dashboard')
    return redirect('portal_paciente')


def _paginar(request, queryset):
    paginator = Paginator(queryset, TAMANHO_PAGINA)
    return paginator.get_page(request.GET.get('page'))


def login_view(request):
    if request.user.is_authenticated:
        return _redirect_pos_login(request.user)

    next_url = request.POST.get('next') or request.GET.get('next') or ''
    error = None
    username = ''

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        usuario, motivo = services.autenticar(request, username, password)

        if usuario is not None:
            auth_login(request, usuario)
            perfil = getattr(usuario, 'perfil_seguranca', None)
            if perfil and perfil.deve_trocar_senha:
                return redirect('trocar_senha')
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                return redirect(next_url)
            return _redirect_pos_login(usuario)

        if motivo == 'bloqueado':
            minutos = services.minutos_restantes_de_bloqueio(request, username)
            error = (
                'Muitas tentativas a partir deste dispositivo. Tente novamente em '
                f'{minutos} minuto(s) ou use "Esqueci minha senha".'
            )
        else:
            error = ERRO_LOGIN_GENERICO

    return render(request, 'accounts/login.html', {
        'error': error,
        'username': username,
        'next': next_url,
    })


@require_POST
def logout_view(request):
    """Logout exige POST.

    Com GET, qualquer prefetch de navegador ou `<img src="/logout/">` numa
    página de terceiros desconecta a usuária.
    """
    auth_logout(request)
    return redirect('login')


class TrocaSenhaForm(forms.Form):
    nova_senha = forms.CharField(widget=forms.PasswordInput, label='Nova senha')
    confirmar_senha = forms.CharField(widget=forms.PasswordInput, label='Confirme a nova senha')

    def clean(self):
        cleaned = super().clean()
        senha1 = cleaned.get('nova_senha')
        senha2 = cleaned.get('confirmar_senha')
        if senha1 and senha2 and senha1 != senha2:
            raise ValidationError('As senhas não coincidem.')
        return cleaned


@login_required
def trocar_senha(request):
    perfil, _ = PerfilSeguranca.objects.get_or_create(usuario=request.user)
    form = TrocaSenhaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        nova_senha = form.cleaned_data['nova_senha']
        try:
            validate_password(nova_senha, user=request.user)
        except ValidationError as exc:
            for erro in exc.messages:
                form.add_error('nova_senha', erro)
        else:
            request.user.set_password(nova_senha)
            request.user.save()
            perfil.deve_trocar_senha = False
            perfil.save(update_fields=['deve_trocar_senha'])
            update_session_auth_hash(request, request.user)
            logger.info('senha alterada usuario=%s', request.user.get_username())
            messages.success(request, 'Senha atualizada com sucesso.')
            return _redirect_pos_login(request.user)

    return render(request, 'accounts/trocar_senha.html', {
        'form': form,
        'obrigatorio': perfil.deve_trocar_senha,
    })


@dentista_required
def dashboard(request):
    hoje = timezone.localdate()

    agenda_hoje = (
        Consulta.objects.do_dia(hoje)
        .select_related('paciente', 'dentista')
        .order_by('data_consulta')
    )
    proximas_consultas = (
        Consulta.objects
        .filter(data_consulta__date__gt=hoje, status=StatusConsulta.AGENDADA)
        .select_related('paciente', 'dentista')
        .order_by('data_consulta')[:5]
    )

    return render(request, 'dashboard/dashboard.html', {
        'pacientes_count': Paciente.objects.ativos().count(),
        'agenda_today': agenda_hoje[:8],
        'agenda_count': agenda_hoje.count(),
        'proximas_consultas': proximas_consultas,
        'recent_pacientes': Paciente.objects.ativos()[:5],
        'prontuarios_count': Prontuario.objects.count(),
        'concluidas_mes': Consulta.objects.filter(
            status=StatusConsulta.CONCLUIDA,
            data_consulta__year=hoje.year,
            data_consulta__month=hoje.month,
        ).count(),
    })


@dentista_required
def pacientes(request):
    busca = request.GET.get('q', '').strip()
    queryset = Paciente.objects.ativos()
    if busca:
        queryset = queryset.filter(nome__icontains=busca)
    return render(request, 'pacientes/list.html', {
        'pagina': _paginar(request, queryset),
        'busca': busca,
    })


@dentista_required
def paciente_add(request):
    if request.method == 'POST':
        form = PacienteForm(request.POST)
        if form.is_valid():
            paciente = form.save(commit=False)
            try:
                paciente, senha_temp = services.registrar_paciente(paciente, request=request)
            except services.pacientes.EmailJaCadastrado:
                form.add_error('email', 'Já existe uma conta cadastrada com este e-mail.')
            else:
                login_url = request.build_absolute_uri(reverse('login'))
                # Só envia depois que a transação de cadastro confirmar: enviar
                # antes arriscaria mandar credencial de um cadastro que falhou.
                transaction.on_commit(
                    lambda: services.pacientes.enviar_credenciais(paciente, senha_temp, login_url)
                )
                messages.success(
                    request,
                    f'Paciente cadastrado. As credenciais de acesso foram enviadas '
                    f'para {paciente.email}.',
                )
                return redirect('pacientes')
    else:
        form = PacienteForm()

    return render(request, 'pacientes/form.html', {'form': form, 'cancel_url': reverse('pacientes')})


@dentista_required
def paciente_detail(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    services.registrar_evento(
        request, AcaoAuditoria.VISUALIZAR, objeto=paciente,
        descricao=f'Ficha clínica de {paciente.nome} acessada.',
    )
    return render(request, 'pacientes/detail.html', {
        'paciente': paciente,
        'consultas': paciente.consultas.select_related('dentista'),
        'prontuarios': paciente.prontuarios.select_related('dentista'),
    })


@dentista_required
def pacientes_export(request):
    lista = Paciente.objects.ativos().order_by('nome')
    services.registrar_evento(
        request, AcaoAuditoria.EXPORTAR, objeto_tipo='Paciente',
        descricao=f'Exportação CSV de {lista.count()} paciente(s).',
    )

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="pacientes.csv"'
    response.write('﻿')  # BOM: o Excel pt-BR precisa dele para acentuação
    writer = csv.writer(response)
    writer.writerow([
        'Nome', 'Data Nascimento', 'Telefone', 'Email',
        'Especialidade', 'Status', 'Data Cadastro',
    ])
    for paciente in lista:
        writer.writerow([
            paciente.nome,
            paciente.data_nascimento.strftime('%d/%m/%Y') if paciente.data_nascimento else '',
            paciente.telefone,
            paciente.email or '',
            paciente.especialidade,
            paciente.get_status_display(),
            timezone.localtime(paciente.data_cadastro).strftime('%d/%m/%Y %H:%M'),
        ])
    return response


@dentista_required
def agenda(request):
    consultas = Consulta.objects.select_related('paciente', 'dentista').order_by('data_consulta')
    return render(request, 'agenda/list.html', {'pagina': _paginar(request, consultas)})


@dentista_required
def agenda_add(request):
    if request.method == 'POST':
        form = ConsultaForm(request.POST)
        if form.is_valid():
            try:
                services.agendar_consulta(form.instance, request=request)
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(request, 'Consulta agendada.')
                return redirect('agenda')
    else:
        form = ConsultaForm(initial={'paciente': request.GET.get('paciente')})
    return render(request, 'agenda/form.html', {'form': form, 'cancel_url': reverse('agenda')})


@dentista_required
def prontuarios(request):
    registros = Prontuario.objects.select_related('paciente', 'dentista')
    return render(request, 'prontuarios/list.html', {'pagina': _paginar(request, registros)})


@dentista_required
def prontuario_add(request):
    if request.method == 'POST':
        form = ProntuarioForm(request.POST)
        if form.is_valid():
            prontuario = form.save()
            services.registrar_evento(
                request, AcaoAuditoria.CRIAR, objeto=prontuario,
                descricao=f'Prontuário registrado para {prontuario.paciente.nome}.',
            )
            messages.success(request, 'Prontuário registrado.')
            return redirect('prontuarios')
    else:
        form = ProntuarioForm(initial={'paciente': request.GET.get('paciente')})
    return render(request, 'prontuarios/form.html', {'form': form, 'cancel_url': reverse('prontuarios')})


@dentista_required
@require_POST
def paciente_arquivar(request, pk):
    """Arquiva o cadastro. Exige POST com token CSRF.

    Antes esta operação respondia a GET e apagava o paciente junto com todas as
    consultas e prontuários — um `<img src>` numa página qualquer bastava para
    destruir histórico clínico.
    """
    paciente = get_object_or_404(Paciente, pk=pk)
    services.arquivar_paciente(paciente, usuario_responsavel=request.user, request=request)
    messages.success(
        request,
        f'Cadastro de {paciente.nome} arquivado. O histórico clínico foi preservado.',
    )
    return redirect('pacientes')


@dentista_required
@require_POST
def consulta_cancelar(request, pk):
    consulta = get_object_or_404(Consulta, pk=pk)
    services.cancelar_consulta(consulta, request=request)
    messages.success(request, 'Consulta cancelada.')
    return redirect('agenda')


@paciente_required
def portal_paciente(request):
    paciente = request.user.paciente_perfil
    agora = timezone.now()
    return render(request, 'portal/paciente.html', {
        'paciente': paciente,
        'proxima_consulta': (
            paciente.consultas.ativas()
            .filter(data_consulta__gte=agora)
            .select_related('dentista')
            .order_by('data_consulta')
            .first()
        ),
        'ultima_consulta': (
            paciente.consultas.filter(data_consulta__lt=agora)
            .select_related('dentista')
            .first()
        ),
        'ultimo_prontuario': paciente.prontuarios.first(),
    })
