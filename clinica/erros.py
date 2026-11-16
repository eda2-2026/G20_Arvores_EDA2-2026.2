"""Exceções da aplicação. Todas herdam de ErroClinica, assim o front-end
pode capturar uma única classe e exibir a mensagem ao usuário."""


class ErroClinica(Exception):
    pass


class DadosInvalidos(ErroClinica, ValueError):
    pass


class PacienteJaCadastrado(ErroClinica):
    pass


class PacienteNaoEncontrado(ErroClinica, KeyError):
    def __str__(self):  # KeyError coloca aspas na mensagem; aqui não queremos
        return str(self.args[0]) if self.args else ""


class AgendamentoNaoEncontrado(ErroClinica, KeyError):
    def __str__(self):
        return str(self.args[0]) if self.args else ""


class ConflitoDeHorario(ErroClinica):
    pass
