"""Monta o .zip de entrega: sem __pycache__, .env, checkpoints; com o .txt de RM/nome/turma.

Uso: python scripts/empacotar.py [--txt identificacao.txt] [--saida zelabairro-ia.zip]
O .txt (RM, nome e turma de cada integrante) é exigência da GS. Confira os notebooks: eles
precisam estar EXECUTADOS, com as saídas do CSV real, antes de empacotar.
"""
import argparse
import json
import os
import sys
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IGNORAR_DIRS = {"__pycache__", ".pytest_cache", ".venv", "venv", ".ipynb_checkpoints", ".git", ".idea", ".vscode"}
IGNORAR_ARQ = (".pyc", ".env", ".exec.ipynb")
OBRIGATORIOS = ["data/dados_sp156.csv", "data/depara_sp156.csv", "data/depara_distrito_subprefeitura.csv", "models/modelo_prazo.joblib",
                "models/modelo_atraso.joblib", "notebooks/01_eda.ipynb", "notebooks/02_modelo_prazo.ipynb",
                "notebooks/03_modelo_atraso.ipynb", "app.py", "requirements.txt", "README.md"]


def notebook_sem_saida(caminho):
    with open(caminho, encoding="utf-8") as f:
        nb = json.load(f)
    codigo = [c for c in nb["cells"] if c["cell_type"] == "code"]
    return not any(c.get("outputs") for c in codigo)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--txt", default=os.path.join(RAIZ, "identificacao.txt"), help="arquivo .txt com RM, nome e turma")
    ap.add_argument("--saida", default=os.path.join(RAIZ, "..", "zelabairro-ia.zip"))
    a = ap.parse_args()
    erros = [f"falta {p}" for p in OBRIGATORIOS if not os.path.exists(os.path.join(RAIZ, p))]
    for nb in ("01_eda", "02_modelo_prazo", "03_modelo_atraso"):
        c = os.path.join(RAIZ, "notebooks", nb + ".ipynb")
        if os.path.exists(c) and notebook_sem_saida(c):
            erros.append(f"{nb}.ipynb está SEM saídas: execute o notebook com o CSV real e salve")
    if not os.path.exists(a.txt):
        erros.append(f"não achei {a.txt}")
    if erros:
        sys.exit("Não empacotei, corrija antes:\n- " + "\n- ".join(erros))
    with zipfile.ZipFile(a.saida, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(a.txt, os.path.basename(a.txt))
        for pasta, dirs, arqs in os.walk(RAIZ):
            dirs[:] = [d for d in dirs if d not in IGNORAR_DIRS]
            for nome in arqs:
                if nome.endswith(IGNORAR_ARQ):
                    continue
                cam = os.path.join(pasta, nome)
                z.write(cam, os.path.join("zelabairro-ia", os.path.relpath(cam, RAIZ)))
    print("gerado", os.path.abspath(a.saida))


if __name__ == "__main__":
    main()
