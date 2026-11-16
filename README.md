# G20 — Árvores (EDA2 2026.2)

Sistema de gerenciamento de pacientes e agendamentos para clínicas, usando
**Árvore AVL** (pacientes) e **Árvore Rubro-Negra** (agenda), implementadas do zero
em Python puro (sem bibliotecas externas).

## Requisitos

- Python 3.10+

## Como executar

```bash
python3 -m clinica                     # menu no terminal (dados em dados/clinica.json)
python3 -m clinica --arquivo outro.json
```

Use a opção **19 — Gerar dados de exemplo** para popular o sistema rapidamente.

## Testes e demonstrações

```bash
python3 -m unittest -v           # todos os testes
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
