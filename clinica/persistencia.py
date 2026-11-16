"""
Salvar e carregar a clínica em JSON.

As árvores NÃO são salvas: só os registros (pacientes e agendamentos).
Ao carregar, os registros são reinseridos e as árvores se reconstroem e
rebalanceiam sozinhas. Isso deixa o arquivo simples, legível, e independente
da implementação das árvores.

Formato:
{
  "versao": 1,
  "salvo_em": "2026-11-16T08:00:00",
  "proximo_prontuario": 5,
  "proximo_id_agendamento": 9,
  "pacientes":    [{"prontuario": 1, "cpf": "...", "nome": "...", ...}],
  "agendamentos": [{"id": 1, "cpf_paciente": "...", "data_hora": "...", ...}]
}
"""
import json
import os
import tempfile
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from .erros import ErroClinica, ErroPersistencia
from .servico import Clinica

VERSAO = 1


def para_dict(clinica):
    pacientes = []
    for p in clinica.listar_por_prontuario():
        registro = asdict(p)
        registro["data_nascimento"] = p.data_nascimento.isoformat()
        pacientes.append(registro)

    agendamentos = []
    for ag in sorted(clinica.listar_agendamentos(), key=lambda a: a.id):
        registro = asdict(ag)
        registro["data_hora"] = ag.data_hora.isoformat(timespec="minutes")
        agendamentos.append(registro)

    return {
        "versao": VERSAO,
        "salvo_em": datetime.now().isoformat(timespec="seconds"),
        **clinica.contadores,
        "pacientes": pacientes,
        "agendamentos": agendamentos,
    }


def de_dict(dados, relogio=datetime.now):
    if not isinstance(dados, dict) or dados.get("versao") != VERSAO:
        raise ErroPersistencia("Arquivo de dados com formato/versão desconhecidos.")

    clinica = Clinica(relogio=relogio)
    for i, p in enumerate(dados.get("pacientes", []), start=1):
        try:
            clinica.cadastrar_paciente(**p)
        except (ErroClinica, TypeError) as erro:
            raise ErroPersistencia(f"Paciente nº {i} do arquivo é inválido: {erro}")

    for i, ag in enumerate(dados.get("agendamentos", []), start=1):
        try:
            clinica.agendar(
                cpf=ag["cpf_paciente"],
                data_hora=ag["data_hora"],
                profissional=ag["profissional"],
                duracao_min=ag.get("duracao_min", 30),
                observacao=ag.get("observacao", ""),
                id_agendamento=ag["id"],
                permitir_passado=True,  # histórico: consultas que já aconteceram
            )
        except (ErroClinica, KeyError, TypeError) as erro:
            raise ErroPersistencia(f"Agendamento nº {i} do arquivo é inválido: {erro}")

    clinica.restaurar_contadores(dados.get("proximo_prontuario", 1),
                                 dados.get("proximo_id_agendamento", 1))
    return clinica


def salvar(clinica, caminho):
    """Grava de forma atômica: escreve num arquivo temporário e só então
    substitui o original. Se o programa cair no meio, o arquivo antigo
    continua íntegro."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    fd, temporario = tempfile.mkstemp(dir=caminho.parent, prefix=".clinica-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as arquivo:
            json.dump(para_dict(clinica), arquivo, ensure_ascii=False, indent=2)
        os.replace(temporario, caminho)
    except BaseException:
        if os.path.exists(temporario):
            os.remove(temporario)
        raise


def carregar(caminho, relogio=datetime.now):
    """Carrega a clínica do arquivo. Se o arquivo não existir, retorna vazia."""
    caminho = Path(caminho)
    if not caminho.exists():
        return Clinica(relogio=relogio)
    try:
        with open(caminho, encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
    except json.JSONDecodeError as erro:
        raise ErroPersistencia(f"Arquivo {caminho} corrompido: {erro}")
    return de_dict(dados, relogio=relogio)
