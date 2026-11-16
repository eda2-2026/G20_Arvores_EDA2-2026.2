"""
Árvore AVL genérica (chave -> valor).

Uma AVL é uma árvore binária de busca auto-balanceada: para todo nó, a
diferença entre as alturas das subárvores esquerda e direita (fator de
balanceamento) é -1, 0 ou +1. Isso garante altura O(log n) e, portanto,
busca, inserção e remoção em O(log n).

No projeto, ela indexa os pacientes (chave = CPF ou prontuário).
As chaves precisam ser comparáveis entre si (<, >, ==).
"""

_AUSENTE = object()  # sentinela: permite guardar None como valor


class NoAVL:
    __slots__ = ("chave", "valor", "esquerda", "direita", "altura")

    def __init__(self, chave, valor):
        self.chave = chave
        self.valor = valor
        self.esquerda = None
        self.direita = None
        self.altura = 1  # folha tem altura 1 (árvore vazia = 0)


class ArvoreAVL:
    def __init__(self):
        self.raiz = None
        self._tamanho = 0
        self.rotacoes = 0  # contador útil para a apresentação

    # ------------------------------------------------------------------ #
    # Auxiliares de altura e balanceamento
    # ------------------------------------------------------------------ #
    @staticmethod
    def _altura(no):
        return no.altura if no else 0

    def _atualizar_altura(self, no):
        no.altura = 1 + max(self._altura(no.esquerda), self._altura(no.direita))

    def _fator(self, no):
        return self._altura(no.esquerda) - self._altura(no.direita)

    def _rotacionar_direita(self, y):
        #       y            x
        #      / \          / \
        #     x   C  -->   A   y
        #    / \              / \
        #   A   B            B   C
        x = y.esquerda
        y.esquerda = x.direita
        x.direita = y
        self._atualizar_altura(y)
        self._atualizar_altura(x)
        self.rotacoes += 1
        return x

    def _rotacionar_esquerda(self, x):
        #     x                y
        #    / \              / \
        #   A   y    -->     x   C
        #      / \          / \
        #     B   C        A   B
        y = x.direita
        x.direita = y.esquerda
        y.esquerda = x
        self._atualizar_altura(x)
        self._atualizar_altura(y)
        self.rotacoes += 1
        return y

    def _balancear(self, no):
        self._atualizar_altura(no)
        fb = self._fator(no)

        if fb > 1:  # pesado à esquerda
            if self._fator(no.esquerda) < 0:  # caso Esquerda-Direita
                no.esquerda = self._rotacionar_esquerda(no.esquerda)
            return self._rotacionar_direita(no)  # caso Esquerda-Esquerda

        if fb < -1:  # pesado à direita
            if self._fator(no.direita) > 0:  # caso Direita-Esquerda
                no.direita = self._rotacionar_direita(no.direita)
            return self._rotacionar_esquerda(no)  # caso Direita-Direita

        return no

    # ------------------------------------------------------------------ #
    # Inserção
    # ------------------------------------------------------------------ #
    def inserir(self, chave, valor=None):
        """Insere (chave, valor). Retorna False se a chave já existir."""
        self.raiz, inserido = self._inserir(self.raiz, chave, valor)
        if inserido:
            self._tamanho += 1
        return inserido

    def _inserir(self, no, chave, valor):
        if no is None:
            return NoAVL(chave, valor), True
        if chave < no.chave:
            no.esquerda, inserido = self._inserir(no.esquerda, chave, valor)
        elif chave > no.chave:
            no.direita, inserido = self._inserir(no.direita, chave, valor)
        else:
            return no, False  # chave duplicada
        return self._balancear(no), inserido

    # ------------------------------------------------------------------ #
    # Remoção
    # ------------------------------------------------------------------ #
    def remover(self, chave):
        """Remove a chave e retorna o valor associado. KeyError se não existir."""
        self.raiz, valor = self._remover(self.raiz, chave)
        if valor is _AUSENTE:
            raise KeyError(chave)
        self._tamanho -= 1
        return valor

    def _remover(self, no, chave):
        if no is None:
            return None, _AUSENTE
        if chave < no.chave:
            no.esquerda, valor = self._remover(no.esquerda, chave)
        elif chave > no.chave:
            no.direita, valor = self._remover(no.direita, chave)
        else:
            valor = no.valor
            # 0 ou 1 filho: o filho (ou None) sobe no lugar do nó
            if no.esquerda is None:
                return no.direita, valor
            if no.direita is None:
                return no.esquerda, valor
            # 2 filhos: copia o sucessor em-ordem e o remove da direita
            sucessor = no.direita
            while sucessor.esquerda:
                sucessor = sucessor.esquerda
            no.chave, no.valor = sucessor.chave, sucessor.valor
            no.direita, _ = self._remover(no.direita, sucessor.chave)
        return self._balancear(no), valor

    # ------------------------------------------------------------------ #
    # Consultas
    # ------------------------------------------------------------------ #
    def buscar(self, chave, padrao=None):
        """Busca iterativa O(log n). Retorna o valor ou `padrao`."""
        no = self.raiz
        while no:
            if chave < no.chave:
                no = no.esquerda
            elif chave > no.chave:
                no = no.direita
            else:
                return no.valor
        return padrao

    def contem(self, chave):
        return self.buscar(chave, _AUSENTE) is not _AUSENTE

    def em_ordem(self):
        """Gera (chave, valor) em ordem crescente de chave (iterativo)."""
        pilha, no = [], self.raiz
        while pilha or no:
            while no:
                pilha.append(no)
                no = no.esquerda
            no = pilha.pop()
            yield no.chave, no.valor
            no = no.direita

    def intervalo(self, inicio, fim):
        """Lista (chave, valor) com inicio <= chave <= fim, em ordem.
        Só visita os ramos que podem conter chaves no intervalo."""
        resultado = []
        self._intervalo(self.raiz, inicio, fim, resultado)
        return resultado

    def _intervalo(self, no, inicio, fim, resultado):
        if no is None:
            return
        if inicio < no.chave:
            self._intervalo(no.esquerda, inicio, fim, resultado)
        if inicio <= no.chave <= fim:
            resultado.append((no.chave, no.valor))
        if no.chave < fim:
            self._intervalo(no.direita, inicio, fim, resultado)

    def filtrar(self, predicado):
        """Lista (chave, valor) cujo valor satisfaz predicado(valor). O(n)."""
        return [(k, v) for k, v in self.em_ordem() if predicado(v)]

    def minimo(self):
        if self.raiz is None:
            return None
        no = self.raiz
        while no.esquerda:
            no = no.esquerda
        return no.chave, no.valor

    def maximo(self):
        if self.raiz is None:
            return None
        no = self.raiz
        while no.direita:
            no = no.direita
        return no.chave, no.valor

    def altura(self):
        return self._altura(self.raiz)

    # ------------------------------------------------------------------ #
    # Protocolos Python
    # ------------------------------------------------------------------ #
    def __len__(self):
        return self._tamanho

    def __contains__(self, chave):
        return self.contem(chave)

    def __iter__(self):
        return (chave for chave, _ in self.em_ordem())

    def __getitem__(self, chave):
        valor = self.buscar(chave, _AUSENTE)
        if valor is _AUSENTE:
            raise KeyError(chave)
        return valor

    # ------------------------------------------------------------------ #
    # Depuração / apresentação
    # ------------------------------------------------------------------ #
    def desenhar(self, formatar=str):
        """Desenho textual da árvore (deitada: raiz à esquerda, direita em cima).
        `formatar` converte a chave em texto."""
        linhas = []

        def visitar(no, prefixo, eh_direita):
            if no is None:
                return
            visitar(no.direita, prefixo + ("    " if eh_direita else "│   "), True)
            conector = "┌── " if eh_direita else "└── "
            linhas.append(f"{prefixo}{conector}{formatar(no.chave)} (h={no.altura}, fb={self._fator(no)})")
            visitar(no.esquerda, prefixo + ("│   " if eh_direita else "    "), False)

        if self.raiz:
            visitar(self.raiz.direita, "", True)
            linhas.append(f"{formatar(self.raiz.chave)} (h={self.raiz.altura}, fb={self._fator(self.raiz)})")
            visitar(self.raiz.esquerda, "", False)
        return "\n".join(linhas) if linhas else "(árvore vazia)"

    def validar(self):
        """Verifica as propriedades da AVL. Lança AssertionError se violadas."""

        def checar(no, minimo, maximo):
            if no is None:
                return 0, 0
            assert minimo is None or no.chave > minimo, f"ordem violada em {no.chave}"
            assert maximo is None or no.chave < maximo, f"ordem violada em {no.chave}"
            he, qe = checar(no.esquerda, minimo, no.chave)
            hd, qd = checar(no.direita, no.chave, maximo)
            assert abs(he - hd) <= 1, f"desbalanceado em {no.chave}"
            assert no.altura == 1 + max(he, hd), f"altura errada em {no.chave}"
            return no.altura, 1 + qe + qd

        _, quantidade = checar(self.raiz, None, None)
        assert quantidade == self._tamanho, "tamanho inconsistente"
        return True

