"""Demonstração da AVL: python3 -m demos.demo_avl"""
from clinica.arvores import ArvoreAVL

arvore = ArvoreAVL()
print("Inserindo prontuários 1..10 EM ORDEM (pior caso de uma BST comum):\n")
for prontuario in range(1, 11):
    arvore.inserir(prontuario, f"Paciente {prontuario}")
print(arvore.desenhar())
print(f"\nTamanho={len(arvore)}  Altura={arvore.altura()}  Rotações={arvore.rotacoes}")
print("(uma BST sem balanceamento teria altura 10)")
print("\nIntervalo [3, 7]:", [k for k, _ in arvore.intervalo(3, 7)])

arvore.remover(4)
print("\nApós remover a raiz 4:\n" + arvore.desenhar())
arvore.validar()
print("\nPropriedades AVL válidas ✔")
