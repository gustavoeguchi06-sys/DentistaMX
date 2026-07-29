from django import forms
from django.core.validators import RegexValidator

from .models import Consulta, Dentista, Paciente, Prontuario

# Nomes próprios brasileiros usam acento, apóstrofo e ponto ("D'Ávila",
# "Dra. Ana"). O validador antigo recusava tudo isso e ainda assim não impedia
# cadastro pelo admin — a garantia real de integridade agora está no model.
nome_valido = RegexValidator(
    regex=r"^[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ.'\- ]*$",
    message='Use letras, espaços, apóstrofo, hífen ou ponto.',
)

telefone_valido = RegexValidator(
    regex=r'^[0-9]{10,15}$',
    message='Informe apenas números, com DDD (10 a 15 dígitos).',
)


class PacienteForm(forms.ModelForm):
    nome = forms.CharField(
        max_length=255,
        validators=[nome_valido],
        widget=forms.TextInput(attrs={
            'placeholder': 'Nome completo',
            'autocomplete': 'name',
        }),
    )
    data_nascimento = forms.DateField(
        required=False,
        input_formats=['%d/%m/%Y'],
        widget=forms.TextInput(attrs={
            'class': 'mask-date',
            'placeholder': 'dd/mm/aaaa',
            'inputmode': 'numeric',
            'pattern': r'[0-9]{2}/[0-9]{2}/[0-9]{4}',
            'title': 'Digite a data no formato dd/mm/aaaa.',
            'autocomplete': 'bday',
        }),
    )
    telefone = forms.CharField(
        validators=[telefone_valido],
        widget=forms.TextInput(attrs={
            'placeholder': 'Telefone com DDD',
            'inputmode': 'numeric',
            'maxlength': '15',
            'autocomplete': 'tel',
        }),
    )
    email = forms.EmailField(
        required=True,
        help_text='Usado para criar o acesso do paciente ao portal e enviar a senha inicial.',
        widget=forms.EmailInput(attrs={
            'placeholder': 'Email',
            'inputmode': 'email',
            'autocomplete': 'email',
        }),
    )
    especialidade = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Especialidade'}),
    )

    class Meta:
        model = Paciente
        fields = ['nome', 'data_nascimento', 'telefone', 'email', 'especialidade', 'status']

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()

    def clean_nome(self):
        return ' '.join(self.cleaned_data['nome'].split())


class ConsultaForm(forms.ModelForm):
    data_consulta = forms.DateTimeField(
        input_formats=['%d/%m/%Y %H:%M'],
        widget=forms.TextInput(attrs={
            'class': 'mask-datetime',
            'placeholder': 'dd/mm/aaaa hh:mm',
            'inputmode': 'numeric',
            'title': 'Digite a data/hora no formato dd/mm/aaaa hh:mm.',
            'autocomplete': 'off',
        }),
    )

    class Meta:
        model = Consulta
        fields = [
            'paciente', 'dentista', 'data_consulta',
            'duracao_min', 'procedimento', 'status', 'observacoes',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Não se agenda para paciente arquivado nem para profissional inativa.
        self.fields['paciente'].queryset = Paciente.objects.ativos()
        self.fields['dentista'].queryset = Dentista.objects.filter(ativo=True)


class ProntuarioForm(forms.ModelForm):
    class Meta:
        model = Prontuario
        fields = ['paciente', 'dentista', 'procedimento', 'observacoes']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['paciente'].queryset = Paciente.objects.ativos()
        self.fields['dentista'].queryset = Dentista.objects.filter(ativo=True)
