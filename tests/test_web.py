"""Testes do front-end. Precisam do Flask: .venv/bin/python -m unittest"""
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

try:
    import flask  # noqa: F401
    TEM_FLASK = True
except ImportError:
    TEM_FLASK = False

from clinica import dados_exemplo, persistencia
from clinica.servico import Clinica

AGORA = datetime(2026, 11, 16, 8, 0)
CPF_ANA = "52998224725"
CPF_BRUNO = "11144477735"


@unittest.skipUnless(TEM_FLASK, "Flask não instalado (use .venv/bin/python)")
class TestWeb(unittest.TestCase):
    def setUp(self):
        from clinica.web import create_app
        self.pasta = tempfile.TemporaryDirectory()
        self.caminho = Path(self.pasta.name) / "clinica.json"
        self.clinica = Clinica(relogio=lambda: AGORA)
        self.clinica.cadastrar_paciente(CPF_ANA, "Ana Souza", "1990-05-20", convenio="Unimed")
        self.clinica.cadastrar_paciente(CPF_BRUNO, "Bruno Lima", "1950-01-01")
        self.clinica.agendar(CPF_ANA, "2026-11-16 09:00", "Dra. Helena", duracao_min=60)
        self.app = create_app(self.caminho, clinica=self.clinica)
        self.app.testing = True
        self.cliente = self.app.test_client()

    def tearDown(self):
        self.clinica.validar_indices()
        self.pasta.cleanup()

    def get(self, url, status=200):
        resposta = self.cliente.get(url)
        self.assertEqual(resposta.status_code, status, url)
        return resposta.get_data(as_text=True)

    # ---------------------------------------------------------------- #
    def test_todas_as_paginas_abrem(self):
        for url in ["/", "/pacientes", "/pacientes/novo", f"/pacientes/{CPF_ANA}",
                    f"/pacientes/{CPF_ANA}/editar", "/agenda", "/agenda?modo=dia",
                    "/agenda?modo=intervalo&inicio=2026-11-16T08:00&fim=2026-11-16T12:00",
                    "/agenda?modo=todos", "/agenda/novo", "/agenda/1/remarcar",
                    "/arvores", "/laboratorio"]:
            self.get(url)

    def test_painel(self):
        html = self.get("/")
        self.assertIn("Ana Souza", html)  # próximos atendimentos
        self.assertIn("Pacientes por CPF", html)

    def test_painel_vazio_oferece_dados_de_exemplo(self):
        from clinica.web import create_app
        cliente = create_app(None, clinica=Clinica(relogio=lambda: AGORA)).test_client()
        self.assertIn("Gerar dados de exemplo", cliente.get("/").get_data(as_text=True))

    def test_modos_de_busca_de_pacientes(self):
        casos = {
            "/pacientes": ["Ana Souza", "Bruno Lima", "percurso em ordem"],
            "/pacientes?modo=nome&q=an": ["Ana Souza", "intervalo"],
            f"/pacientes?modo=cpf&q=529.982.247-25": ["Ana Souza", "O(log n)"],
            "/pacientes?modo=prontuario&q=2": ["Bruno Lima"],
            "/pacientes?modo=intervalo_prontuario&inicio=1&fim=2": ["Ana Souza", "Bruno Lima"],
            "/pacientes?modo=intervalo_cpf&inicio=500&fim=599": ["Ana Souza"],
            "/pacientes?modo=criterios&idade_min=60": ["Bruno Lima"],
            "/pacientes?modo=criterios&convenio=Unimed": ["Ana Souza"],
        }
        for url, esperados in casos.items():
            html = self.get(url)
            for texto in esperados:
                self.assertIn(texto, html, url)
        self.assertNotIn("Bruno Lima", self.get("/pacientes?modo=nome&q=an"))
        self.assertIn("não encontrado", self.get("/pacientes?modo=cpf&q=12345678909"))

    def test_cadastrar_paciente(self):
        r = self.cliente.post("/pacientes/novo", data={
            "cpf": "390.533.447-05", "nome": "Carla Dias", "data_nascimento": "2000-02-03",
            "telefone": "", "email": "", "convenio": ""}, follow_redirects=True)
        self.assertIn("Carla Dias cadastrado", r.get_data(as_text=True))
        self.assertEqual(self.clinica.total_pacientes(), 3)
        self.assertEqual(persistencia.carregar(self.caminho).total_pacientes(), 3)  # salvou

    def test_cadastro_invalido_mantem_formulario(self):
        r = self.cliente.post("/pacientes/novo", data={
            "cpf": "123", "nome": "Fulano de Tal", "data_nascimento": "2000-01-01"})
        self.assertEqual(r.status_code, 422)
        html = r.get_data(as_text=True)
        self.assertIn("CPF inválido", html)
        self.assertIn('value="Fulano de Tal"', html)  # não perde o que foi digitado

    def test_editar_e_remover_paciente(self):
        self.cliente.post(f"/pacientes/{CPF_BRUNO}/editar", data={
            "nome": "Bruno Lima Neto", "data_nascimento": "1950-01-01", "telefone": "",
            "email": "", "convenio": "Amil"})
        self.assertEqual(self.clinica.buscar_por_cpf(CPF_BRUNO).nome, "Bruno Lima Neto")
        r = self.cliente.post(f"/pacientes/{CPF_ANA}/remover", follow_redirects=True)
        self.assertIn("1 agendamento(s) cancelado(s)", r.get_data(as_text=True))
        self.assertEqual(self.clinica.total_agendamentos(), 0)
        self.get(f"/pacientes/{CPF_ANA}", status=404)

    def test_agendar_conflito_remarcar_cancelar(self):
        r = self.cliente.post("/agenda/novo", data={
            "cpf": "111.444.777-35", "profissional": "Dra. Helena", "data": "2026-11-16",
            "hora": "09:30", "duracao_min": "30", "observacao": ""})
        self.assertEqual(r.status_code, 422)
        self.assertIn("já tem atendimento", r.get_data(as_text=True))

        r = self.cliente.post("/agenda/novo", data={
            "cpf": CPF_BRUNO, "profissional": "Dra. Helena", "data": "2026-11-16",
            "hora": "10:00", "duracao_min": "30", "observacao": "Retorno"}, follow_redirects=True)
        self.assertIn("Agendamento #2 criado", r.get_data(as_text=True))

        self.cliente.post("/agenda/2/remarcar", data={
            "data": "2026-11-17", "hora": "14:00", "duracao_min": "45"})
        ag = self.clinica.buscar_agendamento(2)
        self.assertEqual((ag.data_hora, ag.duracao_min), (datetime(2026, 11, 17, 14, 0), 45))

        self.cliente.post("/agenda/2/cancelar")
        self.assertEqual(self.clinica.total_agendamentos(), 1)
        self.get("/agenda/2/remarcar", status=404)

    def test_agenda_por_dia_e_profissional(self):
        html = self.get("/agenda?modo=dia&dia=2026-11-16&profissional=Dra.+Helena")
        self.assertIn("Ana Souza", html)
        self.assertIn("17/11/2026", html)  # navegação para o dia seguinte
        self.assertIn("Nenhum agendamento", self.get("/agenda?modo=dia&dia=2026-11-18"))

    def test_gerar_exemplo(self):
        self.cliente.post("/exemplo", data={"pacientes": "10", "agendamentos": "15"})
        self.assertEqual(self.clinica.total_pacientes(), 12)

    # ---------------------------------------------------------------- #
    def test_api_arvores(self):
        dados_exemplo.popular(self.clinica, 20, 20, semente=1)
        for slug in ["cpf", "prontuario", "nome", "agenda-horario", "agenda-id",
                     "agenda-profissional", "agenda-paciente"]:
            dados = self.cliente.get(f"/api/arvores/{slug}").get_json()
            self.assertIn(dados["tipo"], ("AVL", "Rubro-Negra"))
            self.assertEqual(_contar(dados["raiz"]), dados["tamanho"])
        raiz = self.cliente.get("/api/arvores/agenda-horario").get_json()["raiz"]
        self.assertEqual(raiz["cor"], "preto")
        self.assertEqual(self.cliente.get("/api/arvores/xyz").status_code, 404)

    def test_api_laboratorio(self):
        post = lambda tipo, **corpo: self.cliente.post(f"/api/lab/{tipo}", json=corpo).get_json()  # noqa
        for tipo in ("avl", "rn"):
            d = post(tipo, acao="carregar", chaves=[1, 2, 3])
            self.assertEqual((d["tamanho"], d["raiz"]["chave"]), (3, "2"))
            self.assertGreaterEqual(d["rotacoes_operacao"], 1)
            d = post(tipo, acao="inserir", chave=4)
            self.assertEqual(d["destaque"], "4")
            self.assertTrue(post(tipo, acao="inserir", chave=4)["erro"])  # duplicada
            d = post(tipo, acao="buscar", chave=4)
            self.assertEqual(d["caminho"], ["2", "3", "4"])
            self.assertFalse(d["erro"])
            self.assertTrue(post(tipo, acao="buscar", chave=99)["erro"])
            self.assertEqual(post(tipo, acao="remover", chave=2)["tamanho"], 3)
            self.assertTrue(post(tipo, acao="remover", chave=2)["erro"])
            self.assertTrue(post(tipo, acao="inserir", chave="abc")["erro"])
            self.assertIsNone(post(tipo, acao="limpar")["raiz"])
        self.assertEqual(self.cliente.post("/api/lab/avl", json={"acao": "x"}).status_code, 400)
        self.assertEqual(self.cliente.get("/api/lab/b").status_code, 404)

    def test_laboratorio_nao_mexe_na_clinica(self):
        self.cliente.post("/api/lab/avl", json={"acao": "carregar", "chaves": list(range(30))})
        self.assertEqual(self.clinica.total_pacientes(), 2)


def _contar(no):
    return 0 if no is None else 1 + _contar(no["esquerda"]) + _contar(no["direita"])


if __name__ == "__main__":
    unittest.main()
