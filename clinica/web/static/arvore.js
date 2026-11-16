/*
 * Desenho de árvores binárias em SVG.
 *
 * Layout: x = posição do nó no percurso em ordem, y = profundidade.
 * Como a árvore é de busca, isso já deixa as chaves ordenadas da esquerda
 * para a direita e garante que nenhum nó se sobreponha.
 *
 * Animação: cada nó é identificado pela chave. Ao redesenhar, os nós saem
 * da posição anterior e deslizam até a nova (CSS transition), assim dá para
 * "ver" as rotações acontecendo.
 */
(function () {
  "use strict";

  const SVG_NS = "http://www.w3.org/2000/svg";
  const ALTURA_NO = 30;
  const DIST_Y = 64;
  const MARGEM = 24;
  const LARGURA_CHAR = 7.4;

  function el(nome, atributos, pai) {
    const elemento = document.createElementNS(SVG_NS, nome);
    for (const [k, v] of Object.entries(atributos || {})) elemento.setAttribute(k, v);
    if (pai) pai.appendChild(elemento);
    return elemento;
  }

  function larguraRotulo(texto) {
    return Math.max(ALTURA_NO + 6, texto.length * LARGURA_CHAR + 18);
  }

  class DesenhoArvore {
    /** @param {HTMLElement} quadro  elemento que recebe o <svg> */
    constructor(quadro) {
      this.quadro = quadro;
      this.posicoes = new Map(); // chave -> {x, y} do último desenho
      this.zoom = 1;
    }

    /**
     * @param {object} dados  {tipo: "AVL"|"Rubro-Negra", raiz: {chave, esquerda, direita, ...}}
     * @param {object} opcoes {destaque: chave, caminho: [chaves], animar: bool}
     */
    desenhar(dados, opcoes = {}) {
      const { destaque = null, caminho = [], animar = true } = opcoes;
      const rubroNegra = dados.tipo === "Rubro-Negra";
      const noCaminho = new Set(caminho.map(String));

      // 0) id único por nó: normalmente a própria chave; se houver rótulos
      //    repetidos (ex.: índice por nome mostrando só o nome), acrescenta #n
      const vistos = new Map();
      (function nomear(no) {
        if (!no) return;
        const n = vistos.get(no.chave) || 0;
        vistos.set(no.chave, n + 1);
        no.id = n ? `${no.chave}#${n}` : String(no.chave);
        nomear(no.esquerda);
        nomear(no.direita);
      })(dados.raiz);

      // 1) layout
      const nos = [];
      let maiorLargura = ALTURA_NO + 6;
      let profundidadeMax = 0;
      (function emOrdem(no, profundidade, pai) {
        if (!no) return;
        emOrdem(no.esquerda, profundidade + 1, no);
        const largura = larguraRotulo(no.chave);
        maiorLargura = Math.max(maiorLargura, largura);
        profundidadeMax = Math.max(profundidadeMax, profundidade);
        nos.push({ no, profundidade, pai: pai ? pai.id : null, largura, indice: nos.length });
        emOrdem(no.direita, profundidade + 1, no);
      })(dados.raiz, 0, null);

      const distX = maiorLargura + 8;
      const posicao = new Map();
      for (const item of nos) {
        posicao.set(item.no.id, {
          x: MARGEM + maiorLargura / 2 + item.indice * distX,
          y: MARGEM + ALTURA_NO / 2 + item.profundidade * DIST_Y,
        });
      }
      const larguraTotal = Math.max(2 * MARGEM + maiorLargura + (nos.length - 1) * distX, 200);
      const alturaTotal = 2 * MARGEM + ALTURA_NO + profundidadeMax * DIST_Y + (rubroNegra ? 0 : 14);

      // 2) svg
      this.quadro.replaceChildren();
      if (!nos.length) {
        const vazio = document.createElement("p");
        vazio.className = "arvore-vazia";
        vazio.textContent = "Árvore vazia";
        this.quadro.appendChild(vazio);
        this.posicoes = new Map();
        return;
      }
      const svg = el("svg", {
        viewBox: `0 0 ${larguraTotal} ${alturaTotal}`,
        class: "arvore-svg" + (rubroNegra ? " arvore-rn" : " arvore-avl"),
        role: "img",
        "aria-label": `${dados.tipo} com ${nos.length} nós`,
      }, this.quadro);
      this.larguraNatural = larguraTotal;
      this.svg = svg;
      this.aplicarZoom();

      // 3) arestas (desenhadas primeiro para ficarem por baixo dos nós)
      const grupoArestas = el("g", { class: "arestas" + (animar && this.posicoes.size ? " aparecer" : "") }, svg);
      for (const item of nos) {
        if (item.pai === null) continue;
        const a = posicao.get(item.pai);
        const b = posicao.get(item.no.id);
        const noTrajeto = noCaminho.has(String(item.pai)) && noCaminho.has(String(item.no.chave));
        el("line", { x1: a.x, y1: a.y, x2: b.x, y2: b.y, class: noTrajeto ? "aresta trajeto" : "aresta" }, grupoArestas);
      }

      // 4) nós
      const grupoNos = el("g", { class: "nos" }, svg);
      const animacoes = [];
      for (const item of nos) {
        const { no, largura } = item;
        const destino = posicao.get(no.id);
        const origem = this.posicoes.get(no.id)
          || (item.pai !== null && this.posicoes.get(item.pai))
          || destino;

        const classes = ["no"];
        if (rubroNegra) classes.push(no.cor === "vermelho" ? "no-vermelho" : "no-preto");
        else if (Math.abs(no.fb) === 1) classes.push("no-inclinado");
        if (noCaminho.has(String(no.chave))) classes.push("no-trajeto");
        if (destaque !== null && String(no.chave) === String(destaque)) classes.push("no-destaque");
        if (!this.posicoes.has(no.id) && this.posicoes.size) classes.push("no-novo");

        const g = el("g", { class: classes.join(" ") }, grupoNos);
        g.style.transform = `translate(${origem.x}px, ${origem.y}px)`;
        el("rect", { x: -largura / 2, y: -ALTURA_NO / 2, width: largura, height: ALTURA_NO, rx: ALTURA_NO / 2 }, g);
        const texto = el("text", { "text-anchor": "middle", dy: "0.35em", class: "rotulo-no" }, g);
        texto.textContent = no.chave;

        const titulo = el("title", {}, g);
        if (rubroNegra) {
          titulo.textContent = `${no.chave}\ncor: ${no.cor}`;
        } else {
          titulo.textContent = `${no.chave}\naltura: ${no.altura}\nfator de balanceamento: ${no.fb}`;
          const fb = el("text", { "text-anchor": "middle", y: ALTURA_NO / 2 + 12, class: "fb" }, g);
          fb.textContent = `fb ${no.fb > 0 ? "+" : ""}${no.fb}`;
        }
        animacoes.push([g, destino]);
      }

      // 5) dispara a animação no próximo quadro (depois do navegador "ver" a origem)
      const mover = () => {
        for (const [g, destino] of animacoes) g.style.transform = `translate(${destino.x}px, ${destino.y}px)`;
      };
      if (animar && this.posicoes.size) {
        svg.getBoundingClientRect(); // força o layout com as posições de origem
        requestAnimationFrame(() => requestAnimationFrame(mover));
      } else {
        svg.classList.add("sem-animacao");
        mover();
      }
      this.posicoes = posicao;
    }

    aplicarZoom() {
      if (this.svg) this.svg.style.width = `${Math.round(this.larguraNatural * this.zoom)}px`;
    }

    definirZoom(valor) {
      this.zoom = Math.min(2, Math.max(0.2, valor));
      this.aplicarZoom();
    }

    /** Zoom para caber na largura do quadro (no máximo 100%).
     *  `minimo` evita rótulos ilegíveis em árvores grandes (aí o quadro rola). */
    ajustar(minimo = 0.2) {
      if (!this.larguraNatural) return;
      const caber = (this.quadro.clientWidth - 8) / this.larguraNatural;
      this.definirZoom(Math.max(minimo, Math.min(1, caber)));
    }
  }

  window.DesenhoArvore = DesenhoArvore;
})();
