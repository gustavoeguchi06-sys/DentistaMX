import csv
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import (
    ConsultaForm,
    EstoqueItemForm,
    PacienteForm,
    PermissaoForm,
    ProntuarioForm,
    RelatorioForm,
    TransacaoFinanceiraForm,
    UsuarioForm,
)
from .models import (
    Consulta,
    EstoqueItem,
    Paciente,
    Prontuario,
    Relatorio,
    TransacaoFinanceira,
    Usuario,
)
from django.test import Client
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import get_user_model, login as auth_login, logout as auth_logout


def ensure_demo_user():
    User = get_user_model()
    demo, created = User.objects.get_or_create(
        username='demo',
        defaults={'email': 'demo@example.com', 'is_staff': True},
    )
    if created or not demo.check_password('demo123'):
        demo.set_password('demo123')
        demo.save()
    return demo


def dashboard(request):
    if request.user.is_authenticated:
        today = timezone.localdate()
        pacientes_count = Paciente.objects.count()
        agenda_today = Consulta.objects.filter(
            data_consulta__date=today
        ).select_related('paciente').order_by('data_consulta')[:5]
        agenda_count = Consulta.objects.filter(data_consulta__date=today).count()
        recent_pacientes = Paciente.objects.order_by('-data_cadastro')[:5]
        prontuarios_count = Prontuario.objects.count()
        relatorios_count = Relatorio.objects.count()
        financeiro_mensal = TransacaoFinanceira.objects.filter(
            data_operacao__year=today.year,
            data_operacao__month=today.month,
        )
        receitas = sum(t.valor for t in financeiro_mensal if t.tipo == 'Receita')
        despesas = sum(t.valor for t in financeiro_mensal if t.tipo == 'Despesa')
        saldo = receitas - despesas

        daily_summary = {}
        for transacao in financeiro_mensal:
            dia = transacao.data_operacao.day
            if dia not in daily_summary:
                daily_summary[dia] = {
                    'label': transacao.data_operacao.strftime('%d/%m'),
                    'receitas': 0.0,
                    'despesas': 0.0,
                }
            if transacao.tipo == 'Receita':
                daily_summary[dia]['receitas'] += float(transacao.valor)
            else:
                daily_summary[dia]['despesas'] += float(transacao.valor)

        chart_labels = []
        chart_receitas = []
        chart_despesas = []
        for dia in sorted(daily_summary):
            chart_labels.append(daily_summary[dia]['label'])
            chart_receitas.append(daily_summary[dia]['receitas'])
            chart_despesas.append(daily_summary[dia]['despesas'])

        low_stock_items = EstoqueItem.objects.filter(
            nivel_alerta__in=['Baixo', 'Crítico']
        ).order_by('nivel_alerta', 'nome')[:4]
        stock_alert_count = EstoqueItem.objects.filter(
            nivel_alerta__in=['Baixo', 'Crítico']
        ).count()
        return render(request, 'dashboard/dashboard.html', {
            'pacientes_count': pacientes_count,
            'agenda_today': agenda_today,
            'agenda_count': agenda_count,
            'recent_pacientes': recent_pacientes,
            'prontuarios_count': prontuarios_count,
            'relatorios_count': relatorios_count,
            'receitas': receitas,
            'despesas': despesas,
            'saldo': saldo,
            'chart_labels': chart_labels,
            'chart_receitas': chart_receitas,
            'chart_despesas': chart_despesas,
            'low_stock_items': low_stock_items,
            'stock_alert_count': stock_alert_count,
        })

    next_url = request.POST.get('next') or request.GET.get('next') or None
    if next_url in ('', 'None'):
        next_url = None
    form_type = request.POST.get('form_type') if request.method == 'POST' else None
    ensure_demo_user()
    login_form = AuthenticationForm(request, data=request.POST if form_type == 'login' else None, prefix='login')
    register_form = UserCreationForm(request.POST if form_type == 'register' else None, prefix='register')

    if request.method == 'POST':
        if form_type == 'login' and login_form.is_valid():
            auth_login(request, login_form.get_user())
            return redirect(next_url or 'pacientes')
        if form_type == 'register' and register_form.is_valid():
            user = register_form.save()
            auth_login(request, user)
            return redirect(next_url or 'pacientes')

    return render(request, 'dashboard/dashboard.html', {
        'login_form': login_form,
        'register_form': register_form,
        'demo_user': 'demo',
        'demo_password': 'demo123',
        'next': next_url,
    })


