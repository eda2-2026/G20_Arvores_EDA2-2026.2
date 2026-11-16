"""Front-end web em Flask. Veja app.py.

O import do Flask é feito só quando o app é criado, assim o resto do projeto
(e a descoberta de testes do unittest) funciona mesmo sem o Flask instalado.
"""


def create_app(*args, **kwargs):
    from .app import create_app as criar
    return criar(*args, **kwargs)


__all__ = ["create_app"]
