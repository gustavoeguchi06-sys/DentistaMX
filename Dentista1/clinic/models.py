from datetime import date
from django.db import models


class Paciente(models.Model):
    nome = models.CharField(max_length=255)
    data_nascimento = models.DateField(null=True, blank=True)
    telefone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(max_length=255, blank=True)
    especialidade = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=50, default='Ativo')
    data_cadastro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome

    @property
    def idade(self):
        if self.data_nascimento:
            today = date.today()
            born = self.data_nascimento
            age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
            return age
        return ''


class Consulta(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='consultas')
    data_consulta = models.DateTimeField()
    procedimento = models.CharField(max_length=255, blank=True)
    dentista = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=50, default='Agendada')
    observacoes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.paciente.nome} - {self.data_consulta:%d/%m/%Y %H:%M}"


class Prontuario(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='prontuarios')
    data_registro = models.DateTimeField(auto_now_add=True)
    procedimento = models.CharField(max_length=255, blank=True)
    observacoes = models.TextField(blank=True)

    def __str__(self):
        return f"Prontuário de {self.paciente.nome} - {self.data_registro:%d/%m/%Y}"


class EstoqueItem(models.Model):
    nome = models.CharField(max_length=255)
    quantidade = models.IntegerField(default=0)
    unidade = models.CharField(max_length=50, blank=True)
    nivel_alerta = models.CharField(max_length=50, default='Normal')
    data_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nome


class TransacaoFinanceira(models.Model):
    TIPO_CHOICES = [
        ('Receita', 'Receita'),
        ('Despesa', 'Despesa'),
    ]

    data_operacao = models.DateTimeField()
    descricao = models.CharField(max_length=255)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    categoria = models.CharField(max_length=120, blank=True)
    observacoes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.tipo} - {self.descricao} ({self.valor})"


class Relatorio(models.Model):
    nome = models.CharField(max_length=255)
    periodo = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=50, default='Disponível')
    data_geracao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome


class Usuario(models.Model):
    nome = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    funcao = models.CharField(max_length=100, blank=True)
    senha_hash = models.CharField(max_length=255)
    status = models.CharField(max_length=50, default='Ativo')
    permissoes = models.CharField(max_length=255, blank=True)
    ultimo_login = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.nome
