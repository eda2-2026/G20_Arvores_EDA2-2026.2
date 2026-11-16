"""Demonstração do serviço da clínica: python3 -m demos.demo_clinica"""
from datetime import datetime

from clinica.erros import ErroClinica
from clinica.servico import Clinica

c = Clinica(relogio=lambda: datetime(2026, 11, 16, 8, 0))

c.cadastrar_paciente("529.982.247-25", "Maria Oliveira", "1955-03-10", convenio="Unimed")
c.cadastrar_paciente("111.444.777-35", "João Pereira", "1988-07-22", convenio="Amil")
c.cadastrar_paciente("390.533.447-05", "Ângela Costa", "2010-01-15", convenio="Unimed")
c.cadastrar_paciente("714.602.380-01", "Bruno Alves", "1972-11-30")

print("Ordem alfabética:")
for p in c.listar_alfabetico():
    print(f"  #{p.prontuario}  {p.nome:<16} {p.cpf_formatado}  {p.idade(c.agora().date())} anos")

print("\nPacientes com 60+ anos ou do convênio Unimed:")
print("  60+:   ", [p.nome for p in c.filtrar_pacientes(idade_min=60)])
print("  Unimed:", [p.nome for p in c.filtrar_pacientes(convenio="unimed")])
print("Prefixo 'an':", [p.nome for p in c.buscar_por_nome("an")])

c.agendar("52998224725", "2026-11-16 09:00", "Dra. Helena", duracao_min=60)
c.agendar("11144477735", "2026-11-16 10:00", "Dra. Helena")
c.agendar("39053344705", "2026-11-16 09:30", "Dr. Ricardo")
c.agendar("71460238001", "2026-11-17 14:00", "Dr. Ricardo")

print("\nTentando agendar Bruno com a Dra. Helena às 09:30:")
try:
    c.agendar("71460238001", "2026-11-16 09:30", "Dra. Helena")
except ErroClinica as erro:
    print("  ✘", erro)

print("\nPróximos 3 atendimentos:")
for ag in c.proximos_atendimentos(3):
    paciente = c.buscar_por_cpf(ag.cpf_paciente)
    print(f"  {ag.data_hora:%d/%m %H:%M}-{ag.fim:%H:%M}  {ag.profissional:<12} {paciente.nome}")

print("\nÍndices (árvores):")
print(f"  {'Índice':<26}{'Tipo':<13}{'Tam':>4}{'Alt':>5}")
for s in c.estatisticas():
    print(f"  {s['indice']:<26}{s['tipo']:<13}{s['tamanho']:>4}{s['altura']:>5}")
c.validar_indices()
