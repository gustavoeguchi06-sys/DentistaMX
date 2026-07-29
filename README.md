<div align="center">

# MX Odontologia

**Sistema de gestão clínica para consultórios odontológicos**

Prontuário eletrônico, agenda e portal do paciente — construído com as garantias
de integridade que registro de saúde exige.

[![CI](https://github.com/gustavoeguchi06-sys/DentistaMX/actions/workflows/ci.yml/badge.svg)](https://github.com/gustavoeguchi06-sys/DentistaMX/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-6.0-092E20?logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![Testes](https://img.shields.io/badge/testes-36%20passando-2ea44f)
![Licença](https://img.shields.io/badge/licen%C3%A7a-propriet%C3%A1ria-lightgrey)

</div>

---

## Sobre o projeto

MX Odontologia é uma aplicação web que centraliza a operação de uma clínica
odontológica: cadastro de pacientes, agendamento de consultas, registro de
prontuários e um portal onde o próprio paciente acompanha seus atendimentos.

O sistema é desenhado em torno de uma premissa: **prontuário odontológico é
registro legal, não um dado descartável**. Isso muda decisões de arquitetura que
normalmente seriam triviais — não existe botão de excluir prontuário, cadastros
são arquivados em vez de removidos, e todo acesso a dado clínico deixa rastro.

## Problema que resolve

Clínicas de pequeno porte costumam operar com agenda em papel, planilhas soltas
e prontuários em arquivos de texto. Isso cria quatro problemas concretos:

| Problema | Como o sistema resolve |
|---|---|
| **Histórico clínico se perde** ao trocar de computador, apagar arquivo ou por engano do operador | Prontuário é imutável e protegido no banco por `on_delete=PROTECT`; não há rota de exclusão |
| **Agendamento duplicado** — dois pacientes marcados no mesmo horário | Validação de sobreposição no domínio, considerando a duração real do procedimento, mais restrição no banco |
| **Nenhum rastro de quem acessou o quê** — exigência de prestação de contas sobre dado sensível de saúde | Trilha de auditoria append-only registrando visualização, criação, alteração, arquivamento e exportação |
| **Paciente liga para a clínica só para saber o horário da consulta** | Portal de autoatendimento onde ele vê a próxima consulta e o último atendimento |

## Funcionalidades

**Gestão clínica**
- Cadastro de pacientes com busca por nome e paginação
- Agenda com detecção de conflito de horário e duração configurável por consulta
- Prontuários vinculados a paciente e profissional responsável
- Exportação de pacientes para CSV compatível com Excel em português

**Portal do paciente**
- Acesso próprio, criado automaticamente no cadastro
- Visualização da próxima consulta, do último atendimento e do último prontuário
- Isolamento por construção: o portal parte da conta autenticada e navega por
  relacionamentos, nunca por um ID vindo da URL

**Segurança e conformidade**
- Dois perfis de acesso com autorização verificada em todas as rotas sensíveis
- Bloqueio de tentativas de login contado por *(IP, usuário)*
- Senha temporária com troca obrigatória no primeiro acesso
- Trilha de auditoria imutável sobre acesso a dado clínico
- Arquivamento com autoria e data, preservando o histórico

## Tecnologias

| Camada | Tecnologia | Por quê |
|---|---|---|
| Backend | **Django 6.0** | ORM maduro, admin pronto e proteções de segurança embutidas (CSRF, XSS, SQL injection) |
| Banco | **PostgreSQL 16** | Restrições de integridade e índices parciais; SQLite apenas em desenvolvimento |
| Frontend | **Templates Django + CSS** | Renderização no servidor: menos superfície de ataque e nada de build de JS para manter |
| Assets | **WhiteNoise** | Serve estáticos com hash e compressão sem exigir CDN ou Nginx |
| Servidor | **Gunicorn** | Padrão WSGI para produção |
| Config | **python-dotenv** | Configuração por variável de ambiente, seguindo 12-Factor |
| Qualidade | **Ruff + GitHub Actions** | Lint e testes bloqueando merge |

Sem dependência de framework JavaScript: os ícones são SVG inline e a única
biblioteca cliente é um script de ~130 linhas para o menu responsivo.

## Arquitetura do sistema

O sistema é um **monolito Django em quatro camadas**. Para uma clínica, o
monolito é a escolha certa — microsserviços aqui seriam complexidade sem
contrapartida. A separação que importa é interna:

```
┌─────────────────────────────────────────────────────────────┐
│  Apresentação        templates/ + views.py                  │
│                      Só HTTP: lê request, monta contexto,   │
│                      escolhe template, redireciona.         │
├─────────────────────────────────────────────────────────────┤
│  Aplicação           clinic/services/                       │
│                      Casos de uso e transações.             │
│                      registrar_paciente, agendar_consulta,  │
│                      arquivar_paciente, registrar_evento    │
├─────────────────────────────────────────────────────────────┤
│  Domínio             clinic/models.py                       │
│                      Invariantes: choices, constraints,     │
│                      conflito de horário, imutabilidade.    │
├─────────────────────────────────────────────────────────────┤
│  Persistência        Managers e QuerySets nomeados          │
│                      Paciente.objects.ativos()              │
│                      Consulta.objects.do_dia(hoje)          │
└─────────────────────────────────────────────────────────────┘
```

**Por que a camada de aplicação existe.** Cadastrar um paciente cria uma conta
de usuário, um perfil de segurança e o próprio paciente, e depois dispara um
e-mail. Se isso vive dentro da view, uma falha no meio deixa conta órfã e um
e-mail bloqueado para sempre. Em `services/`, a operação é atômica e o e-mail
só sai via `transaction.on_commit`, depois que o banco confirmou.

**Onde as regras moram.** Validação de formulário protege a digitação; ela não
protege o admin do Django, um comando de importação ou código futuro. Por isso
as invariantes ficam no model e no banco:

```python
class Consulta(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['dentista', 'data_consulta'],
                condition=~models.Q(status='CANCELADA'),
                name='consulta_horario_unico_por_dentista',
            ),
        ]
```

### Modelo de dados

```
Dentista ──┬──< Consulta >──── Paciente ──── User (auth)
           └──< Prontuario >───┘                 │
                                                 │
PerfilSeguranca ─────────────────────────────────┤
EventoAuditoria ─────────────────────────────────┤   trilha append-only
TentativaLogin  ─────────────────────────────────┘   bloqueio + auditoria
```

`Consulta` e `Prontuario` apontam para `Paciente` com `PROTECT`: remover um
cadastro não destrói histórico clínico por cascata — o banco recusa a operação.

## Estrutura de pastas

```
.
├── .github/workflows/ci.yml      Lint, testes, check --deploy, migrações
├── clinic/                       Aplicação principal
│   ├── models.py                 Entidades, choices e invariantes
│   ├── views.py                  Camada HTTP (fina)
│   ├── forms.py                  Validação de entrada
│   ├── urls.py                   Rotas
│   ├── decorators.py             dentista_required, paciente_required
│   ├── admin.py                  Admin, com auditoria em somente-leitura
│   ├── services/                 ── Camada de aplicação ──
│   │   ├── pacientes.py          Cadastro e arquivamento
│   │   ├── agenda.py             Agendamento e cancelamento
│   │   ├── autenticacao.py       Login e bloqueio por (IP, usuário)
│   │   └── auditoria.py          Registro de eventos
│   ├── management/commands/
│   │   ├── criar_dentista.py     Cria o acesso da profissional
│   │   ├── auditar_staff.py      Detecta contas administrativas indevidas
│   │   └── seed_demo.py          Dados de exemplo (só com DEBUG=True)
│   ├── migrations/               Inclui migração de dados 0003→0005
│   ├── templatetags/icons.py     Ícones SVG inline
│   └── tests/                    36 testes de regressão
├── mxodontologia/settings.py     Configuração por variável de ambiente
├── templates/                    HTML
├── static/                       CSS e JS
├── pyproject.toml                Configuração do Ruff
├── render.yaml                   Infraestrutura como código (Render)
└── requirements.txt              Dependências com versão fixada
```

## Instalação

### Pré-requisitos

- Python 3.12 ou superior
- PostgreSQL 16 (produção) — SQLite serve para desenvolvimento

### Passo a passo

```bash
git clone https://github.com/gustavoeguchi06-sys/DentistaMX.git
cd DentistaMX
```

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
```

```bash
pip install -r requirements.txt
```

## Configuração do ambiente

Copie o arquivo de exemplo e gere uma chave secreta:

```bash
cp .env.example .env
```

```bash
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

Cole o resultado em `SECRET_KEY` dentro do `.env`.

> **Dois comportamentos que surpreendem quem não leu:**
>
> `DEBUG` vale **False** por padrão. Para desenvolver, defina `DEBUG=True`
> explicitamente. Assim, uma variável que não chega ao processo em produção
> nunca resulta em modo de depuração ligado.
>
> `SECRET_KEY` é **obrigatória** quando `DEBUG=False`. A aplicação se recusa a
> subir sem ela, em vez de servir requisições com uma chave conhecida — o que
> permitiria forjar sessões e tokens de redefinição de senha.

Prepare o banco e crie o primeiro acesso:

```bash
python manage.py migrate
```

```bash
python manage.py criar_dentista
```

## Variáveis de ambiente

### Obrigatórias em produção

| Variável | Descrição |
|---|---|
| `SECRET_KEY` | Chave criptográfica do Django, mínimo 50 caracteres. Sem ela o app não sobe com `DEBUG=False` |
| `DATABASE_URL` | Conexão PostgreSQL (`postgres://usuario:senha@host:porta/banco`) |
| `ALLOWED_HOSTS` | Domínios aceitos, separados por vírgula |

### Aplicação

| Variável | Padrão | Descrição |
|---|---|---|
| `DEBUG` | `False` | Modo de depuração. Ligue apenas em desenvolvimento |
| `USE_SQLITE_FALLBACK` | `true` se `DEBUG` | Permite SQLite. Ignorado em produção |
| `LOG_LEVEL` | `INFO` | Nível do logger `clinic` |
| `RENDER_EXTERNAL_HOSTNAME` | — | Preenchido automaticamente pelo Render |

### Banco (alternativa ao `DATABASE_URL`)

| Variável | Padrão |
|---|---|
| `POSTGRES_DB` · `POSTGRES_USER` · `POSTGRES_PASSWORD` | — |
| `POSTGRES_HOST` | `localhost` |
| `POSTGRES_PORT` | `5432` |

### E-mail

Sem `EMAIL_HOST_USER` e `EMAIL_HOST_PASSWORD`, o sistema usa o *console
backend* e imprime os e-mails no terminal — conveniente em desenvolvimento.

| Variável | Padrão |
|---|---|
| `EMAIL_HOST` | `smtp.gmail.com` |
| `EMAIL_PORT` | `587` |
| `EMAIL_USE_TLS` | `True` |
| `EMAIL_HOST_USER` · `EMAIL_HOST_PASSWORD` · `DEFAULT_FROM_EMAIL` | — |

> Para Gmail, use uma [senha de app](https://myaccount.google.com/apppasswords),
> nunca a senha da conta.

### Bloqueio de login

| Variável | Padrão | Descrição |
|---|---|---|
| `LOGIN_MAX_ATTEMPTS` | `5` | Falhas toleradas por (IP, usuário) |
| `LOGIN_LOCKOUT_MINUTES` | `15` | Duração do bloqueio |
| `LOGIN_ATTEMPT_WINDOW_MINUTES` | `15` | Janela de contagem |
| `LOGIN_ATTEMPT_RETENTION_DAYS` | `90` | Retenção do histórico de tentativas |

## Como executar

```bash
python manage.py runserver
```

A aplicação sobe em `http://127.0.0.1:8000/`.

### Outros comandos

```bash
python manage.py test
```
```bash
python manage.py auditar_staff
```
```bash
python manage.py check --deploy
```
```bash
python manage.py seed_demo
```

| Comando | O que faz |
|---|---|
| `test` | Suíte completa — 36 testes de regressão |
| `auditar_staff` | Lista contas administrativas e sinaliza as suspeitas. Use `--strict` no deploy para falhar quando houver conta inesperada |
| `check --deploy` | Validação de segurança para produção. Deve terminar sem nenhum aviso |
| `seed_demo` | Dados de exemplo. Recusa-se a rodar com `DEBUG=False`, para nunca criar paciente fictício indistinguível de um real |

### Rotas

| Rota | Nome | Acesso |
|---|---|---|
| `/` | `dashboard` | Dentista |
| `/pacientes/` | `pacientes` | Dentista |
| `/pacientes/adicionar/` | `paciente_add` | Dentista |
| `/pacientes/<pk>/` | `paciente_detail` | Dentista |
| `/pacientes/<pk>/arquivar/` | `paciente_arquivar` | Dentista · **POST** |
| `/pacientes/exportar/` | `pacientes_export` | Dentista |
| `/agenda/` · `/agenda/novo/` | `agenda` · `agenda_add` | Dentista |
| `/agenda/<pk>/cancelar/` | `consulta_cancelar` | Dentista · **POST** |
| `/prontuarios/` · `/prontuarios/novo/` | `prontuarios` · `prontuario_add` | Dentista |
| `/portal/` | `portal_paciente` | Paciente |
| `/login/` · `/logout/` | `login` · `logout` | Público · logout por **POST** |
| `/senha/recuperar/` | `password_reset` | Público |

Ações destrutivas respondem **apenas a POST**. Um `GET` retorna `405 Method Not
Allowed` — sem isso, uma tag `<img src="/pacientes/7/arquivar/">` numa página
qualquer, ou o prefetch do navegador, dispararia a ação sem nenhum clique.

## Exemplos de uso

### Cadastrar paciente e criar o acesso ao portal

O serviço cuida da transação inteira e devolve a senha temporária:

```python
from clinic.models import Paciente
from clinic.services import registrar_paciente

paciente = Paciente(
    nome='Ana Ribeiro',
    email='ana@example.com',
    telefone='11999998888',
)
paciente, senha_temp = registrar_paciente(paciente, request=request)
# Cria User + PerfilSeguranca + Paciente atomicamente.
# O paciente é obrigado a trocar a senha no primeiro acesso.
```

### Agendar consulta com verificação de conflito

```python
from clinic.models import Consulta
from clinic.services import agendar_consulta
from django.core.exceptions import ValidationError

consulta = Consulta(
    paciente=paciente,
    dentista=dentista,
    data_consulta=datetime(2026, 8, 12, 14, 30),
    duracao_min=60,
    procedimento='Canal',
)

try:
    agendar_consulta(consulta, request=request)
except ValidationError as erro:
    # "Dra. Ana já tem atendimento das 14:00 às 15:00 nesse dia."
    print(erro.message_dict['data_consulta'])
```

### Arquivar sem destruir histórico

```python
from clinic.services import arquivar_paciente

arquivar_paciente(paciente, usuario_responsavel=request.user, request=request)
# Marca arquivado_em/arquivado_por, desativa o acesso ao portal
# e registra o evento na auditoria.
# Consultas e prontuários permanecem intactos.
```

### Consultar a trilha de auditoria

```python
from clinic.models import EventoAuditoria

EventoAuditoria.objects.filter(
    objeto_tipo='Paciente',
    objeto_id='42',
).values_list('criado_em', 'usuario__username', 'acao', 'descricao')
```

### Usar os QuerySets nomeados

```python
Paciente.objects.ativos()              # exclui arquivados
Consulta.objects.do_dia(hoje).ativas() # do dia, sem canceladas
```

## Screenshots

> As imagens ainda não foram capturadas. Para gerá-las sem expor dado real de
> paciente, use o banco de demonstração:
>
> ```bash
> DEBUG=True python manage.py seed_demo
> ```
>
> Capture `/` (dashboard), `/pacientes/`, `/agenda/` e `/portal/`, salve em
> `docs/screenshots/` e referencie aqui. **Nunca use o banco de produção para
> screenshots** — nomes e dados clínicos de pacientes reais não podem ir para
> um repositório.

| Tela | Arquivo esperado |
|---|---|
| Dashboard | `docs/screenshots/dashboard.png` |
| Lista de pacientes | `docs/screenshots/pacientes.png` |
| Agenda | `docs/screenshots/agenda.png` |
| Portal do paciente | `docs/screenshots/portal.png` |

## Roadmap

**Concluído**

- [x] Cadastro de pacientes, agenda e prontuários
- [x] Portal do paciente com isolamento por construção
- [x] Autorização por perfil em todas as rotas sensíveis
- [x] Camada de serviços com operações transacionais
- [x] Trilha de auditoria append-only sobre dado clínico
- [x] Bloqueio de login por (IP, usuário)
- [x] Arquivamento em vez de exclusão, com `PROTECT` no histórico
- [x] Detecção de conflito de horário na agenda
- [x] Paginação e busca nas listagens
- [x] Suíte de 36 testes e CI com lint, testes e `check --deploy`

**Em avaliação**

- [ ] Edição de paciente, consulta e prontuário pela interface
- [ ] Visão de calendário semanal e mensal
- [ ] Lembrete automático de consulta por e-mail
- [ ] Backup automatizado do PostgreSQL com restauração testada

## Melhorias futuras

| Melhoria | Motivação |
|---|---|
| **Autenticação em dois fatores** | A conta da dentista dá acesso a todo o prontuário da clínica; senha sozinha é pouco para esse nível de exposição |
| **Odontograma** | Registro por dente e face é o vocabulário real da odontologia; hoje o prontuário é texto livre |
| **Anexos no prontuário** | Radiografias e fotos intraorais exigem armazenamento com controle de acesso e verificação de tipo |
| **Retenção automática** | Expurgo programado de `TentativaLogin` e anonimização de cadastros após o prazo legal de guarda |
| **Relatórios gerenciais** | Taxa de comparecimento, procedimentos mais frequentes e ocupação da agenda |
| **API REST** | Permitiria app móvel e integração com sistemas de faturamento |
| **Separação em apps** | Dividir `clinic` em `pacientes`, `agenda` e `prontuarios` quando passar de ~2.000 linhas |

## Contribuição

Este é um projeto proprietário e não aceita contribuições externas. As
diretrizes abaixo valem para quem trabalha no código com autorização.

**Fluxo**

1. Crie uma branch a partir da `main`: `git checkout -b feat/nome-da-mudanca`
2. Escreva o teste antes da correção quando estiver consertando um defeito
3. Garanta que a suíte passa: `python manage.py test`
4. Verifique o lint: `ruff check .`
5. Abra um Pull Request descrevendo **o motivo** da mudança, não apenas o que mudou

**O CI bloqueia o merge** se falhar lint, testes, `check --deploy` (com
`--fail-level WARNING`) ou se houver migração pendente não commitada.

**Antes de mexer nas decisões de segurança**, leia o motivo delas neste README.
Várias parecem restrições arbitrárias até se entender o que elas previnem —
exclusão por `GET`, bloqueio contado só por conta e cascata no prontuário já
foram problemas reais neste código.

**Convenções**
- Código, commits e comentários em português
- Comentário explica *por quê*, não *o quê*
- Regra de negócio vai para `services/` ou para o model, nunca para a view

## Licença

**Copyright © 2026. Todos os direitos reservados.**

Software proprietário. Nenhuma permissão é concedida para usar, copiar,
modificar, distribuir ou criar obras derivadas deste código sem autorização
expressa por escrito do titular dos direitos.

O repositório é público para fins de demonstração e avaliação técnica. Isso não
constitui licença de uso.

---


