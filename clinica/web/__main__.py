import argparse

from ..cli import CAMINHO_PADRAO
from .app import create_app

parser = argparse.ArgumentParser(description="Front-end web da clínica.")
parser.add_argument("--arquivo", default=CAMINHO_PADRAO)
parser.add_argument("--porta", type=int, default=5000)
args = parser.parse_args()

app = create_app(args.arquivo)
print(f"Abra http://127.0.0.1:{args.porta} no navegador (Ctrl+C para encerrar).")
app.run(host="127.0.0.1", port=args.porta, debug=False, threaded=False)
