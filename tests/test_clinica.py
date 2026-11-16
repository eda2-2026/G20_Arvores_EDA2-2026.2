import random
import unittest
from datetime import date, datetime, timedelta

from clinica.erros import (AgendamentoNaoEncontrado, ConflitoDeHorario, DadosInvalidos,
                           ErroClinica, PacienteJaCadastrado, PacienteNaoEncontrado)
from clinica.modelos import digitos_verificadores, formatar_cpf, normalizar_texto, validar_cpf
from clinica.servico import Clinica

AGORA = datetime(2026, 11, 16, 8, 0)


def cpf(n):
    """Gera um CPF válido a partir de um número (para os testes)."""
    base = f"{n:09d}"
    return base + digitos_verificadores(base)


class TestModelos(unittest.TestCase):
    def test_validar_cpf(self):
        self.assertEqual(validar_cpf("529.982.247-25"), "52998224725")
        self.assertEqual(validar_cpf(cpf(1)), cpf(1))  # zeros à esquerda preservados
        for invalido in ["529.982.247-24", "111.111.111-11", "123", "", None]:
            with self.assertRaises(DadosInvalidos):
                validar_cpf(invalido)

    def test_formatar_e_normalizar(self):
        self.assertEqual(formatar_cpf("52998224725"), "529.982.247-25")
        self.assertEqual(normalizar_texto("  JOSÉ  da   Conceição "), "jose da conceicao")

    def test_erros_herdam_de_erro_clinica(self):
        for erro in (DadosInvalidos, PacienteJaCadastrado, PacienteNaoEncontrado,
                     AgendamentoNaoEncontrado, ConflitoDeHorario):
            self.assertTrue(issubclass(erro, ErroClinica))
        self.assertEqual(str(PacienteNaoEncontrado("msg")), "msg")


