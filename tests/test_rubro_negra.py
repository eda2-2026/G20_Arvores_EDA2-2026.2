import math
import random
import unittest
from datetime import datetime, timedelta

from clinica.arvores.rubro_negra import PRETO, VERMELHO, ArvoreRubroNegra


class TestArvoreRubroNegra(unittest.TestCase):
    def setUp(self):
        self.arvore = ArvoreRubroNegra()

    def test_arvore_vazia(self):
        self.assertEqual(len(self.arvore), 0)
        self.assertEqual(self.arvore.altura(), 0)
        self.assertIsNone(self.arvore.buscar(1))
        self.assertIsNone(self.arvore.minimo())
        self.assertEqual(self.arvore.proximos(0, 5), [])
        with self.assertRaises(KeyError):
            self.arvore.remover(1)
        self.arvore.validar()

    def test_raiz_preta_e_filhos_vermelhos(self):
        for k in [10, 5, 15]:
            self.arvore.inserir(k)
        self.assertEqual(self.arvore.raiz.cor, PRETO)
        self.assertEqual(self.arvore.raiz.esquerda.cor, VERMELHO)
        self.assertEqual(self.arvore.raiz.direita.cor, VERMELHO)

    def test_insercao_busca_duplicada(self):
        self.assertTrue(self.arvore.inserir(1, "a"))
        self.assertFalse(self.arvore.inserir(1, "b"))
        self.assertEqual(self.arvore[1], "a")
        self.assertEqual(len(self.arvore), 1)
        self.assertIn(1, self.arvore)

    def test_casos_de_rotacao(self):
        for seq in ([3, 2, 1], [1, 2, 3], [3, 1, 2], [1, 3, 2]):
            arvore = ArvoreRubroNegra()
            for k in seq:
                arvore.inserir(k)
            self.assertEqual(arvore.raiz.chave, 2, seq)
            arvore.validar()

    def test_insercao_ordenada_altura_limitada(self):
        n = 1024
        for k in range(n):
            self.arvore.inserir(k)
            if k % 128 == 0:
                self.arvore.validar()
        self.arvore.validar()
        self.assertLessEqual(self.arvore.altura(), 2 * math.log2(n + 1))

    def test_remocao_casos(self):
        chaves = [50, 30, 70, 20, 40, 60, 80, 10, 25, 35, 45]
        for k in chaves:
            self.arvore.inserir(k, str(k))
        for k in [10, 30, 50, 80]:  # folha, 2 filhos, raiz, sem irmão vermelho
            self.assertEqual(self.arvore.remover(k), str(k))
            self.arvore.validar()
        self.assertEqual(list(self.arvore), [20, 25, 35, 40, 45, 60, 70])

    def test_remover_tudo(self):
        for k in range(100):
            self.arvore.inserir(k)
        for k in random.Random(1).sample(range(100), 100):
            self.arvore.remover(k)
            self.arvore.validar()
        self.assertEqual(len(self.arvore), 0)
        self.assertIs(self.arvore.raiz, self.arvore.NIL)

    def test_intervalo_e_proximos(self):
        for k in range(0, 100, 10):
            self.arvore.inserir(k)
        self.assertEqual([k for k, _ in self.arvore.intervalo(25, 60)], [30, 40, 50, 60])
        self.assertEqual([k for k, _ in self.arvore.proximos(35, 3)], [40, 50, 60])
        self.assertEqual([k for k, _ in self.arvore.proximos(40, 2)], [40, 50])
        self.assertEqual(self.arvore.proximos(95, 3), [])
        self.assertEqual(len(self.arvore.proximos(-1)), 10)  # sem limite

    def test_chaves_de_agendamento(self):
        """Chave (data_hora, id): horários iguais não colidem."""
        base = datetime(2026, 11, 16, 8, 0)
        self.arvore.inserir((base + timedelta(hours=2), 1), "Ana")
        self.arvore.inserir((base, 2), "Bruno")
        self.arvore.inserir((base, 3), "Carla")  # mesmo horário que Bruno
        self.arvore.inserir((base + timedelta(hours=1), 4), "Davi")

        nomes = [v for _, v in self.arvore.em_ordem()]
        self.assertEqual(nomes, ["Bruno", "Carla", "Davi", "Ana"])

        # "a partir de" um instante: tupla de 1 elemento
        a_partir = (base + timedelta(minutes=30),)
        self.assertEqual([v for _, v in self.arvore.proximos(a_partir, 2)], ["Davi", "Ana"])
        self.assertEqual([v for _, v in self.arvore.proximos((base,), 1)], ["Bruno"])

    def test_aleatorio_contra_dict(self):
        rng = random.Random(42)
        referencia = {}
        for i in range(5000):
            k = rng.randint(0, 500)
            if rng.random() < 0.6:
                self.assertEqual(self.arvore.inserir(k, -k), k not in referencia)
                referencia.setdefault(k, -k)
            elif k in referencia:
                self.assertEqual(self.arvore.remover(k), referencia.pop(k))
            if i % 250 == 0:
                self.arvore.validar()
        self.arvore.validar()
        self.assertEqual(list(self.arvore.em_ordem()), sorted(referencia.items()))
        inicio = 250
        esperado = [kv for kv in sorted(referencia.items()) if kv[0] >= inicio][:7]
        self.assertEqual(self.arvore.proximos(inicio, 7), esperado)


if __name__ == "__main__":
    unittest.main()
