"""Converte os dados já cadastrados para o novo modelo.

Três conversões: o texto livre do campo `dentista` vira registro na tabela
Dentista; os rótulos de status ("Concluída") viram códigos estáveis
("CONCLUIDA"); e e-mails vazios viram NULL, para que o índice único de 0005
não trate dois cadastros sem e-mail como duplicados.
"""

from django.db import migrations

# Mapeamento tolerante: aceita as variações que o texto livre permitiu entrar
# no banco (com e sem acento, maiúsculas e minúsculas).
STATUS_CONSULTA = {
    'agendada': 'AGENDADA',
    'confirmada': 'CONFIRMADA',
    'concluída': 'CONCLUIDA',
    'concluida': 'CONCLUIDA',
    'cancelada': 'CANCELADA',
}

STATUS_PACIENTE = {
    'ativo': 'ATIVO',
    'inativo': 'INATIVO',
}


def converter(apps, schema_editor):
    Consulta = apps.get_model('clinic', 'Consulta')
    Dentista = apps.get_model('clinic', 'Dentista')
    Paciente = apps.get_model('clinic', 'Paciente')

    # 1. Texto livre -> entidade Dentista.
    nomes = (
        Consulta.objects.exclude(dentista='')
        .values_list('dentista', flat=True)
        .distinct()
    )
    por_nome = {}
    for nome in nomes:
        limpo = ' '.join((nome or '').split())
        if not limpo:
            continue
        # Nomes que só diferem por caixa/espaço são a mesma profissional.
        chave = limpo.casefold()
        if chave not in por_nome:
            dentista, _ = Dentista.objects.get_or_create(nome=limpo)
            por_nome[chave] = dentista

    if not por_nome:
        # Base sem consultas ou sem responsável preenchido: ainda assim é
        # preciso uma dentista para as consultas órfãs referenciarem.
        por_nome['__padrao__'] = Dentista.objects.get_or_create(
            nome='Dentista não informada'
        )[0]

    padrao = por_nome.get('__padrao__') or next(iter(por_nome.values()))

    for consulta in Consulta.objects.all().iterator():
        chave = ' '.join((consulta.dentista or '').split()).casefold()
        consulta.dentista_ref = por_nome.get(chave, padrao)
        consulta.status = STATUS_CONSULTA.get(
            (consulta.status or '').strip().casefold(), 'AGENDADA'
        )
        consulta.save(update_fields=['dentista_ref', 'status'])

    # 2. Status do paciente + 3. e-mail vazio -> NULL.
    for paciente in Paciente.objects.all().iterator():
        paciente.status = STATUS_PACIENTE.get(
            (paciente.status or '').strip().casefold(), 'ATIVO'
        )
        if not (paciente.email or '').strip():
            paciente.email = None
        else:
            paciente.email = paciente.email.strip().lower()
        paciente.save(update_fields=['status', 'email'])


def reverter(apps, schema_editor):
    """Reescreve os rótulos antigos para permitir rollback."""
    Consulta = apps.get_model('clinic', 'Consulta')
    Paciente = apps.get_model('clinic', 'Paciente')

    rotulos_consulta = {
        'AGENDADA': 'Agendada',
        'CONFIRMADA': 'Confirmada',
        'CONCLUIDA': 'Concluída',
        'CANCELADA': 'Cancelada',
    }
    for consulta in Consulta.objects.all().iterator():
        consulta.dentista = consulta.dentista_ref.nome if consulta.dentista_ref_id else ''
        consulta.status = rotulos_consulta.get(consulta.status, 'Agendada')
        consulta.save(update_fields=['dentista', 'status'])

    for paciente in Paciente.objects.all().iterator():
        paciente.status = 'Ativo' if paciente.status == 'ATIVO' else 'Inativo'
        if paciente.email is None:
            paciente.email = ''
        paciente.save(update_fields=['status', 'email'])


class Migration(migrations.Migration):

    dependencies = [
        ('clinic', '0003_estrutura_clinica_e_auditoria'),
    ]

    operations = [
        migrations.RunPython(converter, reverter),
    ]
