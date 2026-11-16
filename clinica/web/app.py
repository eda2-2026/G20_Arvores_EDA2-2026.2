"""
Front-end web (Flask).

Executar:  .venv/bin/python -m clinica.web           -> http://127.0.0.1:5000
           .venv/bin/python -m clinica.web --porta 8000 --arquivo outro.json

Páginas renderizadas no servidor (Jinja) para pacientes e agenda, e uma API
JSON pequena usada pela visualização das árvores e pelo laboratório.
O servidor roda em uma única thread (uso local), então não há acesso
concorrente às árvores.
"""
import os
import secrets
import time
from datetime import datetime, timedelta

from flask import (Flask, abort, flash, jsonify, redirect, render_template, request,
                   url_for)

from .. import dados_exemplo, persistencia
from ..arvores import ArvoreAVL, ArvoreRubroNegra
from ..cli import CAMINHO_PADRAO, formatar_chave
from ..erros import ErroClinica, PacienteNaoEncontrado
from ..modelos import DURACAO_MAXIMA, converter_data, formatar_cpf, somente_digitos

# slug da URL -> nome do índice em Clinica.arvores()
INDICES = {
    "cpf": "Pacientes por CPF",
    "prontuario": "Pacientes por prontuário",
    "nome": "Pacientes por nome",
    "agenda-horario": "Agenda por horário",
    "agenda-id": "Agenda por id",
    "agenda-profissional": "Agenda por profissional",
    "agenda-paciente": "Agenda por paciente",
}

LIMITE_LAB = 63  # nós no laboratório (cabe bem na tela)


