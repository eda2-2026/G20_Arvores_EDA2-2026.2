"""
Interface de linha de comando (menu no terminal) para testar o backend.

Executar:  python3 -m clinica            (dados em dados/clinica.json)
           python3 -m clinica --arquivo outro.json

Os dados são salvos automaticamente após cada alteração.
`entrada` e `saida` são injetáveis para permitir testes automatizados.
"""
import argparse
from datetime import datetime

from . import dados_exemplo, persistencia
from .erros import ErroClinica
from .modelos import formatar_cpf

CAMINHO_PADRAO = "dados/clinica.json"


def formatar_chave(chave):
    """Converte qualquer chave de índice em texto curto para o desenho."""
    if isinstance(chave, tuple):
        return " | ".join(formatar_chave(parte) for parte in chave)
    if isinstance(chave, datetime):
        return f"{chave:%d/%m %H:%M}"
    if isinstance(chave, str) and len(chave) == 11 and chave.isdigit():
        return formatar_cpf(chave)
    return str(chave)


class CLI:
    def __init__(self, clinica, caminho=None, entrada=input, saida=print):
        self.clinica = clinica
        self.caminho = caminho
        self.entrada = entrada
        self.saida = saida
        # (rótulo, função, altera_dados?)
        self.secoes = [
            ("PACIENTES", [
                ("Cadastrar paciente", self.cadastrar_paciente, True),
                ("Buscar por CPF", self.buscar_cpf, False),
                ("Buscar por prontuário", self.buscar_prontuario, False),
                ("Listar em ordem alfabética", self.listar_alfabetico, False),
                ("Buscar por nome (início do nome)", self.buscar_nome, False),
                ("Intervalo de prontuários", self.intervalo_prontuario, False),
                ("Intervalo de CPFs", self.intervalo_cpf, False),
                ("Filtrar por critérios (idade, convênio, nome)", self.filtrar, False),
                ("Atualizar paciente", self.atualizar_paciente, True),
                ("Remover paciente", self.remover_paciente, True),
            ]),
            ("AGENDA", [
                ("Agendar consulta", self.agendar, True),
                ("Cancelar agendamento", self.cancelar, True),
                ("Remarcar agendamento", self.remarcar, True),
                ("Próximos atendimentos", self.proximos, False),
                ("Agenda do dia", self.agenda_do_dia, False),
                ("Agendamentos de um paciente", self.agendamentos_paciente, False),
            ]),
            ("SISTEMA", [
                ("Estatísticas das árvores", self.estatisticas, False),
                ("Desenhar uma árvore", self.desenhar, False),
                ("Gerar dados de exemplo", self.gerar_exemplo, True),
            ]),
        ]
        self.opcoes = {}
        numero = 1
        for _, itens in self.secoes:
            for rotulo, funcao, altera in itens:
                self.opcoes[str(numero)] = (rotulo, funcao, altera)
                numero += 1

    # ================================================================== #
    # Laço principal
    # ================================================================== #
    def executar(self):
        self.saida("=== Sistema de Pacientes e Agendamentos (AVL + Rubro-Negra) ===")
        self.saida(f"{self.clinica.total_pacientes()} pacientes, "
                   f"{self.clinica.total_agendamentos()} agendamentos carregados.")
        while True:
            self.mostrar_menu()
            try:
                opcao = self.ler("Opção").strip()
            except (EOFError, KeyboardInterrupt):
                opcao = "0"
            if opcao == "0":
                self.salvar()
                self.saida("Até logo!")
                return
            if opcao not in self.opcoes:
                self.saida("Opção inválida.")
                continue
            rotulo, funcao, altera = self.opcoes[opcao]
            self.saida(f"\n--- {rotulo} ---")
            try:
                if funcao() is not False and altera:
                    self.salvar()
            except ErroClinica as erro:
                self.saida(f"✘ {erro}")
            except (EOFError, KeyboardInterrupt):
                self.saida("\nOperação interrompida.")
            self.ler("\n[Enter para continuar]")

    def mostrar_menu(self):
        self.saida("")
        numero = 1
        for titulo, itens in self.secoes:
            self.saida(f"  {titulo}")
            for rotulo, _, _ in itens:
                self.saida(f"   {numero:>2}. {rotulo}")
                numero += 1
        self.saida("    0. Salvar e sair")

    def salvar(self):
        if self.caminho:
            persistencia.salvar(self.clinica, self.caminho)

    # ================================================================== #
    # Entrada
    # ================================================================== #
    def ler(self, rotulo, padrao=None):
        sufixo = f" [{padrao}]" if padrao not in (None, "") else ""
        valor = self.entrada(f"{rotulo}{sufixo}: ").strip()
        return valor if valor else (padrao if padrao is not None else "")

    def ler_int(self, rotulo, padrao=None, opcional=False):
        while True:
            texto = self.ler(rotulo, None if padrao is None else str(padrao))
            if texto == "" and opcional:
                return None
            try:
                return int(texto)
            except ValueError:
                self.saida("  Digite um número inteiro.")

    def confirmar(self, pergunta):
        return self.ler(f"{pergunta} (s/N)").lower() in ("s", "sim")

    # ================================================================== #
    # Saída
    # ================================================================== #
    def mostrar_pacientes(self, pacientes):
        if not pacientes:
            self.saida("Nenhum paciente encontrado.")
            return
        hoje = self.clinica.agora().date()
        self.saida(f"{'Pront.':>6}  {'Nome':<30} {'CPF':<15} {'Idade':>5}  Convênio")
        for p in pacientes:
            self.saida(f"{p.prontuario:>6}  {p.nome[:30]:<30} {p.cpf_formatado:<15} "
                       f"{p.idade(hoje):>5}  {p.convenio}")
        self.saida(f"({len(pacientes)} paciente(s))")

    def mostrar_paciente(self, p):
        self.saida(f"Prontuário: {p.prontuario}\nNome:       {p.nome}\n"
                   f"CPF:        {p.cpf_formatado}\n"
                   f"Nascimento: {p.data_nascimento:%d/%m/%Y} "
                   f"({p.idade(self.clinica.agora().date())} anos)\n"
                   f"Telefone:   {p.telefone or '-'}\nE-mail:     {p.email or '-'}\n"
                   f"Convênio:   {p.convenio or '-'}")

    def mostrar_agendamentos(self, agendamentos):
        if not agendamentos:
            self.saida("Nenhum agendamento encontrado.")
            return
        self.saida(f"{'Id':>4}  {'Data':<10} {'Horário':<11}  {'Profissional':<20} "
                   f"{'Paciente':<25} Obs.")
        for ag in agendamentos:
            paciente = self.clinica.buscar_por_cpf(ag.cpf_paciente)
            self.saida(f"{ag.id:>4}  {ag.data_hora:%d/%m/%Y} {ag.data_hora:%H:%M}-{ag.fim:%H:%M}  "
                       f"{ag.profissional[:20]:<20} {paciente.nome[:25]:<25} {ag.observacao}")
        self.saida(f"({len(agendamentos)} agendamento(s))")

    # ================================================================== #
    # Ações: pacientes
    # ================================================================== #
    def cadastrar_paciente(self):
        p = self.clinica.cadastrar_paciente(
            cpf=self.ler("CPF"),
            nome=self.ler("Nome"),
            data_nascimento=self.ler("Data de nascimento (DD/MM/AAAA)"),
            telefone=self.ler("Telefone (opcional)"),
            email=self.ler("E-mail (opcional)"),
            convenio=self.ler("Convênio (opcional)"),
        )
        self.saida(f"✔ Paciente cadastrado com prontuário {p.prontuario}.")

    def buscar_cpf(self):
        self.mostrar_paciente(self.clinica.buscar_por_cpf(self.ler("CPF")))

    def buscar_prontuario(self):
        self.mostrar_paciente(self.clinica.buscar_por_prontuario(self.ler_int("Prontuário")))

    def listar_alfabetico(self):
        self.mostrar_pacientes(self.clinica.listar_alfabetico())

    def buscar_nome(self):
        self.mostrar_pacientes(self.clinica.buscar_por_nome(self.ler("Início do nome")))

    def intervalo_prontuario(self):
        inicio = self.ler_int("Prontuário inicial")
        fim = self.ler_int("Prontuário final")
        self.mostrar_pacientes(self.clinica.pacientes_por_intervalo_prontuario(inicio, fim))

    def intervalo_cpf(self):
        self.saida("Dica: pode digitar só o começo do CPF (ex.: 123 até 456).")
        self.mostrar_pacientes(self.clinica.pacientes_por_intervalo_cpf(
            self.ler("CPF inicial"), self.ler("CPF final")))

    def filtrar(self):
        self.saida("Deixe em branco os critérios que não quiser usar.")
        self.mostrar_pacientes(self.clinica.filtrar_pacientes(
            idade_min=self.ler_int("Idade mínima", opcional=True),
            idade_max=self.ler_int("Idade máxima", opcional=True),
            convenio=self.ler("Convênio") or None,
            nome_contem=self.ler("Nome contém") or None,
        ))

    def atualizar_paciente(self):
        p = self.clinica.buscar_por_cpf(self.ler("CPF do paciente"))
        self.saida("Enter mantém o valor atual.")
        campos = {
            "nome": self.ler("Nome", p.nome),
            "data_nascimento": self.ler("Data de nascimento", f"{p.data_nascimento:%d/%m/%Y}"),
            "telefone": self.ler("Telefone", p.telefone),
            "email": self.ler("E-mail", p.email),
            "convenio": self.ler("Convênio", p.convenio),
        }
        self.clinica.atualizar_paciente(p.cpf, **campos)
        self.saida("✔ Paciente atualizado.")

    def remover_paciente(self):
        p = self.clinica.buscar_por_cpf(self.ler("CPF do paciente"))
        agendamentos = self.clinica.agendamentos_do_paciente(p.cpf)
        aviso = f" e seus {len(agendamentos)} agendamento(s)" if agendamentos else ""
        if not self.confirmar(f"Remover {p.nome}{aviso}?"):
            self.saida("Cancelado.")
            return False
        self.clinica.remover_paciente(p.cpf)
        self.saida("✔ Paciente removido.")

    # ================================================================== #
    # Ações: agenda
    # ================================================================== #
    def agendar(self):
        p = self.clinica.buscar_por_cpf(self.ler("CPF do paciente"))
        self.saida(f"Paciente: {p.nome}")
        profissionais = self.clinica.listar_profissionais()
        if profissionais:
            self.saida("Profissionais com agenda: " + ", ".join(profissionais))
        ag = self.clinica.agendar(
            cpf=p.cpf,
            data_hora=self.ler("Data e hora (DD/MM/AAAA HH:MM)"),
            profissional=self.ler("Profissional"),
            duracao_min=self.ler_int("Duração em minutos", 30),
            observacao=self.ler("Observação (opcional)"),
        )
        self.saida(f"✔ Agendamento #{ag.id}: {ag.data_hora:%d/%m/%Y %H:%M}-{ag.fim:%H:%M}.")

    def cancelar(self):
        ag = self.clinica.buscar_agendamento(self.ler_int("Id do agendamento"))
        self.mostrar_agendamentos([ag])
        if not self.confirmar("Cancelar este agendamento?"):
            self.saida("Mantido.")
            return False
        self.clinica.cancelar_agendamento(ag.id)
        self.saida("✔ Agendamento cancelado.")

    def remarcar(self):
        ag = self.clinica.buscar_agendamento(self.ler_int("Id do agendamento"))
        self.mostrar_agendamentos([ag])
        self.clinica.remarcar(ag.id, self.ler("Nova data e hora (DD/MM/AAAA HH:MM)"),
                              self.ler_int("Duração em minutos", ag.duracao_min))
        self.saida(f"✔ Remarcado para {ag.data_hora:%d/%m/%Y %H:%M}.")

    def proximos(self):
        quantidade = self.ler_int("Quantos", 10)
        profissional = self.ler("Profissional (em branco = todos)") or None
        self.mostrar_agendamentos(self.clinica.proximos_atendimentos(
            quantidade, profissional=profissional))

    def agenda_do_dia(self):
        dia = self.ler("Dia (DD/MM/AAAA)", f"{self.clinica.agora():%d/%m/%Y}")
        profissional = self.ler("Profissional (em branco = todos)") or None
        self.mostrar_agendamentos(self.clinica.agenda_do_dia(dia, profissional))

    def agendamentos_paciente(self):
        p = self.clinica.buscar_por_cpf(self.ler("CPF do paciente"))
        self.saida(f"Paciente: {p.nome}")
        self.mostrar_agendamentos(self.clinica.agendamentos_do_paciente(p.cpf))

    # ================================================================== #
    # Ações: sistema
    # ================================================================== #
    def estatisticas(self):
        self.saida(f"{'Índice':<26} {'Tipo':<12} {'Nós':>6} {'Altura':>7} {'Rotações':>9}")
        for s in self.clinica.estatisticas():
            self.saida(f"{s['indice']:<26} {s['tipo']:<12} {s['tamanho']:>6} "
                       f"{s['altura']:>7} {s['rotacoes']:>9}")
        self.saida("Rotações contam desde que os dados foram carregados.")

    def desenhar(self):
        arvores = list(self.clinica.arvores().items())
        for i, (nome, arvore) in enumerate(arvores, start=1):
            self.saida(f"  {i}. {nome} ({len(arvore)} nós)")
        escolha = self.ler_int("Qual árvore")
        if not 1 <= escolha <= len(arvores):
            self.saida("Opção inválida.")
            return
        nome, arvore = arvores[escolha - 1]
        if len(arvore) > 60 and not self.confirmar(f"A árvore tem {len(arvore)} nós. Desenhar?"):
            return
        legenda = "[V] vermelho, [P] preto" if "Agenda" in nome else "h = altura, fb = fator"
        self.saida(f"{nome} — {legenda}\n")
        self.saida(arvore.desenhar(formatar=formatar_chave))

    def gerar_exemplo(self):
        n_pac = self.ler_int("Quantos pacientes", 30)
        n_ag = self.ler_int("Quantos agendamentos", 60)
        pacientes, agendamentos = dados_exemplo.popular(self.clinica, n_pac, n_ag)
        self.saida(f"✔ {len(pacientes)} pacientes e {len(agendamentos)} agendamentos criados.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Sistema de pacientes e agendamentos.")
    parser.add_argument("--arquivo", default=CAMINHO_PADRAO,
                        help=f"arquivo JSON de dados (padrão: {CAMINHO_PADRAO})")
    args = parser.parse_args(argv)
    try:
        clinica = persistencia.carregar(args.arquivo)
    except ErroClinica as erro:
        print(f"✘ {erro}")
        return 1
    CLI(clinica, args.arquivo).executar()
    return 0
