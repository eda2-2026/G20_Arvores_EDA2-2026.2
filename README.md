# G20 — Árvores (EDA2 2026.2)

Sistema de gerenciamento de pacientes e agendamentos para clínicas, usando
**Árvore AVL** (pacientes) e **Árvore Rubro-Negra** (agenda), implementadas do zero
em Python puro (sem bibliotecas externas).

## Requisitos

- Python 3.10+
- Flask (só para o front-end web)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Como executar

**Front-end web** (recomendado):

```bash
.venv/bin/python -m clinica.web        # abra http://127.0.0.1:5000
```

Páginas: Painel, Pacientes (7 modos de busca, cada um mostrando a operação
de árvore usada e o tempo medido), Agenda, Árvores (desenho dos 7 índices
reais) e **Laboratório** (AVL × Rubro-Negra lado a lado, com animação das
rotações). Se o sistema estiver vazio, o painel oferece gerar dados de exemplo.

**Menu no terminal** (não precisa de Flask):

```bash
python3 -m clinica                     # dados em dados/clinica.json
python3 -m clinica --arquivo outro.json
```

Os dois usam o mesmo arquivo `dados/clinica.json`, mas não rode os dois ao
mesmo tempo (cada um sobrescreve o arquivo ao salvar).

## Testes e demonstrações

```bash
.venv/bin/python -m unittest -v  # todos os testes (os do front exigem Flask)
python3 -m demos.demo_avl        # AVL: inserção ordenada e rotações
python3 -m demos.demo_rubro_negra # Rubro-Negra + comparação AVL x RN
python3 -m demos.demo_clinica    # serviço completo
```

## Estrutura

```
clinica/
  arvores/avl.py          Árvore AVL genérica
  arvores/rubro_negra.py  Árvore Rubro-Negra genérica (CLRS)
  modelos.py              Paciente, Agendamento e validações (CPF, datas…)
  servico.py              Clinica: índices em árvores + regras de negócio
  persistencia.py         Salvar/carregar em JSON
  dados_exemplo.py        Gerador de dados fictícios
  cli.py                  Menu no terminal
  web/                    Front-end Flask (app.py, templates/, static/)
tests/                    Testes unitários (unittest)
demos/                    Scripts de demonstração
```

## Índices

| Índice | Árvore | Chave |
|---|---|---|
| Pacientes por CPF | AVL | `cpf` |
| Pacientes por prontuário | AVL | `prontuario` |
| Pacientes por nome | AVL | `(nome_normalizado, cpf)` |
| Agenda por horário | Rubro-Negra | `(data_hora, id)` |
| Agenda por id | Rubro-Negra | `id` |
| Agenda por profissional | Rubro-Negra | `(profissional, data_hora, id)` |
| Agenda por paciente | Rubro-Negra | `(cpf, data_hora, id)` |

Pacientes são muito consultados e pouco alterados → AVL (mais baixa, buscas
mais curtas). A agenda muda o tempo todo → Rubro-Negra (menos rotações).
