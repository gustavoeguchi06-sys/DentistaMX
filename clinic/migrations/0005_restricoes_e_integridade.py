"""Aplica as restrições depois que os dados já estão convertidos.

Só agora é seguro: tornar o e-mail único, exigir a dentista na consulta, trocar
CASCADE por PROTECT (para que remover um paciente nunca destrua prontuário) e
impedir dois atendimentos no mesmo horário para a mesma profissional.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clinic', '0004_converter_dados_existentes'),
    ]

    operations = [
        # --- Paciente --------------------------------------------------------
        migrations.AlterField(
            model_name='paciente',
            name='nome',
            field=models.CharField(db_index=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='paciente',
            name='email',
            field=models.EmailField(blank=True, max_length=255, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='paciente',
            name='status',
            field=models.CharField(choices=[('ATIVO', 'Ativo'), ('INATIVO', 'Inativo')], db_index=True, default='ATIVO', max_length=20),
        ),
        migrations.AlterField(
            model_name='paciente',
            name='data_cadastro',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AlterModelOptions(
            name='paciente',
            options={'ordering': ['-data_cadastro'], 'verbose_name': 'paciente', 'verbose_name_plural': 'pacientes'},
        ),
        migrations.AddIndex(
            model_name='paciente',
            index=models.Index(fields=['arquivado_em', '-data_cadastro'], name='clinic_paci_arq_cad_idx'),
        ),

        # --- Consulta: remove o texto livre e promove a FK -------------------
        migrations.RemoveField(
            model_name='consulta',
            name='dentista',
        ),
        migrations.RenameField(
            model_name='consulta',
            old_name='dentista_ref',
            new_name='dentista',
        ),
        migrations.AlterField(
            model_name='consulta',
            name='dentista',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='consultas', to='clinic.dentista'),
        ),
        migrations.AlterField(
            model_name='consulta',
            name='paciente',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='consultas', to='clinic.paciente'),
        ),
        migrations.AlterField(
            model_name='consulta',
            name='data_consulta',
            field=models.DateTimeField(db_index=True),
        ),
        migrations.AlterField(
            model_name='consulta',
            name='status',
            field=models.CharField(choices=[('AGENDADA', 'Agendada'), ('CONFIRMADA', 'Confirmada'), ('CONCLUIDA', 'Concluída'), ('CANCELADA', 'Cancelada')], db_index=True, default='AGENDADA', max_length=20),
        ),
        migrations.AlterModelOptions(
            name='consulta',
            options={'ordering': ['-data_consulta'], 'verbose_name': 'consulta', 'verbose_name_plural': 'consultas'},
        ),
        migrations.AddIndex(
            model_name='consulta',
            index=models.Index(fields=['data_consulta', 'status'], name='clinic_cons_data_stat_idx'),
        ),
        migrations.AddIndex(
            model_name='consulta',
            index=models.Index(fields=['dentista', 'data_consulta'], name='clinic_cons_dent_data_idx'),
        ),
        migrations.AddConstraint(
            model_name='consulta',
            constraint=models.UniqueConstraint(
                condition=models.Q(('status', 'CANCELADA'), _negated=True),
                fields=('dentista', 'data_consulta'),
                name='consulta_horario_unico_por_dentista',
            ),
        ),

        # --- Prontuário: PROTECT para o histórico clínico não ser destruído --
        migrations.AlterField(
            model_name='prontuario',
            name='paciente',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='prontuarios', to='clinic.paciente'),
        ),
        migrations.AlterField(
            model_name='prontuario',
            name='data_registro',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AlterModelOptions(
            name='prontuario',
            options={'ordering': ['-data_registro'], 'verbose_name': 'prontuário', 'verbose_name_plural': 'prontuários'},
        ),
        migrations.AddIndex(
            model_name='prontuario',
            index=models.Index(fields=['paciente', '-data_registro'], name='clinic_pron_pac_data_idx'),
        ),

        # --- PerfilSeguranca: o bloqueio agora vem de TentativaLogin ---------
        migrations.RemoveField(
            model_name='perfilseguranca',
            name='tentativas_falhas',
        ),
        migrations.RemoveField(
            model_name='perfilseguranca',
            name='bloqueado_ate',
        ),
        migrations.AlterModelOptions(
            name='perfilseguranca',
            options={'verbose_name': 'perfil de segurança', 'verbose_name_plural': 'perfis de segurança'},
        ),
    ]
