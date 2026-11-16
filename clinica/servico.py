"""
Serviço da clínica: junta as árvores (índices) e aplica as regras de negócio.

Índices de pacientes (AVL, muito lidos e pouco alterados):
    _por_cpf          cpf                    -> Paciente
    _por_prontuario   prontuario             -> Paciente
    _por_nome         (nome_normalizado, cpf) -> Paciente

Índices da agenda (Rubro-Negra, alterados com frequência):
    _agenda_horario       (data_hora, id)                -> Agendamento
    _agenda_id            id                             -> Agendamento
    _agenda_profissional  (profissional, data_hora, id)  -> Agendamento
    _agenda_paciente      (cpf, data_hora, id)           -> Agendamento

Todos os índices apontam para o MESMO objeto, então não há dados duplicados,
só referências. Toda alteração precisa manter os índices sincronizados.

Truque das chaves em tupla: em Python, (a,) < (a, b) para qualquer b. Assim
(cpf,) é um limite inferior de todas as chaves (cpf, ...), e
(cpf, datetime.max) é um limite superior.
"""
from datetime import date, datetime, timedelta

from .arvores import ArvoreAVL, ArvoreRubroNegra
from .erros import (AgendamentoNaoEncontrado, ConflitoDeHorario, DadosInvalidos,
                    PacienteJaCadastrado, PacienteNaoEncontrado)
from .modelos import (DURACAO_MAXIMA, Agendamento, Paciente, _validar_data_hora,
                      _validar_data_nascimento, _validar_duracao, _validar_email,
                      _validar_nome, _validar_telefone, normalizar_texto, somente_digitos,
                      validar_cpf)

_CAMPOS_EDITAVEIS = {"nome", "data_nascimento", "telefone", "email", "convenio"}


