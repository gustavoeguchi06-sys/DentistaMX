"""Adições de esquema: entidade Dentista, arquivamento e trilha de auditoria.

Esta migração é puramente aditiva — nada é removido nem tornado obrigatório
aqui. A conversão dos dados existentes acontece em 0004 e só depois, em 0005,
as colunas antigas saem e as restrições entram. Separar em três etapas é o que
permite migrar sem perder o histórico já cadastrado.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clinic', '0002_perfilseguranca_delete_estoqueitem_delete_relatorio_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Dentista',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=120, unique=True)),
                ('cro', models.CharField(blank=True, max_length=30, verbose_name='CRO')),
                ('ativo', models.BooleanField(default=True)),
                ('usuario', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='dentista_perfil', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'dentista',
                'verbose_name_plural': 'dentistas',
                'ordering': ['nome'],
            },
        ),
        migrations.CreateModel(
            name='TentativaLogin',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(db_index=True, max_length=254)),
                ('ip', models.GenericIPAddressField(blank=True, db_index=True, null=True)),
                ('sucesso', models.BooleanField(default=False)),
                ('user_agent', models.CharField(blank=True, max_length=255)),
                ('criado_em', models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                'verbose_name': 'tentativa de login',
                'verbose_name_plural': 'tentativas de login',
                'ordering': ['-criado_em'],
            },
        ),
        migrations.CreateModel(
            name='EventoAuditoria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('acao', models.CharField(choices=[('VISUALIZAR', 'Visualizou'), ('CRIAR', 'Criou'), ('ALTERAR', 'Alterou'), ('ARQUIVAR', 'Arquivou'), ('EXPORTAR', 'Exportou')], db_index=True, max_length=20)),
                ('objeto_tipo', models.CharField(db_index=True, max_length=60)),
                ('objeto_id', models.CharField(blank=True, max_length=40)),
                ('descricao', models.CharField(blank=True, max_length=255)),
                ('ip', models.GenericIPAddressField(blank=True, null=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('usuario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='eventos_auditoria', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'evento de auditoria',
                'verbose_name_plural': 'eventos de auditoria',
                'ordering': ['-criado_em'],
            },
        ),
        migrations.AddIndex(
            model_name='tentativalogin',
            index=models.Index(fields=['ip', 'username', '-criado_em'], name='clinic_tent_ip_user_idx'),
        ),
        migrations.AddIndex(
            model_name='eventoauditoria',
            index=models.Index(fields=['objeto_tipo', 'objeto_id', '-criado_em'], name='clinic_even_obj_idx'),
        ),

        # --- Arquivamento do paciente (soft delete) --------------------------
        migrations.AddField(
            model_name='paciente',
            name='arquivado_em',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='paciente',
            name='arquivado_por',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pacientes_arquivados', to=settings.AUTH_USER_MODEL),
        ),
        # Aceita NULL já aqui: 0004 precisa gravar NULL nos e-mails vazios antes
        # de 0005 criar o índice único. Sem esta etapa, a conversão esbarraria
        # na restrição NOT NULL que ainda vigora.
        migrations.AlterField(
            model_name='paciente',
            name='email',
            field=models.EmailField(blank=True, max_length=255, null=True),
        ),

        # --- Consulta: duração e vínculo com a dentista ----------------------
        migrations.AddField(
            model_name='consulta',
            name='duracao_min',
            field=models.PositiveIntegerField(default=30, verbose_name='duração (min)'),
        ),
        # Entra como nulo: 0004 preenche a partir do texto da coluna antiga e
        # 0005 torna obrigatório.
        migrations.AddField(
            model_name='consulta',
            name='dentista_ref',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='consultas', to='clinic.dentista'),
        ),
        migrations.AddField(
            model_name='prontuario',
            name='dentista',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='prontuarios', to='clinic.dentista'),
        ),
    ]
