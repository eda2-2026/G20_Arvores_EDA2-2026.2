"""
Árvore Rubro-Negra genérica (chave -> valor), baseada no Cormen (CLRS).

Propriedades:
  1. Todo nó é VERMELHO ou PRETO.
  2. A raiz é PRETA.
  3. Toda folha (NIL) é PRETA.
  4. Um nó VERMELHO não tem filho VERMELHO.
  5. Todo caminho de um nó até as folhas NIL tem o mesmo número de nós
     PRETOS (altura negra).

Isso garante altura <= 2*log2(n+1), logo busca/inserção/remoção em O(log n).
Comparada à AVL, é "menos rigidamente" balanceada: faz menos rotações em
inserções/remoções (no máximo 2 na inserção e 3 na remoção), ao custo de uma
altura um pouco maior.

No projeto, ela indexa os agendamentos. Chave sugerida: (data_hora, id), assim
dois agendamentos no mesmo horário não colidem. Para buscar "a partir de" um
instante, use a tupla (data_hora,) — em Python, (x,) < (x, qualquer_coisa).
"""

VERMELHO = True
PRETO = False

_AUSENTE = object()


class NoRN:
    __slots__ = ("chave", "valor", "cor", "esquerda", "direita", "pai")

    def __init__(self, chave, valor, cor, nil=None):
        self.chave = chave
        self.valor = valor
        self.cor = cor
        self.esquerda = nil
        self.direita = nil
        self.pai = nil


