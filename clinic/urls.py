from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('senha/trocar/', views.trocar_senha, name='trocar_senha'),

    path(
        'senha/recuperar/',
        auth_views.PasswordResetView.as_view(
            template_name='accounts/password_reset_form.html',
            email_template_name='accounts/password_reset_email.txt',
            subject_template_name='accounts/password_reset_subject.txt',
            success_url=reverse_lazy('password_reset_done'),
        ),
        name='password_reset',
    ),
    path(
        'senha/recuperar/enviado/',
        auth_views.PasswordResetDoneView.as_view(template_name='accounts/password_reset_done.html'),
        name='password_reset_done',
    ),
    path(
        'senha/redefinir/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='accounts/password_reset_confirm.html',
            success_url=reverse_lazy('password_reset_complete'),
        ),
        name='password_reset_confirm',
    ),
    path(
        'senha/redefinir/concluido/',
        auth_views.PasswordResetCompleteView.as_view(template_name='accounts/password_reset_complete.html'),
        name='password_reset_complete',
    ),

    path('portal/', views.portal_paciente, name='portal_paciente'),

    path('pacientes/', views.pacientes, name='pacientes'),
    path('pacientes/adicionar/', views.paciente_add, name='paciente_add'),
    path('pacientes/exportar/', views.pacientes_export, name='pacientes_export'),
    path('pacientes/<int:pk>/', views.paciente_detail, name='paciente_detail'),
    # Arquiva em vez de excluir: prontuário tem prazo legal de guarda.
    path('pacientes/<int:pk>/arquivar/', views.paciente_arquivar, name='paciente_arquivar'),

    path('agenda/', views.agenda, name='agenda'),
    path('agenda/novo/', views.agenda_add, name='agenda_add'),
    # Cancelar preserva o histórico de desmarcações, que é informação clínica.
    path('agenda/<int:pk>/cancelar/', views.consulta_cancelar, name='consulta_cancelar'),

    path('prontuarios/', views.prontuarios, name='prontuarios'),
    path('prontuarios/novo/', views.prontuario_add, name='prontuario_add'),
    # Não existe rota de exclusão de prontuário: registro clínico é imutável.
]