def create_app(caminho=CAMINHO_PADRAO, relogio=datetime.now, clinica=None):
    app = Flask(__name__)
    app.secret_key = os.environ.get("CLINICA_SECRET_KEY") or secrets.token_hex(16)

    estado = {
        "clinica": clinica if clinica is not None else persistencia.carregar(caminho, relogio),
        "lab": {"avl": ArvoreAVL(), "rn": ArvoreRubroNegra()},
    }

    def c():
        return estado["clinica"]

    def salvar():
        if caminho:
            persistencia.salvar(c(), caminho)

    def medir(funcao, *args, **kwargs):
        """Executa a operação e devolve (resultado, tempo em microssegundos)."""
        inicio = time.perf_counter_ns()
        resultado = funcao(*args, **kwargs)
        return resultado, (time.perf_counter_ns() - inicio) / 1000

    # ------------------------------------------------------------------ #
    # Filtros e variáveis disponíveis em todos os templates
    # ------------------------------------------------------------------ #
    app.add_template_filter(formatar_cpf, "cpf")
    app.add_template_filter(lambda d: f"{d:%d/%m/%Y}" if d else "", "data")
    app.add_template_filter(lambda d: f"{d:%H:%M}" if d else "", "hora")

    @app.context_processor
    def globais():
        def paciente_de(ag):
            try:
                return c().buscar_por_cpf(ag.cpf_paciente)
            except PacienteNaoEncontrado:
                return None
        return {"agora": c().agora(), "hoje": c().agora().date(),
                "paciente_de": paciente_de, "INDICES": INDICES}

    # ================================================================== #
    # Painel
    # ================================================================== #
    @app.get("/")
    def painel():
        return render_template(
            "painel.html",
            total_pacientes=c().total_pacientes(),
            total_agendamentos=c().total_agendamentos(),
            proximos=c().proximos_atendimentos(8),
            hoje_lista=c().agenda_do_dia(),
            estatisticas=c().estatisticas(),
        )

    @app.post("/exemplo")
    def gerar_exemplo():
        n_pac = request.form.get("pacientes", 30, type=int)
        n_ag = request.form.get("agendamentos", 60, type=int)
        n_pac, n_ag = max(0, min(n_pac, 2000)), max(0, min(n_ag, 4000))
        pacientes, agendamentos = dados_exemplo.popular(c(), n_pac, n_ag)
        salvar()
        flash(f"{len(pacientes)} pacientes e {len(agendamentos)} agendamentos criados.", "ok")
        return redirect(url_for("painel"))

    # ================================================================== #
    # Pacientes
    # ================================================================== #
    @app.get("/pacientes")
    def pacientes():
        """Uma página, vários modos de busca. Cada modo mostra qual operação
        de árvore foi usada, sua complexidade e o tempo medido."""
        modo = request.args.get("modo", "alfabetica")
        a = request.args
        resultado, operacao, tempo = [], "", None
        try:
            if modo == "nome":
                resultado, tempo = medir(c().buscar_por_nome, a.get("q", ""))
                operacao = "AVL por nome → intervalo((prefixo,), (prefixo+'\\uffff',)) — O(log n + k)"
            elif modo == "cpf":
                paciente, tempo = medir(c().buscar_por_cpf, a.get("q", ""))
                resultado, operacao = [paciente], "AVL por CPF → buscar(cpf) — O(log n)"
            elif modo == "prontuario":
                paciente, tempo = medir(c().buscar_por_prontuario, _int(a.get("q")))
                resultado, operacao = [paciente], "AVL por prontuário → buscar(n) — O(log n)"
            elif modo == "intervalo_prontuario":
                resultado, tempo = medir(c().pacientes_por_intervalo_prontuario,
                                         _int(a.get("inicio")), _int(a.get("fim")))
                operacao = "AVL por prontuário → intervalo(início, fim) — O(log n + k)"
            elif modo == "intervalo_cpf":
                resultado, tempo = medir(c().pacientes_por_intervalo_cpf,
                                         a.get("inicio", ""), a.get("fim", ""))
                operacao = "AVL por CPF → intervalo(início, fim) — O(log n + k)"
            elif modo == "criterios":
                resultado, tempo = medir(
                    c().filtrar_pacientes,
                    idade_min=_int(a.get("idade_min"), None),
                    idade_max=_int(a.get("idade_max"), None),
                    convenio=a.get("convenio") or None,
                    nome_contem=a.get("nome_contem") or None)
                operacao = "AVL por nome → percurso em ordem + filtro — O(n)"
            else:
                modo = "alfabetica"
                resultado, tempo = medir(c().listar_alfabetico)
                operacao = "AVL por nome → percurso em ordem — O(n)"
        except ErroClinica as erro:
            flash(str(erro), "erro")
            resultado = []
        convenios = sorted({p.convenio for p in c().listar_por_prontuario() if p.convenio})
        return render_template("pacientes.html", modo=modo, args=a, pacientes=resultado,
                               operacao=operacao, tempo=tempo, convenios=convenios)

    @app.route("/pacientes/novo", methods=["GET", "POST"])
    def novo_paciente():
        if request.method == "POST":
            f = request.form
            try:
                p = c().cadastrar_paciente(f.get("cpf"), f.get("nome"), f.get("data_nascimento"),
                                           f.get("telefone"), f.get("email"), f.get("convenio"))
            except ErroClinica as erro:
                flash(str(erro), "erro")
                return render_template("paciente_form.html", form=f, editar=False), 422
            salvar()
            flash(f"Paciente {p.nome} cadastrado (prontuário {p.prontuario}).", "ok")
            return redirect(url_for("ver_paciente", cpf=p.cpf))
        return render_template("paciente_form.html", form={}, editar=False)

    @app.get("/pacientes/<cpf>")
    def ver_paciente(cpf):
        p = _paciente_ou_404(cpf)
        return render_template("paciente.html", p=p,
                               agendamentos=c().agendamentos_do_paciente(p.cpf))

    @app.route("/pacientes/<cpf>/editar", methods=["GET", "POST"])
    def editar_paciente(cpf):
        p = _paciente_ou_404(cpf)
        if request.method == "POST":
            f = request.form
            try:
                c().atualizar_paciente(p.cpf, nome=f.get("nome"),
                                       data_nascimento=f.get("data_nascimento"),
                                       telefone=f.get("telefone"), email=f.get("email"),
                                       convenio=f.get("convenio"))
            except ErroClinica as erro:
                flash(str(erro), "erro")
                return render_template("paciente_form.html", form=f, editar=True, p=p), 422
            salvar()
            flash("Dados atualizados.", "ok")
            return redirect(url_for("ver_paciente", cpf=p.cpf))
        form = {"cpf": p.cpf_formatado, "nome": p.nome,
                "data_nascimento": p.data_nascimento.isoformat(), "telefone": p.telefone,
                "email": p.email, "convenio": p.convenio}
        return render_template("paciente_form.html", form=form, editar=True, p=p)

    @app.post("/pacientes/<cpf>/remover")
    def remover_paciente(cpf):
        p = _paciente_ou_404(cpf)
        _, cancelados = c().remover_paciente(p.cpf)
        salvar()
        extra = f" e {len(cancelados)} agendamento(s) cancelado(s)" if cancelados else ""
        flash(f"Paciente {p.nome} removido{extra}.", "ok")
        return redirect(url_for("pacientes"))

    def _paciente_ou_404(cpf):
        try:
            return c().buscar_por_cpf(cpf)
        except PacienteNaoEncontrado:
            abort(404)

    # ================================================================== #
    # Agenda
    # ================================================================== #
    @app.get("/agenda")
    def agenda():
        modo = request.args.get("modo", "proximos")
        a = request.args
        profissional = a.get("profissional") or None
        lista, operacao, tempo, navegacao = [], "", None, None
        try:
            if modo == "dia":
                dia = converter_data(a.get("dia") or "") or c().agora().date()
                lista, tempo = medir(c().agenda_do_dia, dia, profissional)
                navegacao = {"dia": dia, "anterior": dia - timedelta(days=1),
                             "seguinte": dia + timedelta(days=1)}
                operacao = ("RN por profissional" if profissional else "RN por horário") + \
                    " → intervalo(dia 00:00, dia+1 00:00) — O(log n + k)"
            elif modo == "intervalo":
                lista, tempo = medir(c().agendamentos_no_intervalo,
                                     _data_hora(a.get("inicio")), _data_hora(a.get("fim")))
                operacao = "RN por horário → intervalo(início, fim) — O(log n + k)"
            elif modo == "todos":
                lista, tempo = medir(c().listar_agendamentos)
                operacao = "RN por horário → percurso em ordem — O(n)"
            else:
                modo = "proximos"
                quantidade = max(1, _int(a.get("quantidade"), 10))
                lista, tempo = medir(c().proximos_atendimentos, quantidade,
                                     profissional=profissional)
                operacao = ("RN por profissional" if profissional else "RN por horário") + \
                    f" → proximos(agora, {quantidade}) — O(log n + k)"
        except ErroClinica as erro:
            flash(str(erro), "erro")
        return render_template("agenda.html", modo=modo, args=a, agendamentos=lista,
                               operacao=operacao, tempo=tempo, navegacao=navegacao,
                               profissionais=c().listar_profissionais())

    @app.route("/agenda/novo", methods=["GET", "POST"])
    def novo_agendamento():
        if request.method == "POST":
            f = request.form
            try:
                ag = c().agendar(f.get("cpf"), f"{f.get('data')} {f.get('hora')}",
                                 f.get("profissional"), f.get("duracao_min", 30),
                                 f.get("observacao"))
            except ErroClinica as erro:
                flash(str(erro), "erro")
                return _form_agendamento(f), 422
            salvar()
            flash(f"Agendamento #{ag.id} criado: {ag.data_hora:%d/%m/%Y %H:%M}.", "ok")
            return redirect(url_for("agenda", modo="dia", dia=ag.data_hora.date().isoformat()))
        form = {"cpf": request.args.get("cpf", ""), "data": c().agora().date().isoformat(),
                "hora": "", "duracao_min": 30}
        return _form_agendamento(form)

    def _form_agendamento(form, ag=None):
        return render_template("agendamento_form.html", form=form, ag=ag,
                               pacientes=c().listar_alfabetico(),
                               profissionais=c().listar_profissionais(),
                               duracao_maxima=DURACAO_MAXIMA)

    @app.route("/agenda/<int:id_ag>/remarcar", methods=["GET", "POST"])
    def remarcar(id_ag):
        ag = _agendamento_ou_404(id_ag)
        if request.method == "POST":
            f = request.form
            try:
                c().remarcar(ag.id, f"{f.get('data')} {f.get('hora')}", f.get("duracao_min"))
            except ErroClinica as erro:
                flash(str(erro), "erro")
                return _form_agendamento(f, ag), 422
            salvar()
            flash(f"Agendamento #{ag.id} remarcado para {ag.data_hora:%d/%m/%Y %H:%M}.", "ok")
            return redirect(url_for("agenda", modo="dia", dia=ag.data_hora.date().isoformat()))
        form = {"cpf": ag.cpf_paciente, "data": ag.data_hora.date().isoformat(),
                "hora": f"{ag.data_hora:%H:%M}", "duracao_min": ag.duracao_min,
                "profissional": ag.profissional, "observacao": ag.observacao}
        return _form_agendamento(form, ag)

    @app.post("/agenda/<int:id_ag>/cancelar")
    def cancelar(id_ag):
        ag = _agendamento_ou_404(id_ag)
        c().cancelar_agendamento(ag.id)
        salvar()
        flash(f"Agendamento #{ag.id} cancelado.", "ok")
        return redirect(request.form.get("voltar") or url_for("agenda"))

    def _agendamento_ou_404(id_ag):
        try:
            return c().buscar_agendamento(id_ag)
        except ErroClinica:
            abort(404)

    # ================================================================== #
    # Visualização das árvores
    # ================================================================== #
    @app.get("/arvores")
    def arvores():
        return render_template("arvores.html", estatisticas=c().estatisticas(),
                               selecionado=request.args.get("indice", "cpf"))

    @app.get("/api/arvores/<slug>")
    def api_arvore(slug):
        if slug not in INDICES:
            abort(404)
        arvore = c().arvores()[INDICES[slug]]
        # no índice por nome a chave é (nome, cpf); o CPF só desempata nomes
        # iguais, então o desenho mostra só o nome para não espalhar a árvore
        formatar = (lambda chave: chave[0]) if slug == "nome" else formatar_chave
        return jsonify(_dados_arvore(arvore, formatar))

    # ================================================================== #
    # Laboratório: árvores de inteiros para demonstrar as operações
    # ================================================================== #
    @app.get("/laboratorio")
    def laboratorio():
        return render_template("laboratorio.html", limite=LIMITE_LAB)

    @app.get("/api/lab/<tipo>")
    def api_lab_ver(tipo):
        return jsonify(_dados_arvore(_lab(tipo)))

    @app.post("/api/lab/<tipo>")
    def api_lab_acao(tipo):
        arvore = _lab(tipo)
        dados = request.get_json(silent=True) or {}
        acao = dados.get("acao")
        rotacoes_antes = arvore.rotacoes
        resposta = {"mensagem": "", "destaque": None, "caminho": [], "erro": False}

        def aviso(texto):
            resposta.update(mensagem=texto, erro=True)

        if acao in ("inserir", "remover", "buscar"):
            try:
                chave = int(dados.get("chave"))
            except (TypeError, ValueError):
                aviso("Digite um número inteiro.")
                return jsonify({**resposta, **_dados_arvore(arvore)})
            resposta["caminho"] = [str(k) for k in arvore.caminho_busca(chave)]
            if acao == "inserir":
                if len(arvore) >= LIMITE_LAB:
                    aviso(f"Limite de {LIMITE_LAB} nós no laboratório.")
                elif arvore.inserir(chave):
                    resposta.update(mensagem=f"{chave} inserido.", destaque=str(chave))
                else:
                    aviso(f"{chave} já está na árvore.")
            elif acao == "remover":
                try:
                    arvore.remover(chave)
                    resposta["mensagem"] = f"{chave} removido."
                except KeyError:
                    aviso(f"{chave} não está na árvore.")
            else:
                encontrado = chave in arvore
                resposta.update(
                    mensagem=f"{chave} {'encontrado' if encontrado else 'não encontrado'} "
                             f"após visitar {len(resposta['caminho'])} nó(s).",
                    destaque=str(chave) if encontrado else None, erro=not encontrado)
        elif acao == "carregar":
            # recomeça a árvore e insere a lista na ordem dada (o front manda a
            # mesma lista para a AVL e para a Rubro-Negra, para comparar)
            try:
                chaves = [int(k) for k in dados.get("chaves", [])][:LIMITE_LAB]
            except (TypeError, ValueError):
                abort(400)
            _limpar_lab(tipo)
            arvore = _lab(tipo)
            rotacoes_antes = 0
            inseridas = [k for k in chaves if arvore.inserir(k)]
            resposta["mensagem"] = f"{len(inseridas)} valores inseridos em sequência."
        elif acao == "limpar":
            _limpar_lab(tipo)
            arvore = _lab(tipo)
            rotacoes_antes = 0
            resposta["mensagem"] = "Árvore vazia."
        else:
            abort(400)

        resposta["rotacoes_operacao"] = arvore.rotacoes - rotacoes_antes
        return jsonify({**resposta, **_dados_arvore(arvore)})

    def _lab(tipo):
        if tipo not in estado["lab"]:
            abort(404)
        return estado["lab"][tipo]

    def _limpar_lab(tipo):
        estado["lab"][tipo] = ArvoreAVL() if tipo == "avl" else ArvoreRubroNegra()

    # ================================================================== #
    # Erros
    # ================================================================== #
    @app.errorhandler(404)
    def nao_encontrado(_erro):
        if request.path.startswith("/api/"):
            return jsonify({"erro": "não encontrado"}), 404
        return render_template("404.html"), 404

    return app


# ---------------------------------------------------------------------- #
# Auxiliares
# ---------------------------------------------------------------------- #
def _dados_arvore(arvore, formatar=str):
    return {
        "tipo": "AVL" if isinstance(arvore, ArvoreAVL) else "Rubro-Negra",
        "tamanho": len(arvore),
        "altura": arvore.altura(),
        "rotacoes": arvore.rotacoes,
        "raiz": arvore.estrutura(formatar),
    }


def _int(texto, padrao=0):
    texto = somente_digitos(texto) if texto not in (None, "") else ""
    return int(texto) if texto else padrao


def _data_hora(texto):
    """Campo <input type="datetime-local"> -> texto aceito pelo serviço."""
    return (texto or "").replace("T", " ")