class TestPacientes(unittest.TestCase):
    def setUp(self):
        self.c = Clinica(relogio=lambda: AGORA)
        self.ana = self.c.cadastrar_paciente(cpf(30), "Ana Souza", "1990-05-20",
                                             convenio="Unimed")
        self.bia = self.c.cadastrar_paciente(cpf(10), "Beatriz Lima", date(1950, 1, 1))
        self.alvaro = self.c.cadastrar_paciente(cpf(20), "Álvaro Dias", "2015-12-01",
                                                convenio="unimed")

    def tearDown(self):
        self.c.validar_indices()

    def test_cadastro_gera_prontuarios_sequenciais(self):
        self.assertEqual([p.prontuario for p in (self.ana, self.bia, self.alvaro)], [1, 2, 3])
        self.assertEqual(self.c.total_pacientes(), 3)

    def test_cadastro_duplicado_e_invalido(self):
        with self.assertRaises(PacienteJaCadastrado):
            self.c.cadastrar_paciente(formatar_cpf(cpf(30)), "Outra", "2000-01-01")
        with self.assertRaises(DadosInvalidos):
            self.c.cadastrar_paciente("123", "X Y", "2000-01-01")
        with self.assertRaises(DadosInvalidos):
            self.c.cadastrar_paciente(cpf(40), "", "2000-01-01")
        with self.assertRaises(DadosInvalidos):
            self.c.cadastrar_paciente(cpf(40), "Futuro", "2030-01-01")
        with self.assertRaises(DadosInvalidos):
            self.c.cadastrar_paciente(cpf(40), "Fulano", "2000-01-01", email="sem-arroba")
        self.assertEqual(self.c.total_pacientes(), 3)  # nada foi inserido

    def test_buscas(self):
        self.assertIs(self.c.buscar_por_cpf(formatar_cpf(cpf(30))), self.ana)
        self.assertIs(self.c.buscar_por_prontuario(2), self.bia)
        with self.assertRaises(PacienteNaoEncontrado):
            self.c.buscar_por_cpf(cpf(99))
        with self.assertRaises(PacienteNaoEncontrado):
            self.c.buscar_por_prontuario(99)

    def test_ordem_alfabetica_ignora_acentos(self):
        nomes = [p.nome for p in self.c.listar_alfabetico()]
        self.assertEqual(nomes, ["Álvaro Dias", "Ana Souza", "Beatriz Lima"])

    def test_nomes_iguais_nao_colidem(self):
        self.c.cadastrar_paciente(cpf(50), "Ana Souza", "2001-01-01")
        self.assertEqual(len(self.c.buscar_por_nome("ana souza")), 2)

    def test_busca_por_prefixo_de_nome(self):
        self.assertEqual([p.nome for p in self.c.buscar_por_nome("a")],
                         ["Álvaro Dias", "Ana Souza"])
        self.assertEqual([p.nome for p in self.c.buscar_por_nome("BEA")], ["Beatriz Lima"])
        self.assertEqual(self.c.buscar_por_nome("zé"), [])

    def test_intervalos(self):
        self.assertEqual([p.prontuario for p in self.c.pacientes_por_intervalo_prontuario(2, 3)],
                         [2, 3])
        self.assertEqual([p.cpf for p in self.c.pacientes_por_intervalo_cpf(cpf(10), cpf(20))],
                         [cpf(10), cpf(20)])
        # CPF parcial: todos que começam com "000000"
        self.assertEqual(len(self.c.pacientes_por_intervalo_cpf("000000", "000000")), 3)

    def test_filtrar_por_criterios(self):
        self.assertEqual([p.nome for p in self.c.filtrar_pacientes(idade_min=60)],
                         ["Beatriz Lima"])
        self.assertEqual([p.nome for p in self.c.filtrar_pacientes(idade_max=17)],
                         ["Álvaro Dias"])
        self.assertEqual([p.nome for p in self.c.filtrar_pacientes(convenio="UNIMED")],
                         ["Álvaro Dias", "Ana Souza"])
        self.assertEqual([p.nome for p in self.c.filtrar_pacientes(
            convenio="unimed", idade_min=18)], ["Ana Souza"])
        self.assertEqual([p.nome for p in self.c.filtrar_pacientes(nome_contem="lima")],
                         ["Beatriz Lima"])

    def test_idade(self):
        self.assertEqual(self.ana.idade(AGORA.date()), 36)
        self.assertEqual(self.ana.idade(date(2027, 5, 19)), 36)  # véspera do aniversário
        self.assertEqual(self.ana.idade(date(2027, 5, 20)), 37)

    def test_atualizar_nome_reindexa(self):
        self.c.atualizar_paciente(cpf(30), nome="Zuleica Souza", telefone="(61) 99999-0000")
        self.assertEqual(self.c.listar_alfabetico()[-1].nome, "Zuleica Souza")
        self.assertEqual(self.ana.telefone, "61999990000")
        self.assertEqual(self.c.buscar_por_nome("ana"), [])

    def test_atualizar_invalido_nao_altera_nada(self):
        with self.assertRaises(DadosInvalidos):
            self.c.atualizar_paciente(cpf(30), nome="Novo Nome", email="ruim")
        self.assertEqual(self.ana.nome, "Ana Souza")
        with self.assertRaises(DadosInvalidos):
            self.c.atualizar_paciente(cpf(30), prontuario=99)

    def test_remover(self):
        removido, _ = self.c.remover_paciente(cpf(30))
        self.assertIs(removido, self.ana)
        self.assertEqual(self.c.total_pacientes(), 2)
        with self.assertRaises(PacienteNaoEncontrado):
            self.c.buscar_por_prontuario(1)
        with self.assertRaises(PacienteNaoEncontrado):
            self.c.remover_paciente(cpf(30))