def logout_view(request):
    auth_logout(request)
    return redirect('dashboard')


@login_required
def pacientes(request):
    pacientes = Paciente.objects.all().order_by('-data_cadastro')
    return render(request, 'pacientes/list.html', {'pacientes': pacientes})


@login_required
def paciente_add(request):
    if request.method == 'POST':
        form = PacienteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('pacientes')
    else:
        form = PacienteForm()

    return render(request, 'pacientes/form.html', {'form': form, 'cancel_url': reverse('pacientes')})


@login_required
def pacientes_export(request):
    pacientes = Paciente.objects.all().order_by('nome')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="pacientes.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Nome',
        'Data Nascimento',
        'Telefone',
        'Email',
        'Especialidade',
        'Status',
        'Data Cadastro',
    ])
    for paciente in pacientes:
        writer.writerow([
            paciente.nome,
            paciente.data_nascimento.strftime('%Y-%m-%d') if paciente.data_nascimento else '',
            paciente.telefone,
            paciente.email,
            paciente.especialidade,
            paciente.status,
            paciente.data_cadastro.strftime('%Y-%m-%d %H:%M'),
        ])
    return response


@login_required
def agenda(request):
    consultas = Consulta.objects.select_related('paciente').order_by('data_consulta')
    return render(request, 'agenda/list.html', {'consultas': consultas})


@login_required
def agenda_add(request):
    if request.method == 'POST':
        form = ConsultaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('agenda')
    else:
        form = ConsultaForm()
    return render(request, 'agenda/form.html', {'form': form, 'cancel_url': reverse('agenda')})


@login_required
def prontuarios(request):
    prontuarios = Prontuario.objects.select_related('paciente').order_by('-data_registro')
    return render(request, 'prontuarios/list.html', {'prontuarios': prontuarios})


@login_required
def prontuario_add(request):
    if request.method == 'POST':
        form = ProntuarioForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('prontuarios')
    else:
        form = ProntuarioForm()
    return render(request, 'prontuarios/form.html', {'form': form, 'cancel_url': reverse('prontuarios')})


@login_required
def estoque(request):
    itens = EstoqueItem.objects.all().order_by('nome')
    return render(request, 'estoque/list.html', {'itens': itens})


@login_required
def estoque_add(request):
    if request.method == 'POST':
        form = EstoqueItemForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('estoque')
    else:
        form = EstoqueItemForm()
    return render(request, 'estoque/form.html', {'form': form, 'cancel_url': reverse('estoque')})


@login_required
def estoque_relatorio(request):
    itens = EstoqueItem.objects.filter(nivel_alerta__in=['Baixo', 'Crítico']).order_by('nivel_alerta', 'nome')
    return render(request, 'estoque/report.html', {'itens': itens})


@login_required
def financeiro(request):
    transacoes = TransacaoFinanceira.objects.all().order_by('-data_operacao')
    now = timezone.localtime(timezone.now())
    mensal = TransacaoFinanceira.objects.filter(
        data_operacao__year=now.year,
        data_operacao__month=now.month,
    )
    receitas = sum(t.valor for t in mensal if t.tipo == 'Receita')
    despesas = sum(t.valor for t in mensal if t.tipo == 'Despesa')
    saldo = receitas - despesas
    return render(request, 'financeiro/list.html', {
        'transacoes': transacoes,
        'receitas': receitas,
        'despesas': despesas,
        'saldo': saldo,
    })


