"""Transforma os CSVs trimestrais do SP156 em data/dados_sp156.csv (esquema do projeto).

Uso (janela adotada: 1º tri/2020 a 3º tri/2023):
  python scripts/preparar_dados.py --entrada "uploads/*trimestre-2020.csv" "uploads/arquivo-final-*trim_-202*.csv" \
      "uploads/arquivo-final-2-trim_-2021.xlsx" --inicio 2020-01-01 --fim 2023-09-30

O que faz, em ordem:
  1. lê cada arquivo (.csv ou .xlsx; detecta codificação e separador) e normaliza os nomes das colunas (os
     arquivos variam: "Distrito" ou "Bairro", "Data do Parecer" ou "Data de Finalização", "Status" ou
     "Status da solicitação"); as datas são ISO (2018–19, xlsx) ou dd/mm/aaaa (2020 em diante), por arquivo;
  2. fica só com os SERVIÇOS do de-para (data/depara_sp156.csv) -> categorias da tabela 6.4;
  3. fica só com status FINALIZADA e remove linhas repetidas ENTRE arquivos vizinhos (sobreposição), mantendo
     linhas idênticas dentro do mesmo arquivo (sem hora/protocolo elas são chamados diferentes);
  4. dias_para_resolver = data do parecer - data de abertura (em dias; negativos são descartados);
  5. a coluna Subprefeitura do SP156 vem VAZIA: a subprefeitura é derivada do distrito
     (data/depara_distrito_subprefeitura.csv);
  6. atrasou = 1 se dias_para_resolver > prazo da categoria (a mesma regra da RN11).

ATENÇÃO — o que "Data do Parecer" mede muda ao longo dos anos: em 2015 e até 3º tri/2016 ela é
praticamente o próprio dia da abertura (não mede atendimento). O script imprime, por trimestre, a
% de chamados com 0 dia e AVISA quando passa de 40%: nesse caso a janela de datas é inadequada.
"""
import argparse
import glob
import os
import re
import sys
import unicodedata

import pandas as pd

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
from chatbot.intents import CATEGORIAS  # noqa: E402  (nomes e prazos canônicos)

LIMITE_ZERO = 0.40  # acima disso, o trimestre não serve para medir tempo de atendimento


