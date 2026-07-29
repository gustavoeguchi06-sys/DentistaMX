# MX Odontologia

Sistema de gestão para clínica odontológica, em Django: cadastro de pacientes,
agenda, prontuários e um portal onde o paciente acompanha os próprios dados.

## Requisitos

- Python 3.12+
- PostgreSQL (produção) — SQLite é aceito apenas em desenvolvimento

## Instalação

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1        # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env              # e preencha os valores
python manage.py migrate
python manage.py criar_dentista   # cria o acesso da profissional
python manage.py runserver
```

Acesse `http://127.0.0.1:8000/`.

## Configuração

Toda configuração vem de variáveis de ambiente — veja `.env.example`. Dois
comportamentos importantes:

- **`DEBUG` é `False` por padrão.** Para desenvolver, defina `DEBUG=True`
  explicitamente. Assim, uma variável que não chega ao processo em produção
  nunca resulta em modo de depuração ligado.
- **`SECRET_KEY` é obrigatória quando `DEBUG=False`.** A aplicação se recusa a
  subir sem ela, em vez de servir requisições com uma chave conhecida (o que
  permitiria forjar sessões e tokens de redefinição de senha).

## Perfis de acesso

| Perfil | Como é criado | Acesso |
|---|---|---|
| Dentista | `python manage.py criar_dentista` | Dashboard, pacientes, agenda, prontuários |
| Paciente | Automaticamente ao cadastrar o paciente | Apenas o portal com os próprios dados |

O paciente recebe uma senha temporária por e-mail e é obrigado a trocá-la no
primeiro acesso.

## Decisões de projeto que não devem ser revertidas

Estas escolhas parecem restritivas até se entender o motivo:

- **Paciente é arquivado, nunca excluído.** Prontuário odontológico tem prazo
  legal de guarda e é dado pessoal sensível de saúde. As FKs usam `PROTECT`
  para que remover um cadastro não destrua histórico clínico por cascata.
- **Prontuário não tem rota de exclusão.** Correções entram como um novo
  registro descrevendo a correção.
- **Consulta é cancelada, não apagada.** O histórico de desmarcações é
  informação clínica.
- **Toda ação destrutiva exige POST com token CSRF.** Com GET, um `<img src>`
  numa página qualquer — ou o prefetch do navegador — bastaria para disparar a
  ação sem nenhum clique.
- **O bloqueio de login conta por (IP, usuário).** Contar apenas por conta
  permitiria manter a dentista permanentemente fora do sistema errando a senha
  de propósito.
- **Acesso a dado clínico é auditado** em `EventoAuditoria`, que é append-only.

## Comandos úteis

```bash
python manage.py test                      # suíte completa
python manage.py auditar_staff             # lista contas administrativas suspeitas
python manage.py auditar_staff --strict    # falha se houver conta inesperada (CI/deploy)
python manage.py check --deploy            # checagem de segurança de produção
python manage.py seed_demo                 # dados de exemplo (só com DEBUG=True)
```

## Estrutura

```
mxodontologia/     configurações do projeto
clinic/
  models.py        entidades e regras de integridade
  services/        casos de uso, transações e auditoria
  views.py         camada HTTP (fina — a regra vive em services/)
  forms.py         validação de entrada
  tests/           testes de regressão das falhas já corrigidas
templates/         HTML
static/            CSS e JS
```

## Deploy

Configurado para Render (`render.yaml`). O `SECRET_KEY` é gerado pelo próprio
Render (`generateValue: true`) e nunca fica no repositório; credenciais de
e-mail e `ALLOWED_HOSTS` são preenchidos no painel (`sync: false`).

Antes de publicar, confirme:

```bash
python manage.py check --deploy    # precisa terminar sem nenhum aviso
python manage.py auditar_staff     # nenhuma conta administrativa inesperada
```