class ArvoreRubroNegra:
    def __init__(self):
        # Sentinela único que representa todas as folhas (e o pai da raiz).
        self.NIL = NoRN(None, None, PRETO)
        self.NIL.esquerda = self.NIL.direita = self.NIL.pai = self.NIL
        self.raiz = self.NIL
        self._tamanho = 0
        self.rotacoes = 0

    # ------------------------------------------------------------------ #
    # Rotações
    # ------------------------------------------------------------------ #
    def _rotacionar_esquerda(self, x):
        y = x.direita
        x.direita = y.esquerda
        if y.esquerda is not self.NIL:
            y.esquerda.pai = x
        y.pai = x.pai
        if x.pai is self.NIL:
            self.raiz = y
        elif x is x.pai.esquerda:
            x.pai.esquerda = y
        else:
            x.pai.direita = y
        y.esquerda = x
        x.pai = y
        self.rotacoes += 1

    def _rotacionar_direita(self, y):
        x = y.esquerda
        y.esquerda = x.direita
        if x.direita is not self.NIL:
            x.direita.pai = y
        x.pai = y.pai
        if y.pai is self.NIL:
            self.raiz = x
        elif y is y.pai.direita:
            y.pai.direita = x
        else:
            y.pai.esquerda = x
        x.direita = y
        y.pai = x
        self.rotacoes += 1

    # ------------------------------------------------------------------ #
    # Inserção
    # ------------------------------------------------------------------ #
    def inserir(self, chave, valor=None):
        """Insere (chave, valor). Retorna False se a chave já existir."""
        pai, atual = self.NIL, self.raiz
        while atual is not self.NIL:
            pai = atual
            if chave < atual.chave:
                atual = atual.esquerda
            elif chave > atual.chave:
                atual = atual.direita
            else:
                return False  # chave duplicada

        novo = NoRN(chave, valor, VERMELHO, self.NIL)
        novo.pai = pai
        if pai is self.NIL:
            self.raiz = novo
        elif chave < pai.chave:
            pai.esquerda = novo
        else:
            pai.direita = novo

        self._tamanho += 1
        self._corrigir_insercao(novo)
        return True

    def _corrigir_insercao(self, z):
        # Único problema possível: z e seu pai são ambos VERMELHOS.
        while z.pai.cor == VERMELHO:
            avo = z.pai.pai
            if z.pai is avo.esquerda:
                tio = avo.direita
                if tio.cor == VERMELHO:
                    # Caso 1: tio vermelho -> recolore e sobe o problema
                    z.pai.cor = PRETO
                    tio.cor = PRETO
                    avo.cor = VERMELHO
                    z = avo
                else:
                    if z is z.pai.direita:
                        # Caso 2: "triângulo" -> vira "linha"
                        z = z.pai
                        self._rotacionar_esquerda(z)
                    # Caso 3: "linha" -> recolore e rotaciona o avô
                    z.pai.cor = PRETO
                    z.pai.pai.cor = VERMELHO
                    self._rotacionar_direita(z.pai.pai)
            else:  # espelho: pai é filho direito do avô
                tio = avo.esquerda
                if tio.cor == VERMELHO:
                    z.pai.cor = PRETO
                    tio.cor = PRETO
                    avo.cor = VERMELHO
                    z = avo
                else:
                    if z is z.pai.esquerda:
                        z = z.pai
                        self._rotacionar_direita(z)
                    z.pai.cor = PRETO
                    z.pai.pai.cor = VERMELHO
                    self._rotacionar_esquerda(z.pai.pai)
        self.raiz.cor = PRETO

    # ------------------------------------------------------------------ #
    # Remoção
    # ------------------------------------------------------------------ #
    def _transplantar(self, u, v):
        """Coloca a subárvore v no lugar de u."""
        if u.pai is self.NIL:
            self.raiz = v
        elif u is u.pai.esquerda:
            u.pai.esquerda = v
        else:
            u.pai.direita = v
        v.pai = u.pai  # pode alterar NIL.pai: é intencional (usado na correção)

    def _minimo_no(self, no):
        while no.esquerda is not self.NIL:
            no = no.esquerda
        return no

    def remover(self, chave):
        """Remove a chave e retorna o valor associado. KeyError se não existir."""
        z = self._buscar_no(chave)
        if z is self.NIL:
            raise KeyError(chave)
        valor = z.valor

        y = z
        cor_original = y.cor
        if z.esquerda is self.NIL:
            x = z.direita
            self._transplantar(z, z.direita)
        elif z.direita is self.NIL:
            x = z.esquerda
            self._transplantar(z, z.esquerda)
        else:
            # dois filhos: o sucessor y ocupa o lugar de z
            y = self._minimo_no(z.direita)
            cor_original = y.cor
            x = y.direita
            if y.pai is z:
                x.pai = y
            else:
                self._transplantar(y, y.direita)
                y.direita = z.direita
                y.direita.pai = y
            self._transplantar(z, y)
            y.esquerda = z.esquerda
            y.esquerda.pai = y
            y.cor = z.cor

        # Remover um nó PRETO quebra a altura negra: x fica "duplamente preto".
        if cor_original == PRETO:
            self._corrigir_remocao(x)
        self._tamanho -= 1
        return valor

    def _corrigir_remocao(self, x):
        while x is not self.raiz and x.cor == PRETO:
            if x is x.pai.esquerda:
                w = x.pai.direita  # irmão
                if w.cor == VERMELHO:
                    # Caso 1: irmão vermelho -> transforma em irmão preto
                    w.cor = PRETO
                    x.pai.cor = VERMELHO
                    self._rotacionar_esquerda(x.pai)
                    w = x.pai.direita
                if w.esquerda.cor == PRETO and w.direita.cor == PRETO:
                    # Caso 2: irmão preto com filhos pretos -> recolore e sobe
                    w.cor = VERMELHO
                    x = x.pai
                else:
                    if w.direita.cor == PRETO:
                        # Caso 3: sobrinho distante preto -> rotaciona o irmão
                        w.esquerda.cor = PRETO
                        w.cor = VERMELHO
                        self._rotacionar_direita(w)
                        w = x.pai.direita
                    # Caso 4: sobrinho distante vermelho -> resolve
                    w.cor = x.pai.cor
                    x.pai.cor = PRETO
                    w.direita.cor = PRETO
                    self._rotacionar_esquerda(x.pai)
                    x = self.raiz
            else:  # espelho
                w = x.pai.esquerda
                if w.cor == VERMELHO:
                    w.cor = PRETO
                    x.pai.cor = VERMELHO
                    self._rotacionar_direita(x.pai)
                    w = x.pai.esquerda
                if w.direita.cor == PRETO and w.esquerda.cor == PRETO:
                    w.cor = VERMELHO
                    x = x.pai
                else:
                    if w.esquerda.cor == PRETO:
                        w.direita.cor = PRETO
                        w.cor = VERMELHO
                        self._rotacionar_esquerda(w)
                        w = x.pai.esquerda
                    w.cor = x.pai.cor
                    x.pai.cor = PRETO
                    w.esquerda.cor = PRETO
                    self._rotacionar_direita(x.pai)
                    x = self.raiz
        x.cor = PRETO

    # ------------------------------------------------------------------ #
    # Consultas
    # ------------------------------------------------------------------ #
    def _buscar_no(self, chave):
        no = self.raiz
        while no is not self.NIL:
            if chave < no.chave:
                no = no.esquerda
            elif chave > no.chave:
                no = no.direita
            else:
                return no
        return self.NIL

    def buscar(self, chave, padrao=None):
        no = self._buscar_no(chave)
        return padrao if no is self.NIL else no.valor

    def contem(self, chave):
        return self._buscar_no(chave) is not self.NIL

    def em_ordem(self):
        """Gera (chave, valor) em ordem crescente de chave."""
        yield from self._percorrer_a_partir_de(None)

    def _percorrer_a_partir_de(self, inicio):
        """Percurso em-ordem começando na primeira chave >= inicio
        (ou na menor chave, se inicio for None). Custo O(log n + k)."""
        pilha, no = [], self.raiz
        # Desce até o ponto de partida, empilhando só os nós >= inicio
        while no is not self.NIL:
            if inicio is None or not (no.chave < inicio):
                pilha.append(no)
                no = no.esquerda
            else:
                no = no.direita
        while pilha:
            no = pilha.pop()
            yield no.chave, no.valor
            no = no.direita
            while no is not self.NIL:
                pilha.append(no)
                no = no.esquerda

    def proximos(self, inicio, quantidade=None):
        """Os `quantidade` primeiros (chave, valor) com chave >= inicio.
        Ex.: próximos atendimentos a partir de agora."""
        resultado = []
        for item in self._percorrer_a_partir_de(inicio):
            if quantidade is not None and len(resultado) >= quantidade:
                break
            resultado.append(item)
        return resultado

    def intervalo(self, inicio, fim):
        """Lista (chave, valor) com inicio <= chave <= fim, em ordem."""
        resultado = []
        for chave, valor in self._percorrer_a_partir_de(inicio):
            if chave > fim:
                break
            resultado.append((chave, valor))
        return resultado

    def filtrar(self, predicado):
        return [(k, v) for k, v in self.em_ordem() if predicado(v)]

    def minimo(self):
        if self.raiz is self.NIL:
            return None
        no = self._minimo_no(self.raiz)
        return no.chave, no.valor

    def maximo(self):
        if self.raiz is self.NIL:
            return None
        no = self.raiz
        while no.direita is not self.NIL:
            no = no.direita
        return no.chave, no.valor

    def altura(self):
        def h(no):
            return 0 if no is self.NIL else 1 + max(h(no.esquerda), h(no.direita))
        return h(self.raiz)

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
        no = self._buscar_no(chave)
        if no is self.NIL:
            raise KeyError(chave)
        return no.valor

    # ------------------------------------------------------------------ #
    # Depuração / apresentação
    # ------------------------------------------------------------------ #
    def desenhar(self, formatar=str):
        """Desenho textual (deitada: raiz à esquerda, direita em cima).
        `formatar` converte a chave em texto (útil para datas)."""
        linhas = []

        def rotulo(no):
            return f"{formatar(no.chave)} [{'V' if no.cor == VERMELHO else 'P'}]"

        def visitar(no, prefixo, eh_direita):
            if no is self.NIL:
                return
            visitar(no.direita, prefixo + ("    " if eh_direita else "│   "), True)
            linhas.append(prefixo + ("┌── " if eh_direita else "└── ") + rotulo(no))
            visitar(no.esquerda, prefixo + ("│   " if eh_direita else "    "), False)

        if self.raiz is not self.NIL:
            visitar(self.raiz.direita, "", True)
            linhas.append(rotulo(self.raiz))
            visitar(self.raiz.esquerda, "", False)
        return "\n".join(linhas) if linhas else "(árvore vazia)"

    def validar(self):
        """Verifica as 5 propriedades + ordem + ponteiros de pai."""
        assert self.NIL.cor == PRETO, "NIL deve ser preto"
        assert self.raiz.cor == PRETO, "raiz deve ser preta"

        def checar(no, minimo, maximo):
            """Retorna (altura negra, quantidade de nós)."""
            if no is self.NIL:
                return 1, 0
            assert minimo is None or no.chave > minimo, f"ordem violada em {no.chave}"
            assert maximo is None or no.chave < maximo, f"ordem violada em {no.chave}"
            for filho in (no.esquerda, no.direita):
                if filho is not self.NIL:
                    assert filho.pai is no, f"ponteiro pai errado em {filho.chave}"
                if no.cor == VERMELHO:
                    assert filho.cor == PRETO, f"vermelho com filho vermelho em {no.chave}"
            ne, qe = checar(no.esquerda, minimo, no.chave)
            nd, qd = checar(no.direita, no.chave, maximo)
            assert ne == nd, f"altura negra diferente em {no.chave}"
            return ne + (1 if no.cor == PRETO else 0), 1 + qe + qd

        _, quantidade = checar(self.raiz, None, None)
        assert quantidade == self._tamanho, "tamanho inconsistente"
        return True
