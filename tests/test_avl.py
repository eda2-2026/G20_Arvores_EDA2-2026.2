import random
import unittest

from clinica.arvores.avl import ArvoreAVL


class TestArvoreAVL(unittest.TestCase):
    def setUp(self):
        self.arvore = ArvoreAVL()

    def test_arvore_vazia(self):
        self.assertEqual(len(self.arvore), 0)
        self.assertEqual(self.arvore.altura(), 0)
        self.assertIsNone(self.arvore.buscar(1))
        self.assertIsNone(self.arvore.minimo())
        self.assertEqual(list(self.arvore.em_ordem()), [])
        with self.assertRaises(KeyError):
            self.arvore.remover(1)

    def test_insercao_e_busca(self):
        self.assertTrue(self.arvore.inserir(10, "dez"))
        self.assertTrue(self.arvore.inserir(5, "cinco"))
        self.assertEqual(self.arvore.buscar(10), "dez")
        self.assertEqual(self.arvore[5], "cinco")
        self.assertIn(5, self.arvore)
        self.assertNotIn(7, self.arvore)

    def test_chave_duplicada_nao_insere(self):
        self.arvore.inserir(1, "a")
        self.assertFalse(self.arvore.inserir(1, "b"))
        self.assertEqual(len(self.arvore), 1)
        self.assertEqual(self.arvore.buscar(1), "a")

    def test_valor_none(self):
        self.arvore.inserir(1, None)
        self.assertTrue(self.arvore.contem(1))
        self.assertIsNone(self.arvore.remover(1))

    def test_rotacoes_simples_e_duplas(self):
        # cada sequência dispara um dos 4 casos e deve resultar na raiz 2
        for seq in ([3, 2, 1], [1, 2, 3], [3, 1, 2], [1, 3, 2]):
            arvore = ArvoreAVL()
            for k in seq:
                arvore.inserir(k)
            self.assertEqual(arvore.raiz.chave, 2, seq)
            self.assertEqual(arvore.altura(), 2)
            arvore.validar()

    def test_insercao_ordenada_mantem_altura_logaritmica(self):
        for k in range(1024):
            self.arvore.inserir(k)
        self.arvore.validar()
        # altura de uma AVL <= 1.44 * log2(n + 2)
        self.assertLessEqual(self.arvore.altura(), 15)

    def test_em_ordem_intervalo_min_max(self):
        chaves = [50, 30, 70, 20, 40, 60, 80]
        for k in chaves:
            self.arvore.inserir(k, str(k))
        self.assertEqual(list(self.arvore), sorted(chaves))
        self.assertEqual([k for k, _ in self.arvore.intervalo(25, 60)], [30, 40, 50, 60])
        self.assertEqual(self.arvore.intervalo(81, 99), [])
        self.assertEqual(self.arvore.minimo(), (20, "20"))
        self.assertEqual(self.arvore.maximo(), (80, "80"))

    def test_filtrar(self):
        for k in range(10):
            self.arvore.inserir(k, {"idade": k * 10})
        resultado = self.arvore.filtrar(lambda p: p["idade"] >= 70)
        self.assertEqual([k for k, _ in resultado], [7, 8, 9])

    def test_remocao_casos(self):
        for k in [50, 30, 70, 20, 40, 60, 80]:
            self.arvore.inserir(k)
        self.arvore.remover(20)  # folha
        self.arvore.remover(30)  # um filho
        self.arvore.remover(50)  # dois filhos (raiz)
        self.arvore.validar()
        self.assertEqual(list(self.arvore), [40, 60, 70, 80])

    def test_chaves_string_cpf(self):
        cpfs = ["98765432100", "01234567890", "55555555555"]
        for cpf in cpfs:
            self.arvore.inserir(cpf)
        self.assertEqual(list(self.arvore), sorted(cpfs))

    def test_aleatorio_contra_dict(self):
        """Compara a AVL com um dict após milhares de operações aleatórias."""
        rng = random.Random(42)
        referencia = {}
        for _ in range(5000):
            k = rng.randint(0, 500)
            if rng.random() < 0.6:
                self.assertEqual(self.arvore.inserir(k, k * 2), k not in referencia)
                referencia.setdefault(k, k * 2)
            elif k in referencia:
                self.assertEqual(self.arvore.remover(k), referencia.pop(k))
            self.assertEqual(len(self.arvore), len(referencia))
        self.arvore.validar()
        self.assertEqual(list(self.arvore.em_ordem()), sorted(referencia.items()))


if __name__ == "__main__":
    unittest.main()