def norm(s) -> str:
    """minúsculas, sem acento, tudo que não é letra/número vira '_' ('?' e '–' ficam iguais)."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


ALIAS = {"bairro": "distrito", "data_do_parecer": "parecer", "data_de_finalizacao": "parecer",
         "status_da_solicitacao": "status", "data_de_abertura": "abertura", "orgao": "orgao"}
NECESSARIAS = ["abertura", "servico", "distrito", "parecer", "status"]


def _datas(serie: pd.Series) -> pd.Series:
    """ISO (aaaa-mm-dd) ou dd/mm/aaaa: decide pelo primeiro valor preenchido do ARQUIVO (nunca por linha)."""
    ref = serie.dropna().head(1).astype(str)
    iso = len(ref) and bool(re.match(r"\d{4}-\d\d-\d\d", ref.iloc[0]))
    return pd.to_datetime(serie, errors="coerce", **({} if iso else {"dayfirst": True}))


def ler(caminho: str, chaves: set) -> pd.DataFrame:
    if caminho.lower().endswith(".xlsx"):
        df = pd.read_excel(caminho, dtype=str)
    else:
        bruto = open(caminho, "rb").read(20000)
        try:
            bruto.decode("utf-8")
            enc = "utf-8-sig"
        except UnicodeDecodeError as e:
            # o corte dos 20000 bytes pode partir um caractere ao meio: só vale como latin-1 se o erro não for no fim
            enc = "utf-8-sig" if e.start >= len(bruto) - 3 else "latin-1"
        primeira = bruto.decode(enc, errors="ignore").splitlines()[0]
        sep = ";" if primeira.count(";") > primeira.count(",") else ","
        df = pd.read_csv(caminho, sep=sep, encoding=enc, dtype=str, low_memory=False)
    nomes = [norm(c) for c in df.columns]
    # 2020 traz "Bairro" E "Distrito": o alias bairro->distrito só vale quando não há coluna Distrito
    df.columns = [ALIAS.get(n, n) if not (n == "bairro" and "distrito" in nomes) else n for n in nomes]
    faltam = [c for c in NECESSARIAS if c not in df.columns]
    if faltam:
        sys.exit(f"{os.path.basename(caminho)}: faltam as colunas {faltam}. Tem: {list(df.columns)}")
    df = df[df["servico"].map(norm).isin(chaves)]
    df = df.assign(abertura=_datas(df["abertura"]), parecer=_datas(df["parecer"]))
    cols = NECESSARIAS + (["canal"] if "canal" in df.columns else [])
    return df[cols].assign(arquivo=os.path.basename(caminho))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--entrada", required=True, nargs="+", help="arquivos ou padrões (glob)")
    ap.add_argument("--saida", default=os.path.join(RAIZ, "data", "dados_sp156.csv"))
    ap.add_argument("--depara", default=os.path.join(RAIZ, "data", "depara_sp156.csv"))
    ap.add_argument("--depara-distrito", default=os.path.join(RAIZ, "data", "depara_distrito_subprefeitura.csv"))
    ap.add_argument("--inicio", default=None, help="abertura a partir de AAAA-MM-DD")
    ap.add_argument("--fim", default=None, help="abertura até AAAA-MM-DD")
    a = ap.parse_args()

    arquivos = sorted({f for p in a.entrada for f in (glob.glob(p) or [p])})
    if not arquivos or not all(os.path.exists(f) for f in arquivos):
        sys.exit(f"Arquivos não encontrados: {a.entrada}")

    dp = pd.read_csv(a.depara, dtype=str).dropna()
    invalidas = sorted(set(dp["categoria"]) - set(CATEGORIAS))
    if invalidas:
        sys.exit(f"Categorias fora da tabela 6.4 no de-para: {invalidas}")
    servico_para_cat = {norm(s): c for s, c in zip(dp["servico_sp156"], dp["categoria"])}
    dist = pd.read_csv(a.depara_distrito, dtype=str)
    distrito_para_sub = {norm(d): s for d, s in zip(dist["distrito"], dist["subprefeitura"])}

    partes = []
    for f in arquivos:
        p = ler(f, set(servico_para_cat))
        print(f"{os.path.basename(f):38s} {len(p):>8,} linhas nas 8 categorias")
        partes.append(p)
    df = pd.concat(partes, ignore_index=True)
    n0 = len(df)

    df["categoria"] = df["servico"].map(lambda s: servico_para_cat[norm(s)])
    df["abertura_dt"] = df["abertura"]
    df["parecer_dt"] = df["parecer"]
    df = df[df["status"].fillna("").str.upper().eq("FINALIZADA")]
    n_final = len(df)
    # De 2020 em diante os arquivos NÃO têm hora nem protocolo: chamados distintos podem ser linhas idênticas.
    # Por isso só se remove a linha que se repete ENTRE arquivos (sobreposição); gêmeas dentro do mesmo arquivo ficam.
    chave = [c for c in df.columns if c != "arquivo"]
    df["_n"] = df.groupby(chave + ["arquivo"], dropna=False).cumcount()
    df = df.drop_duplicates(subset=chave + ["_n"]).drop(columns="_n")
    n_dedup = len(df)
    df = df.dropna(subset=["abertura_dt", "parecer_dt", "distrito"])
    if a.inicio:
        df = df[df["abertura_dt"] >= pd.Timestamp(a.inicio)]
    if a.fim:
        df = df[df["abertura_dt"] < pd.Timestamp(a.fim) + pd.Timedelta(days=1)]
    df["dias_para_resolver"] = (df["parecer_dt"].dt.normalize() - df["abertura_dt"].dt.normalize()).dt.days
    negativos = int((df["dias_para_resolver"] < 0).sum())
    df = df[df["dias_para_resolver"] >= 0]
    df["subprefeitura"] = df["distrito"].map(lambda d: distrito_para_sub.get(norm(d)))
    sem_sub = int(df["subprefeitura"].isna().sum())
    if sem_sub:
        print("Distritos sem subprefeitura no de-para (descartados):",
              df.loc[df["subprefeitura"].isna(), "distrito"].value_counts().head(8).to_dict())
    df = df.dropna(subset=["subprefeitura"])

    # --- alarme: o parecer mede atendimento neste período? ---
    df["tri"] = df["abertura_dt"].dt.year.astype(str) + "T" + df["abertura_dt"].dt.quarter.astype(str)
    zero = df.groupby("tri")["dias_para_resolver"].agg(n="size", pct_zero=lambda s: (s == 0).mean())
    print("\nChamados por trimestre e % com parecer no MESMO dia da abertura:")
    print(zero.assign(pct_zero=lambda z: (z.pct_zero * 100).round(1)).to_string())
    ruins = zero[zero["pct_zero"] > LIMITE_ZERO]
    if len(ruins):
        print(f"\n*** ATENÇÃO: {list(ruins.index)} têm mais de {LIMITE_ZERO:.0%} de chamados com 0 dia. "
              "A 'Data do Parecer' provavelmente NÃO mede o tempo de atendimento nesses trimestres. "
              "Use --inicio/--fim para uma janela melhor, ou confirme com o grupo. ***")

    out = pd.DataFrame({
        "categoria": df["categoria"], "subprefeitura": df["subprefeitura"],
        "data_abertura": df["abertura_dt"].dt.strftime("%Y-%m-%d"),
        "data_encerramento": df["parecer_dt"].dt.strftime("%Y-%m-%d"),
        "mes": df["abertura_dt"].dt.month, "dia_semana": df["abertura_dt"].dt.weekday,
        "dias_para_resolver": df["dias_para_resolver"],
    })
    out["nr_prazo_dias"] = out["categoria"].map(lambda c: CATEGORIAS[c]["prazo_dias"])
    out["atrasou"] = (out["dias_para_resolver"] > out["nr_prazo_dias"]).astype(int)  # RN11
    out = out.sort_values("data_abertura").reset_index(drop=True)
    os.makedirs(os.path.dirname(a.saida), exist_ok=True)
    out.to_csv(a.saida, index=False)

    print(f"\nFunil: {n0:,} nas 8 categorias -> {n_final:,} FINALIZADA -> {n_dedup:,} sem duplicatas "
          f"-> {len(out):,} final (negativos: {negativos:,}; sem subprefeitura: {sem_sub:,})")
    print(f"Gravado em {a.saida}\n")
    resumo = out.groupby("categoria").agg(chamados=("atrasou", "size"), pct_atrasou=("atrasou", "mean"),
                                          mediana_dias=("dias_para_resolver", "median"),
                                          pct_zero_dia=("dias_para_resolver", lambda s: (s == 0).mean()))
    print(resumo.round(3).to_string())


if __name__ == "__main__":
    main()
