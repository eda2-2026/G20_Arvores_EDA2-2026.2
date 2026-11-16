import json
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from clinica import dados_exemplo, persistencia
from clinica.cli import CLI, formatar_chave
from clinica.erros import ErroPersistencia
from clinica.modelos import validar_cpf
from clinica.servico import Clinica

AGORA = datetime(2026, 11, 16, 8, 0)  # segunda-feira
relogio = lambda: AGORA  # noqa: E731


def resumo(clinica):
    """Representação comparável do conteúdo de uma clínica."""
    return (
        [(p.prontuario, p.cpf, p.nome, p.data_nascimento, p.telefone, p.email, p.convenio)
         for p in clinica.listar_por_prontuario()],
        [(a.id, a.cpf_paciente, a.profissional, a.data_hora, a.duracao_min, a.observacao)
         for a in clinica.listar_agendamentos()],
        clinica.contadores,
    )


class TestPersistencia(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.caminho = Path(self.pasta.name) / "sub" / "clinica.json"
        self.c = Clinica(relogio=relogio)
        dados_exemplo.popular(self.c, pacientes=40, agendamentos=80, semente=1)

    def tearDown(self):
        self.pasta.cleanup()

    def test_ida_e_volta(self):
        persistencia.salvar(self.c, self.caminho)
        recarregada = persistencia.carregar(self.caminho, relogio=relogio)
        self.assertEqual(resumo(recarregada), resumo(self.c))
        recarregada.validar_indices()

    def test_arquivo_legivel_com_acentos(self):
        self.c.cadastrar_paciente("529.982.247-25", "Conceição Ávila", "01/02/1960")
        persistencia.salvar(self.c, self.caminho)
        texto = self.caminho.read_text(encoding="utf-8")
        self.assertIn("Conceição Ávila", texto)
        dados = json.loads(texto)
        self.assertEqual(dados["versao"], 1)
        self.assertIn("1960-02-01", texto)

    def test_ids_removidos_nao_sao_reutilizados(self):
        ultimo = self.c.listar_por_prontuario()[-1]
        self.c.remover_paciente(ultimo.cpf)
        persistencia.salvar(self.c, self.caminho)
        recarregada = persistencia.carregar(self.caminho, relogio=relogio)
        novo = recarregada.cadastrar_paciente("529.982.247-25", "Novo Paciente", "2000-01-01")
        self.assertEqual(novo.prontuario, ultimo.prontuario + 1)

    def test_consultas_passadas_sao_preservadas(self):
        c = Clinica(relogio=relogio)
        c.cadastrar_paciente("52998224725", "Ana", "1990-01-01")
        c.agendar("52998224725", "10/11/2026 09:00", "Dra. X", permitir_passado=True)
        persistencia.salvar(c, self.caminho)
        self.assertEqual(persistencia.carregar(self.caminho, relogio=relogio)
                         .total_agendamentos(), 1)

    def test_arquivo_inexistente_retorna_clinica_vazia(self):
        c = persistencia.carregar(Path(self.pasta.name) / "nao_existe.json")
        self.assertEqual(c.total_pacientes(), 0)

    def test_arquivo_corrompido(self):
        self.caminho.parent.mkdir(parents=True)
        self.caminho.write_text("{ isto não é json", encoding="utf-8")
        with self.assertRaises(ErroPersistencia):
            persistencia.carregar(self.caminho)
        self.caminho.write_text('{"versao": 99}', encoding="utf-8")
        with self.assertRaises(ErroPersistencia):
            persistencia.carregar(self.caminho)

    def test_registro_invalido_no_arquivo(self):
        dados = persistencia.para_dict(self.c)
        dados["pacientes"][0]["cpf"] = "123"
        with self.assertRaises(ErroPersistencia):
            persistencia.de_dict(dados, relogio=relogio)

    def test_salvar_nao_deixa_temporarios(self):
        persistencia.salvar(self.c, self.caminho)
        persistencia.salvar(self.c, self.caminho)
        self.assertEqual([p.name for p in self.caminho.parent.iterdir()], ["clinica.json"])


class TestDadosExemplo(unittest.TestCase):
    def test_popular(self):
        c = Clinica(relogio=relogio)
        pacientes, agendamentos = dados_exemplo.popular(c, 25, 50, semente=7)
        self.assertEqual(len(pacientes), 25)
        self.assertEqual(len(agendamentos), 50)
        for p in pacientes:
            validar_cpf(p.cpf)
            self.assertTrue(p.email.isascii())
        for a in agendamentos:
            self.assertLess(a.data_hora.weekday(), 5)
            self.assertTrue(8 <= a.data_hora.hour < 18)
        c.validar_indices()

    def test_mesma_semente_mesmos_dados(self):
        c1, c2 = Clinica(relogio=relogio), Clinica(relogio=relogio)
        dados_exemplo.popular(c1, 10, 20, semente=5)
        dados_exemplo.popular(c2, 10, 20, semente=5)
        self.assertEqual(resumo(c1), resumo(c2))


class TestCLI(unittest.TestCase):
    def executar(self, entradas, clinica=None, caminho=None):
        clinica = clinica or Clinica(relogio=relogio)
        respostas = iter(entradas)
        saidas = []

        def entrada(_prompt):
            try:
                return next(respostas)
            except StopIteration:
                raise EOFError

        CLI(clinica, caminho, entrada=entrada, saida=saidas.append).executar()
        return clinica, "\n".join(saidas)

    def test_cadastrar_buscar_e_listar(self):
        c, saida = self.executar([
            "1", "529.982.247-25", "Maria Silva", "10/03/1955", "", "", "Unimed", "",
            "2", "52998224725", "",
            "4", "",
            "0",
        ])
        self.assertEqual(c.total_pacientes(), 1)
        self.assertIn("prontuário 1", saida)
        self.assertIn("Nascimento: 10/03/1955 (71 anos)", saida)
        self.assertIn("(1 paciente(s))", saida)

    def test_erro_e_mostrado_sem_derrubar_o_programa(self):
        _, saida = self.executar(["2", "000.000.000-00", "", "99", "", "0"])
        self.assertIn("✘ Paciente com CPF 000.000.000-00 não encontrado.", saida)
        self.assertIn("Opção inválida.", saida)
        self.assertIn("Até logo!", saida)

    def test_agendar_conflito_e_proximos(self):
        c = Clinica(relogio=relogio)
        c.cadastrar_paciente("52998224725", "Ana", "1990-01-01")
        c.cadastrar_paciente("11144477735", "Bruno", "1990-01-01")
        _, saida = self.executar([
            "11", "52998224725", "16/11/2026 09:00", "Dra. Helena", "60", "", "",
            "11", "11144477735", "16/11/2026 09:30", "Dra. Helena", "", "", "",
            "14", "", "", "",
            "0",
        ], clinica=c)
        self.assertIn("✔ Agendamento #1: 16/11/2026 09:00-10:00.", saida)
        self.assertIn("✘ O profissional Dra. Helena já tem atendimento", saida)
        self.assertIn("(1 agendamento(s))", saida)

    def test_remover_pede_confirmacao(self):
        c = Clinica(relogio=relogio)
        c.cadastrar_paciente("52998224725", "Ana", "1990-01-01")
        self.executar(["10", "52998224725", "n", "", "0"], clinica=c)
        self.assertEqual(c.total_pacientes(), 1)
        self.executar(["10", "52998224725", "s", "", "0"], clinica=c)
        self.assertEqual(c.total_pacientes(), 0)

    def test_atualizar_mantem_valores_com_enter(self):
        c = Clinica(relogio=relogio)
        c.cadastrar_paciente("52998224725", "Ana", "1990-01-01", convenio="Amil")
        self.executar(["9", "52998224725", "", "", "61999998888", "", "", "", "0"], clinica=c)
        p = c.buscar_por_cpf("52998224725")
        self.assertEqual((p.nome, p.data_nascimento, p.telefone, p.convenio),
                         ("Ana", date(1990, 1, 1), "61999998888", "Amil"))

    def test_estatisticas_e_desenho(self):
        c = Clinica(relogio=relogio)
        dados_exemplo.popular(c, 7, 5, semente=2)
        _, saida = self.executar(["17", "", "18", "4", "", "0"], clinica=c)
        self.assertIn("Pacientes por CPF", saida)
        self.assertIn("[P]", saida)  # árvore da agenda desenhada com cores

    def test_salva_automaticamente(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "dados.json"
            self.executar(["1", "52998224725", "Ana", "01/01/1990", "", "", "", ""],
                          caminho=caminho)  # termina com EOF, sem digitar 0
            self.assertEqual(persistencia.carregar(caminho).total_pacientes(), 1)

    def test_formatar_chave(self):
        self.assertEqual(formatar_chave("52998224725"), "529.982.247-25")
        self.assertEqual(formatar_chave((datetime(2026, 11, 16, 9, 5), 3)), "16/11 09:05 | 3")
        self.assertEqual(formatar_chave(("ana", "52998224725")), "ana | 529.982.247-25")


if __name__ == "__main__":
    unittest.main()