class TestAgendamentos(unittest.TestCase):
    def setUp(self):
        self.c = Clinica(relogio=lambda: AGORA)
        self.c.cadastrar_paciente(cpf(1), "Ana", "1990-01-01")
        self.c.cadastrar_paciente(cpf(2), "Bruno", "1980-01-01")
        self.c.cadastrar_paciente(cpf(3), "Carla", "1970-01-01")
        self.h = lambda hora, minuto=0, dia=16: datetime(2026, 11, dia, hora, minuto)

    def tearDown(self):
        self.c.validar_indices()

    def test_agendar_e_buscar(self):
        ag = self.c.agendar(cpf(1), "2026-11-16 09:00", "Dra. Maria")
        self.assertEqual(ag.id, 1)
        self.assertIs(self.c.buscar_agendamento(1), ag)
        self.assertEqual(ag.fim, self.h(9, 30))
        self.assertEqual(self.c.total_agendamentos(), 1)

    def test_validacoes(self):
        with self.assertRaises(PacienteNaoEncontrado):
            self.c.agendar(cpf(99), self.h(9), "Dra. Maria")
        with self.assertRaises(DadosInvalidos):
            self.c.agendar(cpf(1), self.h(7), "Dra. Maria")  # passado
        with self.assertRaises(DadosInvalidos):
            self.c.agendar(cpf(1), self.h(9), "Dra. Maria", duracao_min=500)
        with self.assertRaises(DadosInvalidos):
            self.c.agendar(cpf(1), "amanhã", "Dra. Maria")
        self.assertEqual(self.c.total_agendamentos(), 0)

    def test_conflito_profissional(self):
        self.c.agendar(cpf(1), self.h(9), "Dra. Maria", duracao_min=60)
        with self.assertRaises(ConflitoDeHorario):
            self.c.agendar(cpf(2), self.h(9, 30), "DRA. MARIA")  # mesmo profissional
        self.c.agendar(cpf(2), self.h(9, 30), "Dr. João")       # outro profissional: ok
        self.c.agendar(cpf(3), self.h(10), "Dra. Maria")        # encosta no fim: ok

    def test_conflito_paciente(self):
        self.c.agendar(cpf(1), self.h(9), "Dra. Maria")
        with self.assertRaises(ConflitoDeHorario):
            self.c.agendar(cpf(1), self.h(9, 15), "Dr. João")

    def test_conflito_com_consulta_longa_que_comecou_antes(self):
        self.c.agendar(cpf(1), self.h(9), "Dra. Maria", duracao_min=240)  # 9h-13h
        with self.assertRaises(ConflitoDeHorario):
            self.c.agendar(cpf(2), self.h(12, 45), "Dra. Maria")
        self.c.agendar(cpf(2), self.h(13), "Dra. Maria")

    def test_proximos_atendimentos(self):
        for i, hora in enumerate([14, 9, 11, 10, 16]):
            self.c.agendar(cpf(i % 3 + 1), self.h(hora), f"Prof {i}")
        self.assertEqual([a.data_hora.hour for a in self.c.proximos_atendimentos(3)],
                         [9, 10, 11])
        self.assertEqual([a.data_hora.hour for a in self.c.proximos_atendimentos(
            10, a_partir_de=self.h(10, 30))], [11, 14, 16])

    def test_proximos_por_profissional(self):
        self.c.agendar(cpf(1), self.h(9), "Dra. Maria")
        self.c.agendar(cpf(2), self.h(10), "Dr. João")
        self.c.agendar(cpf(3), self.h(11), "Dra. Maria")
        res = self.c.proximos_atendimentos(5, profissional="dra. maria")
        self.assertEqual([a.data_hora.hour for a in res], [9, 11])
        self.assertEqual([a.data_hora.hour for a in self.c.proximos_atendimentos(
            5, profissional="Dr. João")], [10])
        self.assertEqual(self.c.proximos_atendimentos(5, profissional="Ninguém"), [])

    def test_agenda_do_dia_e_intervalo(self):
        self.c.agendar(cpf(1), self.h(9), "Dra. Maria")
        self.c.agendar(cpf(2), self.h(23, 30), "Dra. Maria")
        self.c.agendar(cpf(3), self.h(0, 0, dia=17), "Dra. Maria")
        self.assertEqual(len(self.c.agenda_do_dia(date(2026, 11, 16))), 2)
        self.assertEqual(len(self.c.agenda_do_dia("2026-11-17")), 1)
        self.assertEqual(len(self.c.agenda_do_dia(date(2026, 11, 16), "Dra. Maria")), 2)
        self.assertEqual(len(self.c.agenda_do_dia(date(2026, 11, 16), "Outro")), 0)
        # intervalo semiaberto: quem começa exatamente no fim não entra
        self.assertEqual(len(self.c.agendamentos_no_intervalo(self.h(9), self.h(23, 30))), 1)

    def test_cancelar(self):
        ag = self.c.agendar(cpf(1), self.h(9), "Dra. Maria")
        self.assertIs(self.c.cancelar_agendamento(ag.id), ag)
        self.assertEqual(self.c.total_agendamentos(), 0)
        with self.assertRaises(AgendamentoNaoEncontrado):
            self.c.cancelar_agendamento(ag.id)
        self.c.agendar(cpf(2), self.h(9), "Dra. Maria")  # horário liberado

    def test_remarcar(self):
        ag = self.c.agendar(cpf(1), self.h(9), "Dra. Maria")
        self.c.agendar(cpf(2), self.h(10), "Dra. Maria")
        self.c.remarcar(ag.id, self.h(9, 15))  # sobrepõe só ele mesmo: ok
        with self.assertRaises(ConflitoDeHorario):
            self.c.remarcar(ag.id, self.h(10, 15))
        self.assertEqual(ag.data_hora, self.h(9, 15))  # falhou: nada mudou
        self.c.remarcar(ag.id, self.h(15))
        self.assertEqual([a.id for a in self.c.proximos_atendimentos()], [2, 1])

    def test_remover_paciente_cancela_agendamentos(self):
        self.c.agendar(cpf(1), self.h(9), "Dra. Maria")
        self.c.agendar(cpf(1), self.h(10), "Dr. João")
        self.c.agendar(cpf(2), self.h(11), "Dra. Maria")
        _, cancelados = self.c.remover_paciente(cpf(1))
        self.assertEqual(len(cancelados), 2)
        self.assertEqual(self.c.total_agendamentos(), 1)

    def test_agendamentos_do_paciente(self):
        self.c.agendar(cpf(1), self.h(15), "Dra. Maria")
        self.c.agendar(cpf(2), self.h(9), "Dra. Maria")
        self.c.agendar(cpf(1), self.h(9, dia=10), "Dr. João", permitir_passado=True)
        self.assertEqual([a.data_hora.day for a in self.c.agendamentos_do_paciente(cpf(1))],
                         [10, 16])
        self.assertEqual(len(self.c.agendamentos_do_paciente(cpf(1), somente_futuros=True)), 1)

    def test_listar_profissionais(self):
        self.c.agendar(cpf(1), self.h(9), "Dra. Maria")
        self.c.agendar(cpf(2), self.h(9), "Dr. João")
        self.c.agendar(cpf(3), self.h(10), "dra. maria")
        self.assertEqual(self.c.listar_profissionais(), ["Dr. João", "Dra. Maria"])

    def test_estatisticas(self):
        self.c.agendar(cpf(1), self.h(9), "Dra. Maria")
        stats = {s["indice"]: s for s in self.c.estatisticas()}
        self.assertEqual(stats["Pacientes por CPF"]["tipo"], "AVL")
        self.assertEqual(stats["Pacientes por CPF"]["tamanho"], 3)
        self.assertEqual(stats["Agenda por horário"]["tipo"], "Rubro-Negra")
        self.assertEqual(stats["Agenda por horário"]["tamanho"], 1)


