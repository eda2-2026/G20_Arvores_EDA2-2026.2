"""Gera pacientes e agendamentos fictícios (para testes e apresentação).
Os CPFs são gerados aleatoriamente com dígitos verificadores válidos."""
import random
from datetime import date, datetime, timedelta

from .erros import ConflitoDeHorario, PacienteJaCadastrado
from .modelos import digitos_verificadores, normalizar_texto

NOMES = ["Ana", "Bruno", "Carla", "Daniel", "Eduarda", "Felipe", "Gabriela", "Heitor",
         "Isabela", "João", "Larissa", "Lucas", "Mariana", "Matheus", "Natália", "Otávio",
         "Patrícia", "Rafael", "Sofia", "Thiago", "Valentina", "Vinícius", "Yasmin",
         "Ângela", "Érico", "Lívia", "Caio", "Beatriz", "Gustavo", "Helena"]
SOBRENOMES = ["Silva", "Santos", "Oliveira", "Souza", "Rodrigues", "Ferreira", "Alves",
              "Pereira", "Lima", "Gomes", "Costa", "Ribeiro", "Martins", "Carvalho",
              "Araújo", "Melo", "Barbosa", "Rocha", "Dias", "Nascimento", "Moreira"]
CONVENIOS = ["Unimed", "Amil", "Bradesco Saúde", "SulAmérica", "Particular"]
PROFISSIONAIS = ["Dra. Helena Prado", "Dr. Ricardo Nunes", "Dra. Camila Torres",
                 "Dr. André Moura"]
OBSERVACOES = ["", "", "", "Retorno", "Primeira consulta", "Exame de rotina",
               "Avaliação", "Limpeza", "Trazer exames"]


def gerar_cpf(rng):
    base = "".join(str(rng.randint(0, 9)) for _ in range(9))
    return base + digitos_verificadores(base)


def popular(clinica, pacientes=50, agendamentos=100, semente=None, dias=14):
    """Adiciona pacientes e agendamentos aleatórios à clínica.
    Agendamentos em horário comercial (8h-18h, dias úteis), em blocos de 30 min,
    entre hoje e `dias` dias à frente. Retorna (pacientes criados, agendamentos criados)."""
    rng = random.Random(semente)
    hoje = clinica.agora().date()

    novos_pacientes = []
    while len(novos_pacientes) < pacientes:
        nome = f"{rng.choice(NOMES)} {rng.choice(SOBRENOMES)}"
        if rng.random() < 0.4:
            nome += f" {rng.choice(SOBRENOMES)}"
        nascimento = date(rng.randint(1940, hoje.year - 1), rng.randint(1, 12), rng.randint(1, 28))
        telefone = f"61{rng.choice('89')}{rng.randint(10_000_000, 99_999_999)}"
        email = f"{normalizar_texto(nome.split()[0])}.{rng.randint(1, 999)}@exemplo.com"
        try:
            novos_pacientes.append(clinica.cadastrar_paciente(
                gerar_cpf(rng), nome, nascimento, telefone,
                email, rng.choice(CONVENIOS)))
        except PacienteJaCadastrado:
            pass  # CPF repetido (raríssimo): tenta outro

    todos = clinica.listar_por_prontuario()
    novos_agendamentos, tentativas = [], 0
    while todos and len(novos_agendamentos) < agendamentos and tentativas < agendamentos * 20:
        tentativas += 1
        dia = hoje + timedelta(days=rng.randint(0, dias))
        if dia.weekday() >= 5:  # sábado/domingo
            continue
        horario = datetime.combine(dia, datetime.min.time()) + timedelta(
            hours=8, minutes=30 * rng.randint(0, 19))
        if horario < clinica.agora():
            continue
        try:
            novos_agendamentos.append(clinica.agendar(
                rng.choice(todos).cpf, horario, rng.choice(PROFISSIONAIS),
                duracao_min=rng.choice([30, 30, 30, 60]), observacao=rng.choice(OBSERVACOES)))
        except ConflitoDeHorario:
            pass
    return novos_pacientes, novos_agendamentos
