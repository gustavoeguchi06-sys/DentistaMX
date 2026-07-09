from django import forms
from django.contrib.auth.hashers import make_password
from django.core.validators import RegexValidator
from .models import (
    Paciente,
    Consulta,
    Prontuario,
    EstoqueItem,
    TransacaoFinanceira,
    Relatorio,
    Usuario,
)


class DateTimeLocalInput(forms.DateTimeInput):
    input_type = 'datetime-local'


only_letters = RegexValidator(
    regex=r'^[A-Za-zÀ-ÿ ]+$',
    message='Use apenas letras e espaços.',
)

only_digits = RegexValidator(
    regex=r'^[0-9]+$',
    message='Use apenas números.',
)


class PacienteForm(forms.ModelForm):
    nome = forms.CharField(
        validators=[only_letters],
        widget=forms.TextInput(
            attrs={
                'pattern': '^[A-Za-zÀ-ÿ ]+$',
                'inputmode': 'text',
                'placeholder': 'Nome completo',
                'title': 'Use apenas letras e espaços.',
            }
        ),
    )
    data_nascimento = forms.DateField(
        required=False,
        input_formats=['%d/%m/%Y'],
        widget=forms.TextInput(
            attrs={
                'class': 'mask-date',
                'placeholder': 'dd/mm/aaaa',
                'inputmode': 'numeric',
                'pattern': '[0-9]{2}/[0-9]{2}/[0-9]{4}',
                'title': 'Digite a data no formato dd/mm/aaaa.',
                'autocomplete': 'bday',
            }
        ),
    )
    telefone = forms.CharField(
        validators=[only_digits],
        widget=forms.TextInput(
            attrs={
                'placeholder': 'Telefone',
                'pattern': '^[0-9]+$',
                'inputmode': 'numeric',
                'title': 'Use apenas números.',
                'maxlength': '15',
                'autocomplete': 'tel',
            }
        ),
    )
    especialidade = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                'placeholder': 'Especialidade',
                'pattern': '^[A-Za-zÀ-ÿ ]*$',
                'inputmode': 'text',
                'title': 'Use apenas letras e espaços.',
            }
        ),
    )

    class Meta:
        model = Paciente
        fields = ['nome', 'data_nascimento', 'telefone', 'email', 'especialidade', 'status']
        widgets = {
            'email': forms.EmailInput(attrs={
                'placeholder': 'Email',
                'inputmode': 'email',
                'autocomplete': 'email',
            }),
        }


class ConsultaForm(forms.ModelForm):
    data_consulta = forms.DateTimeField(
        input_formats=['%d/%m/%Y %H:%M'],
        widget=forms.TextInput(
            attrs={
                'class': 'mask-datetime',
                'placeholder': 'dd/mm/aaaa hh:mm',
                'inputmode': 'numeric',
                'pattern': '[0-9]{2}/[0-9]{2}/[0-9]{4} [0-9]{2}:[0-9]{2}',
                'title': 'Digite a data/hora no formato dd/mm/aaaa hh:mm.',
                'autocomplete': 'off',
            }
        ),
    )
    dentista = forms.CharField(
        validators=[only_letters],
        widget=forms.TextInput(
            attrs={
                'placeholder': 'Nome do dentista',
                'pattern': '^[A-Za-zÀ-ÿ ]+$',
                'inputmode': 'text',
                'title': 'Use apenas letras e espaços.',
            }
        ),
    )
    procedimento = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                'inputmode': 'text',
            }
        ),
    )

    class Meta:
        model = Consulta
        fields = ['paciente', 'data_consulta', 'procedimento', 'dentista', 'status', 'observacoes']


class ProntuarioForm(forms.ModelForm):
    procedimento = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                'inputmode': 'text',
            }
        ),
    )

    class Meta:
        model = Prontuario
        fields = ['paciente', 'procedimento', 'observacoes']


class EstoqueItemForm(forms.ModelForm):
    nome = forms.CharField(label='Materiais')
    quantidade = forms.IntegerField(
        widget=forms.NumberInput(
            attrs={
                'inputmode': 'numeric',
                'min': '0',
            }
        )
    )

    class Meta:
        model = EstoqueItem
        fields = ['nome', 'quantidade', 'unidade', 'nivel_alerta']


class TransacaoFinanceiraForm(forms.ModelForm):
    data_operacao = forms.DateTimeField(widget=DateTimeLocalInput())
    valor = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                'inputmode': 'decimal',
                'step': '0.01',
                'min': '0',
            }
        ),
    )

    class Meta:
        model = TransacaoFinanceira
        fields = ['data_operacao', 'descricao', 'tipo', 'valor', 'categoria', 'observacoes']


class UsuarioForm(forms.ModelForm):
    nome = forms.CharField(
        validators=[only_letters],
        widget=forms.TextInput(
            attrs={
                'pattern': '^[A-Za-zÀ-ÿ ]+$',
                'inputmode': 'text',
                'title': 'Use apenas letras e espaços.',
            }
        ),
    )
    senha = forms.CharField(widget=forms.PasswordInput(), label='Senha')

    class Meta:
        model = Usuario
        fields = ['nome', 'email', 'funcao', 'status', 'permissoes']

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('senha')
        if password:
            user.senha_hash = make_password(password)
        if commit:
            user.save()
        return user


class PermissaoForm(forms.Form):
    usuario = forms.ModelChoiceField(queryset=Usuario.objects.all(), label='Usuário')
    permissoes = forms.CharField(max_length=255, required=False, label='Permissões')


class RelatorioForm(forms.ModelForm):
    class Meta:
        model = Relatorio
        fields = ['nome', 'periodo', 'status']
