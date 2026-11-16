"""Demonstração da Rubro-Negra: python3 -m demos.demo_rubro_negra"""
import random
from datetime import datetime, timedelta

from clinica.arvores import ArvoreAVL, ArvoreRubroNegra

# ---------------------------------------------------------------------- #
# 1) Agenda do dia: chave = (data_hora, id)
# ---------------------------------------------------------------------- #
agenda = ArvoreRubroNegra()
inicio_dia = datetime(2026, 11, 16, 8, 0)
pacientes = ["Ana", "Bruno", "Carla", "Davi", "Eva", "Fábio", "Gabi", "Hugo"]
rng = random.Random(7)
for id_ag, nome in enumerate(pacientes, start=1):
    horario = inicio_dia + timedelta(minutes=30 * rng.randint(0, 16))
    agenda.inserir((horario, id_ag), nome)


def fmt(chave):
    return f"{chave[0]:%H:%M}#{chave[1]}"


print("Agenda (V = vermelho, P = preto):\n")
print(agenda.desenhar(formatar=fmt))

agora = datetime(2026, 11, 16, 11, 0)
print(f"\nPróximos 3 atendimentos a partir de {agora:%H:%M}:")
for (horario, id_ag), nome in agenda.proximos((agora,), 3):
    print(f"  {horario:%H:%M}  #{id_ag}  {nome}")

print("\nAtendimentos entre 09:00 e 10:30:")
for (horario, id_ag), nome in agenda.intervalo((inicio_dia + timedelta(hours=1),),
                                                (inicio_dia + timedelta(hours=2, minutes=30), float("inf"))):
    print(f"  {horario:%H:%M}  #{id_ag}  {nome}")

agenda.validar()
print("\nPropriedades Rubro-Negra válidas ✔")

# ---------------------------------------------------------------------- #
# 2) Comparação AVL x Rubro-Negra
# ---------------------------------------------------------------------- #
print("\n" + "=" * 62)
print(f"{'Cenário':<28}{'Árvore':<14}{'Altura':>8}{'Rotações':>12}")
print("=" * 62)
n = 100_000
cenarios = {
    "inserção ordenada": list(range(n)),
    "inserção aleatória": random.Random(1).sample(range(n), n),
}
for nome, chaves in cenarios.items():
    for Arvore in (ArvoreAVL, ArvoreRubroNegra):
        arvore = Arvore()
        for k in chaves:
            arvore.inserir(k)
        print(f"{nome:<28}{Arvore.__name__[6:]:<14}{arvore.altura():>8}{arvore.rotacoes:>12}")

# remoção de metade das chaves (contando só as rotações da remoção)
for Arvore in (ArvoreAVL, ArvoreRubroNegra):
    arvore = Arvore()
    for k in cenarios["inserção aleatória"]:
        arvore.inserir(k)
    antes = arvore.rotacoes
    for k in random.Random(2).sample(range(n), n // 2):
        arvore.remover(k)
    print(f"{'remoção de 50% aleatória':<28}{Arvore.__name__[6:]:<14}"
          f"{arvore.altura():>8}{arvore.rotacoes - antes:>12}")

print(f"\nn = {n:,} chaves. AVL: altura menor no pior caso (buscas mais curtas).")
print("Rubro-Negra: menos rotações ao inserir/remover aleatoriamente.")