class Clinica:
    def __init__(self, relogio=datetime.now):
        """`relogio` devolve o "agora". Nos testes passamos um relógio fixo."""
        self._relogio = relogio

        self._por_cpf = ArvoreAVL()
        self._por_prontuario = ArvoreAVL()
        self._por_nome = ArvoreAVL()

        self._agenda_horario = ArvoreRubroNegra()
        self._agenda_id = ArvoreRubroNegra()
        self._agenda_profissional = ArvoreRubroNegra()
        self._agenda_paciente = ArvoreRubroNegra()

        self._proximo_prontuario = 1
        self._proximo_id_agendamento = 1

    def agora(self):
        return self._relogio().replace(second=0, microsecond=0)

    # ================================================================== #
    # PACIENTES
    # ================================================================== #
    def cadastrar_paciente(self, cpf, nome, data_nascimento, telefone="", email="",
                           convenio="", prontuario=None):
        cpf = validar_cpf(cpf)
        if cpf in self._por_cpf:
            raise PacienteJaCadastrado(f"Já existe paciente com CPF {cpf}.")
        if prontuario is None:
            prontuario = self._proximo_prontuario
        elif prontuario in self._por_prontuario:
            raise PacienteJaCadastrado(f"Prontuário {prontuario} já está em uso.")

        paciente = Paciente(
            prontuario=prontuario,
            cpf=cpf,
            nome=_validar_nome(nome),
            data_nascimento=_validar_data_nascimento(data_nascimento, self.agora().date()),
            telefone=_validar_telefone(telefone),
            email=_validar_email(email),
            convenio=" ".join(str(convenio or "").split()),
        )
        self._por_cpf.inserir(paciente.cpf, paciente)
        self._por_prontuario.inserir(paciente.prontuario, paciente)
        self._por_nome.inserir(paciente.chave_nome, paciente)
        self._proximo_prontuario = max(self._proximo_prontuario, prontuario + 1)
        return paciente

    def atualizar_paciente(self, cpf, **campos):
        """Atualiza nome, data_nascimento, telefone, email e/ou convenio.
        CPF e prontuário são identificadores e não podem ser alterados."""
        paciente = self.buscar_por_cpf(cpf)
        invalidos = set(campos) - _CAMPOS_EDITAVEIS
        if invalidos:
            raise DadosInvalidos(f"Campos não editáveis: {', '.join(sorted(invalidos))}")

        # valida tudo antes de alterar qualquer coisa
        novos = {}
        if "nome" in campos:
            novos["nome"] = _validar_nome(campos["nome"])
        if "data_nascimento" in campos:
            novos["data_nascimento"] = _validar_data_nascimento(
                campos["data_nascimento"], self.agora().date())
        if "telefone" in campos:
            novos["telefone"] = _validar_telefone(campos["telefone"])
        if "email" in campos:
            novos["email"] = _validar_email(campos["email"])
        if "convenio" in campos:
            novos["convenio"] = " ".join(str(campos["convenio"] or "").split())

        # o nome faz parte da chave do índice alfabético: remove e reinsere
        chave_antiga = paciente.chave_nome
        for campo, valor in novos.items():
            setattr(paciente, campo, valor)
        if paciente.chave_nome != chave_antiga:
            self._por_nome.remover(chave_antiga)
            self._por_nome.inserir(paciente.chave_nome, paciente)
        return paciente

    def remover_paciente(self, cpf):
        """Remove o paciente e cancela todos os seus agendamentos.
        Retorna (paciente, lista de agendamentos cancelados)."""
        paciente = self.buscar_por_cpf(cpf)
        cancelados = self.agendamentos_do_paciente(paciente.cpf)
        for agendamento in cancelados:
            self._desindexar_agendamento(agendamento)
        self._por_cpf.remover(paciente.cpf)
        self._por_prontuario.remover(paciente.prontuario)
        self._por_nome.remover(paciente.chave_nome)
        return paciente, cancelados

    # ---------------------------- consultas --------------------------- #
    def buscar_por_cpf(self, cpf):
        try:
            cpf_limpo = validar_cpf(cpf)
        except DadosInvalidos:
            raise PacienteNaoEncontrado(f"Paciente com CPF {cpf} não encontrado.")
        paciente = self._por_cpf.buscar(cpf_limpo)
        if paciente is None:
            raise PacienteNaoEncontrado(f"Paciente com CPF {cpf} não encontrado.")
        return paciente

    def buscar_por_prontuario(self, prontuario):
        paciente = self._por_prontuario.buscar(int(prontuario))
        if paciente is None:
            raise PacienteNaoEncontrado(f"Prontuário {prontuario} não encontrado.")
        return paciente

    def listar_alfabetico(self):
        return [p for _, p in self._por_nome.em_ordem()]

    def listar_por_prontuario(self):
        return [p for _, p in self._por_prontuario.em_ordem()]

    def buscar_por_nome(self, prefixo):
        """Pacientes cujo nome começa com `prefixo` (sem diferenciar acentos e
        maiúsculas), em ordem alfabética. Usa busca por intervalo na AVL:
        tudo entre (prefixo,) e (prefixo + '\\uffff',)."""
        p = normalizar_texto(prefixo)
        if not p:
            return self.listar_alfabetico()
        return [pac for _, pac in self._por_nome.intervalo((p,), (p + "￿",))]

    def pacientes_por_intervalo_prontuario(self, inicio, fim):
        return [p for _, p in self._por_prontuario.intervalo(int(inicio), int(fim))]

    def pacientes_por_intervalo_cpf(self, inicio, fim):
        """Intervalo de CPFs. Aceita CPFs parciais/formatados: '123' vira
        '12300000000' no início e '12399999999' no fim."""
        ini = (somente_digitos(inicio) + "0" * 11)[:11]
        fim_ = (somente_digitos(fim) + "9" * 11)[:11]
        return [p for _, p in self._por_cpf.intervalo(ini, fim_)]

    def filtrar_pacientes(self, idade_min=None, idade_max=None, convenio=None,
                          nome_contem=None):
        """Localiza pacientes por critérios combinados (em ordem alfabética).
        Percorre a árvore toda: O(n)."""
        hoje = self.agora().date()
        conv = normalizar_texto(convenio) if convenio else None
        trecho = normalizar_texto(nome_contem) if nome_contem else None

        def atende(p):
            idade = p.idade(hoje)
            return ((idade_min is None or idade >= idade_min)
                    and (idade_max is None or idade <= idade_max)
                    and (conv is None or normalizar_texto(p.convenio) == conv)
                    and (trecho is None or trecho in normalizar_texto(p.nome)))

        return [p for _, p in self._por_nome.filtrar(atende)]

    def total_pacientes(self):
        return len(self._por_cpf)

    # ================================================================== #
    # AGENDAMENTOS
    # ================================================================== #
    def agendar(self, cpf, data_hora, profissional, duracao_min=30, observacao="",
                permitir_passado=False):
        paciente = self.buscar_por_cpf(cpf)
        data_hora = _validar_data_hora(data_hora)
        duracao_min = _validar_duracao(duracao_min)
        profissional = _validar_nome(profissional, "Profissional")
        if not permitir_passado and data_hora < self.agora():
            raise DadosInvalidos("Não é possível agendar no passado.")

        agendamento = Agendamento(
            id=self._proximo_id_agendamento,
            cpf_paciente=paciente.cpf,
            profissional=profissional,
            data_hora=data_hora,
            duracao_min=duracao_min,
            observacao=str(observacao or "").strip(),
        )
        self._verificar_conflitos(agendamento)
        self._indexar_agendamento(agendamento)
        self._proximo_id_agendamento += 1
        return agendamento

    def cancelar_agendamento(self, id_agendamento):
        agendamento = self.buscar_agendamento(id_agendamento)
        self._desindexar_agendamento(agendamento)
        return agendamento

    def remarcar(self, id_agendamento, nova_data_hora, nova_duracao=None):
        agendamento = self.buscar_agendamento(id_agendamento)
        nova_data_hora = _validar_data_hora(nova_data_hora)
        duracao = agendamento.duracao_min if nova_duracao is None else _validar_duracao(nova_duracao)
        if nova_data_hora < self.agora():
            raise DadosInvalidos("Não é possível remarcar para o passado.")

        # simula o agendamento novo para checar conflitos (ignorando ele mesmo)
        candidato = Agendamento(agendamento.id, agendamento.cpf_paciente,
                                agendamento.profissional, nova_data_hora, duracao,
                                agendamento.observacao)
        self._verificar_conflitos(candidato, ignorar_id=agendamento.id)

        # a data faz parte das chaves: remove dos índices, altera e reinsere
        self._desindexar_agendamento(agendamento)
        agendamento.data_hora = nova_data_hora
        agendamento.duracao_min = duracao
        self._indexar_agendamento(agendamento)
        return agendamento

    # ---------------------------- consultas --------------------------- #
    def buscar_agendamento(self, id_agendamento):
        agendamento = self._agenda_id.buscar(int(id_agendamento))
        if agendamento is None:
            raise AgendamentoNaoEncontrado(f"Agendamento {id_agendamento} não encontrado.")
        return agendamento

    def proximos_atendimentos(self, quantidade=10, a_partir_de=None, profissional=None):
        """Os próximos `quantidade` atendimentos a partir de agora (ou de
        `a_partir_de`). Custo O(log n + k): não percorre a agenda toda."""
        inicio = _validar_data_hora(a_partir_de) if a_partir_de else self.agora()
        if profissional is None:
            return [ag for _, ag in self._agenda_horario.proximos((inicio,), quantidade)]
        prof = normalizar_texto(profissional)
        itens = self._agenda_profissional.proximos((prof, inicio), quantidade)
        # depois do último atendimento deste profissional vêm os do próximo
        return [ag for chave, ag in itens if chave[0] == prof]

    def agendamentos_no_intervalo(self, inicio, fim):
        """Agendamentos que COMEÇAM em [inicio, fim). O limite superior (fim,)
        é menor que qualquer (fim, id), então quem começa em `fim` fica de fora."""
        inicio, fim = _validar_data_hora(inicio), _validar_data_hora(fim)
        return [ag for _, ag in self._agenda_horario.intervalo((inicio,), (fim,))]

    def agenda_do_dia(self, dia=None, profissional=None):
        dia = dia or self.agora().date()
        if isinstance(dia, str):
            dia = date.fromisoformat(dia)
        inicio = datetime.combine(dia, datetime.min.time())
        if profissional is None:
            return self.agendamentos_no_intervalo(inicio, inicio + timedelta(days=1))
        prof = normalizar_texto(profissional)
        fim = inicio + timedelta(days=1)
        return [ag for _, ag in self._agenda_profissional.intervalo((prof, inicio), (prof, fim))]

    def agendamentos_do_paciente(self, cpf, somente_futuros=False):
        cpf = self.buscar_por_cpf(cpf).cpf
        inicio = (cpf, self.agora()) if somente_futuros else (cpf,)
        return [ag for _, ag in self._agenda_paciente.intervalo(inicio, (cpf, datetime.max))]

    def listar_agendamentos(self):
        return [ag for _, ag in self._agenda_horario.em_ordem()]

    def listar_profissionais(self):
        """Nomes distintos de profissionais, em ordem alfabética."""
        vistos = {}
        for (prof, _, _), ag in self._agenda_profissional.em_ordem():
            vistos.setdefault(prof, ag.profissional)
        return list(vistos.values())

    def total_agendamentos(self):
        return len(self._agenda_id)

    # ================================================================== #
    # Estatísticas das árvores (para a apresentação / front-end)
    # ================================================================== #
    def arvores(self):
        return {
            "Pacientes por CPF": self._por_cpf,
            "Pacientes por prontuário": self._por_prontuario,
            "Pacientes por nome": self._por_nome,
            "Agenda por horário": self._agenda_horario,
            "Agenda por id": self._agenda_id,
            "Agenda por profissional": self._agenda_profissional,
            "Agenda por paciente": self._agenda_paciente,
        }

    def estatisticas(self):
        return [
            {"indice": nome,
             "tipo": "AVL" if isinstance(arv, ArvoreAVL) else "Rubro-Negra",
             "tamanho": len(arv), "altura": arv.altura(), "rotacoes": arv.rotacoes}
            for nome, arv in self.arvores().items()
        ]

    def validar_indices(self):
        """Confere as propriedades de todas as árvores e a consistência entre elas."""
        for arv in self.arvores().values():
            arv.validar()
        n_pac, n_ag = len(self._por_cpf), len(self._agenda_id)
        assert len(self._por_prontuario) == len(self._por_nome) == n_pac
        assert (len(self._agenda_horario) == len(self._agenda_profissional)
                == len(self._agenda_paciente) == n_ag)
        return True

    # ================================================================== #
    # Internos
    # ================================================================== #
    def _indexar_agendamento(self, ag):
        self._agenda_horario.inserir(ag.chave_horario, ag)
        self._agenda_id.inserir(ag.id, ag)
        self._agenda_profissional.inserir(ag.chave_profissional, ag)
        self._agenda_paciente.inserir(ag.chave_paciente, ag)

    def _desindexar_agendamento(self, ag):
        self._agenda_horario.remover(ag.chave_horario)
        self._agenda_id.remover(ag.id)
        self._agenda_profissional.remover(ag.chave_profissional)
        self._agenda_paciente.remover(ag.chave_paciente)

    def _verificar_conflitos(self, novo, ignorar_id=None):
        """Um profissional não atende dois pacientes ao mesmo tempo e um paciente
        não está em duas consultas ao mesmo tempo.

        Como nenhuma consulta dura mais que DURACAO_MAXIMA, só podem sobrepor
        `novo` as que começam em [início - DURACAO_MAXIMA, fim): uma busca por
        intervalo O(log n + k) em vez de varrer a agenda."""
        janela = novo.data_hora - timedelta(minutes=DURACAO_MAXIMA)
        verificacoes = (
            (self._agenda_profissional, normalizar_texto(novo.profissional),
             "O profissional {} já tem atendimento das {:%H:%M} às {:%H:%M} (#{})."),
            (self._agenda_paciente, novo.cpf_paciente,
             "O paciente já tem consulta das {1:%H:%M} às {2:%H:%M} (#{3})."),
        )
        for arvore, prefixo, mensagem in verificacoes:
            for _, ag in arvore.intervalo((prefixo, janela), (prefixo, novo.fim)):
                if ag.id != ignorar_id and ag.sobrepoe(novo.data_hora, novo.fim):
                    raise ConflitoDeHorario(
                        mensagem.format(ag.profissional, ag.data_hora, ag.fim, ag.id))