@login_required
def financeiro_add(request):
    if request.method == 'POST':
        form = TransacaoFinanceiraForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('financeiro')
    else:
        form = TransacaoFinanceiraForm()
    return render(request, 'financeiro/form.html', {'form': form, 'cancel_url': reverse('financeiro')})


@login_required
def financeiro_relatorio(request):
    now = timezone.localtime(timezone.now())
    mensal = TransacaoFinanceira.objects.filter(
        data_operacao__year=now.year,
        data_operacao__month=now.month,
    )
    receitas = sum(t.valor for t in mensal if t.tipo == 'Receita')
    despesas = sum(t.valor for t in mensal if t.tipo == 'Despesa')
    return render(request, 'financeiro/report.html', {
        'mensal': mensal,
        'receitas': receitas,
        'despesas': despesas,
        'saldo': receitas - despesas,
        'periodo': now.strftime('%B/%Y'),
    })


@login_required
def relatorios(request):
    relatorios = Relatorio.objects.all().order_by('-data_geracao')
    return render(request, 'relatorios/list.html', {'relatorios': relatorios})


@login_required
def relatorio_add(request):
    if request.method == 'POST':
        form = RelatorioForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('relatorios')
    else:
        form = RelatorioForm()
    return render(request, 'relatorios/form.html', {'form': form, 'cancel_url': reverse('relatorios')})


@login_required
def administracao(request):
    usuarios = Usuario.objects.all().order_by('nome')
    return render(request, 'administracao/list.html', {'usuarios': usuarios})


@login_required
def administracao_add(request):
    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('administracao')
    else:
        form = UsuarioForm()
    return render(request, 'administracao/form.html', {'form': form, 'cancel_url': reverse('administracao')})


@login_required
def administracao_permissoes(request):
    if request.method == 'POST':
        form = PermissaoForm(request.POST)
        if form.is_valid():
            usuario = form.cleaned_data['usuario']
            usuario.permissoes = form.cleaned_data['permissoes']
            usuario.save()
            return redirect('administracao')
    else:
        form = PermissaoForm()
    return render(request, 'administracao/permissions.html', {'form': form, 'cancel_url': reverse('administracao')})


@login_required
def paciente_delete(request, pk):
    try:
        paciente = Paciente.objects.get(pk=pk)
        paciente.delete()
    except Paciente.DoesNotExist:
        pass
    return redirect('pacientes')


@login_required
def consulta_delete(request, pk):
    try:
        consulta = Consulta.objects.get(pk=pk)
        consulta.delete()
    except Consulta.DoesNotExist:
        pass
    return redirect('agenda')


@login_required
def prontuario_delete(request, pk):
    try:
        prontuario = Prontuario.objects.get(pk=pk)
        prontuario.delete()
    except Prontuario.DoesNotExist:
        pass
    return redirect('prontuarios')


def check_pages(request):
    client = Client()
    User = get_user_model()
    demo, created = User.objects.get_or_create(
        username='demo',
        defaults={'email': 'demo@example.com', 'is_staff': True}
    )
    if created:
        demo.set_password('demo123')
        demo.save()
    client.login(username='demo', password='demo123')

    paths = [
        '/',
        '/pacientes/',
        '/agenda/',
        '/prontuarios/',
        '/estoque/',
        '/financeiro/',
        '/relatorios/',
        '/administracao/',
    ]
    results = []
    for p in paths:
        try:
            resp = client.get(p)
            content = resp.content.decode('utf-8', errors='ignore')[:1000]
            # try to extract <title>
            import re
            m = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE|re.DOTALL)
            title = m.group(1).strip() if m else ''
            results.append({'path': p, 'status': resp.status_code, 'title': title})
        except Exception as e:
            results.append({'path': p, 'status': 'ERROR', 'title': str(e)})
    return render(request, 'dashboard/check_pages.html', {'results': results})


def register(request):
    """Simple user registration using Django's built-in UserCreationForm.
    After successful registration the user is logged in and redirected to dashboard.
    """
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})