class TestCargaAleatoria(unittest.TestCase):
    def test_muitas_operacoes_mantem_indices_consistentes(self):
        rng = random.Random(3)
        c = Clinica(relogio=lambda: AGORA)
        profissionais = ["Dra. Maria", "Dr. João", "Dra. Paula"]
        for n in range(1, 301):
            c.cadastrar_paciente(cpf(n), f"Paciente {rng.randint(1, 9999)}", "1990-01-01")
        for _ in range(2000):
            op = rng.random()
            try:
                if op < 0.6:
                    c.agendar(cpf(rng.randint(1, 300)),
                              AGORA + timedelta(minutes=15 * rng.randint(0, 2000)),
                              rng.choice(profissionais), duracao_min=rng.choice([15, 30, 60]))
                elif op < 0.8 and c.total_agendamentos():
                    c.cancelar_agendamento(rng.choice(c.listar_agendamentos()).id)
                elif op < 0.95 and c.total_agendamentos():
                    c.remarcar(rng.choice(c.listar_agendamentos()).id,
                               AGORA + timedelta(minutes=15 * rng.randint(0, 2000)))
                elif c.total_pacientes():
                    c.remover_paciente(rng.choice(c.listar_alfabetico()).cpf)
            except (ConflitoDeHorario, PacienteNaoEncontrado):
                pass
        c.validar_indices()
        # nenhum profissional com atendimentos sobrepostos
        for prof in profissionais:
            ags = c.proximos_atendimentos(10_000, a_partir_de=AGORA, profissional=prof)
            for a, b in zip(ags, ags[1:]):
                self.assertLessEqual(a.fim, b.data_hora)


if __name__ == "__main__":
    unittest.main()
