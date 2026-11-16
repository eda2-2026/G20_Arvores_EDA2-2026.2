"""Entidades do domínio (Paciente, Agendamento) e funções de validação."""
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from .erros import DadosInvalidos

DURACAO_MINIMA = 5     # minutos
DURACAO_MAXIMA = 240   # minutos (usada também na checagem de conflitos)


# ---------------------------------------------------------------------- #
# Funções utilitárias
# ---------------------------------------------------------------------- #
def somente_digitos(texto):
    return re.sub(r"\D", "", str(texto or ""))


def digitos_verificadores(nove_digitos):
    """Calcula os 2 dígitos verificadores de um CPF a partir dos 9 primeiros."""
    d = [int(c) for c in nove_digitos]
    for n in (9, 10):  # pesos 10..2 para o 1º DV e 11..2 para o 2º
        soma = sum(d[i] * (n + 1 - i) for i in range(n))
        d.append(soma * 10 % 11 % 10)
    return f"{d[9]}{d[10]}"


def validar_cpf(cpf):
    """Retorna o CPF só com dígitos (str, preserva zeros à esquerda).
    Lança DadosInvalidos se o CPF não for válido."""
    d = somente_digitos(cpf)
    if len(d) != 11 or d == d[0] * 11 or digitos_verificadores(d[:9]) != d[9:]:
        raise DadosInvalidos(f"CPF inválido: {cpf}")
    return d


def formatar_cpf(cpf):
    d = somente_digitos(cpf)
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}" if len(d) == 11 else cpf


def normalizar_texto(texto):
    """Remove acentos, ignora maiúsculas e espaços extras.
    'José  da Silva' -> 'jose da silva'. Usado nas chaves de ordenação."""
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return " ".join(sem_acento.casefold().split())


def _validar_nome(nome, campo="Nome"):
    nome = " ".join(str(nome or "").split())
    if len(nome) < 2:
        raise DadosInvalidos(f"{campo} é obrigatório.")
    return nome


def _validar_data_nascimento(valor, hoje):
    if isinstance(valor, str):
        try:
            valor = date.fromisoformat(valor)
        except ValueError:
            raise DadosInvalidos(f"Data de nascimento inválida: {valor} (use AAAA-MM-DD)")
    if isinstance(valor, datetime):
        valor = valor.date()
    if not isinstance(valor, date):
        raise DadosInvalidos("Data de nascimento é obrigatória.")
    if valor > hoje:
        raise DadosInvalidos("Data de nascimento não pode estar no futuro.")
    if valor.year < 1900:
        raise DadosInvalidos("Data de nascimento muito antiga.")
    return valor


def _validar_email(email):
    email = str(email or "").strip()
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise DadosInvalidos(f"E-mail inválido: {email}")
    return email


def _validar_telefone(telefone):
    d = somente_digitos(telefone)
    if d and not 10 <= len(d) <= 11:
        raise DadosInvalidos(f"Telefone inválido: {telefone} (use DDD + número)")
    return d


def _validar_data_hora(valor):
    if isinstance(valor, str):
        try:
            valor = datetime.fromisoformat(valor)
        except ValueError:
            raise DadosInvalidos(f"Data/hora inválida: {valor} (use AAAA-MM-DD HH:MM)")
    if not isinstance(valor, datetime):
        raise DadosInvalidos("Data/hora é obrigatória.")
    return valor.replace(second=0, microsecond=0)


def _validar_duracao(duracao):
    try:
        duracao = int(duracao)
    except (TypeError, ValueError):
        raise DadosInvalidos(f"Duração inválida: {duracao}")
    if not DURACAO_MINIMA <= duracao <= DURACAO_MAXIMA:
        raise DadosInvalidos(
            f"Duração deve estar entre {DURACAO_MINIMA} e {DURACAO_MAXIMA} minutos.")
    return duracao


# ---------------------------------------------------------------------- #
# Entidades
# ---------------------------------------------------------------------- #
@dataclass
class Paciente:
    prontuario: int
    cpf: str
    nome: str
    data_nascimento: date
    telefone: str = ""
    email: str = ""
    convenio: str = ""

    @property
    def chave_nome(self):
        """Chave do índice alfabético. O CPF desempata nomes iguais."""
        return (normalizar_texto(self.nome), self.cpf)

    def idade(self, hoje=None):
        hoje = hoje or date.today()
        n = self.data_nascimento
        return hoje.year - n.year - ((hoje.month, hoje.day) < (n.month, n.day))

    @property
    def cpf_formatado(self):
        return formatar_cpf(self.cpf)


@dataclass
class Agendamento:
    id: int
    cpf_paciente: str
    profissional: str
    data_hora: datetime
    duracao_min: int = 30
    observacao: str = ""

    @property
    def fim(self):
        return self.data_hora + timedelta(minutes=self.duracao_min)

    def sobrepoe(self, inicio, fim):
        """Intervalos semiabertos [início, fim): 9h-9h30 não conflita com 9h30-10h."""
        return self.data_hora < fim and inicio < self.fim

    # chaves usadas nos índices da agenda
    @property
    def chave_horario(self):
        return (self.data_hora, self.id)

    @property
    def chave_profissional(self):
        return (normalizar_texto(self.profissional), self.data_hora, self.id)

    @property
    def chave_paciente(self):
        return (self.cpf_paciente, self.data_hora, self.id)
