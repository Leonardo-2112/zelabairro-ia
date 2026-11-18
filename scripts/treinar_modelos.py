"""Treina M1 (prazo, regressão) e M2 (atraso, classificação) e salva os .joblib.

Espelha os notebooks 02 e 03 (mesmos algoritmos, alvo log(1 + dias) no prazo e hiperparâmetros da busca deles; sem a
busca nem a validação cruzada, que ficam só nos notebooks). Uso: python scripts/treinar_modelos.py [--dados data/dados_sp156.csv]
Todas as métricas são calculadas no conjunto de TESTE (20%) e gravadas dentro do .joblib e em
models/metricas.json. Nada aqui é fixo ou inventado: sem o CSV real, o script para.
"""
import argparse
import json
import os
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score, mean_absolute_error,
                             mean_squared_error, precision_score, r2_score, recall_score, roc_auc_score)
from sklearn.model_selection import train_test_split

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
from ml_utils import FEATURES, montar_pipeline as montar, montar_regressor  # noqa: E402  (módulo importável pela API)

SEED = 42
# melhores hiperparâmetros encontrados pela busca dos notebooks 02 e 03
PARAMS_PRAZO = dict(n_estimators=100, min_samples_leaf=50, max_depth=None)
PARAMS_ATRASO = dict(n_estimators=100, min_samples_leaf=20, max_depth=16)


def treinar(dados: str, saida: str):
    if not os.path.exists(dados):
        sys.exit(f"Arquivo {dados} não existe. Rode scripts/preparar_dados.py com o CSV do SP156.")
    df = pd.read_csv(dados)
    obrig = FEATURES + ["dias_para_resolver", "atrasou"]
    faltam = [c for c in obrig if c not in df.columns]
    if faltam:
        sys.exit(f"Colunas ausentes em {dados}: {faltam}")
    if len(df) < 200:
        print(f"AVISO: só {len(df)} linhas; as métricas serão pouco confiáveis.")
    X = df[FEATURES]
    # categorias com exemplos no treino: o chatbot só mostra previsão para elas (ver predictor.info)
    cobertura = {k: int(v) for k, v in df["categoria"].value_counts().items()}
    os.makedirs(saida, exist_ok=True)
    resultado = {}
    ano = pd.to_datetime(df["data_abertura"]).dt.year if "data_abertura" in df.columns else None

    # ---- M1: regressão ----
    Xtr, Xte, ytr, yte = train_test_split(X, df["dias_para_resolver"], test_size=0.2, random_state=SEED)
    reg = montar_regressor(RandomForestRegressor(n_jobs=-1, random_state=SEED, **PARAMS_PRAZO)).fit(Xtr, ytr)
    base = DummyRegressor(strategy="median").fit(Xtr, ytr)
    p = reg.predict(Xte)
    med_cat = ytr.groupby(Xtr["categoria"]).median()  # baseline sem IA: a mediana de cada categoria
    p_cat = Xte["categoria"].map(med_cat).fillna(ytr.median())
    m1 = {"MAE": float(mean_absolute_error(yte, p)),
          "RMSE": float(np.sqrt(mean_squared_error(yte, p))), "R2": float(r2_score(yte, p)),
          "baseline_mediana_MAE": float(mean_absolute_error(yte, base.predict(Xte))),
          "baseline_mediana_por_categoria_MAE": float(mean_absolute_error(yte, p_cat)),
          "linhas_treino": int(len(Xtr)), "linhas_teste": int(len(Xte))}
    reg.fit(X, df["dias_para_resolver"])  # como nos notebooks: o modelo final usa todos os dados; as métricas são do teste
    joblib.dump({"pipeline": reg, "metricas": m1, "features": FEATURES, "usa_mes": False, "alvo": "log1p(dias)",
                 "categorias_treino": cobertura}, os.path.join(saida, "modelo_prazo.joblib"), compress=3)
    if ano is not None and (ano <= 2022).any() and (ano == 2023).any():
        # teste "no tempo": treina até 2022 e avalia em 2023 (o uso real é prever o futuro)
        a, b = df[ano <= 2022], df[ano == 2023]
        rt = montar_regressor(RandomForestRegressor(n_estimators=60, min_samples_leaf=20, n_jobs=-1,
                                                    random_state=SEED)).fit(a[FEATURES], a["dias_para_resolver"])
        m1["temporal_2023_MAE"] = float(mean_absolute_error(b["dias_para_resolver"], rt.predict(b[FEATURES])))
    resultado["modelo_prazo"] = m1

    # ---- M2: classificação ----
    estrat = df["atrasou"] if df["atrasou"].nunique() > 1 else None
    Xtr, Xte, ytr, yte = train_test_split(X, df["atrasou"], test_size=0.2, random_state=SEED,
                                          stratify=estrat)
    clf = montar(RandomForestClassifier(class_weight="balanced", n_jobs=-1, random_state=SEED,
                                        **PARAMS_ATRASO)).fit(Xtr, ytr)
    base = DummyClassifier(strategy="most_frequent").fit(Xtr, ytr)
    p = clf.predict(Xte)
    m2 = {"acuracia": float(accuracy_score(yte, p)),
          "precisao": float(precision_score(yte, p, zero_division=0)),
          "recall": float(recall_score(yte, p, zero_division=0)),
          "f1": float(f1_score(yte, p, zero_division=0)),
          "roc_auc": float(roc_auc_score(yte, clf.predict_proba(Xte)[:, 1])) if yte.nunique() > 1 else None,
          "matriz_confusao": confusion_matrix(yte, p, labels=[0, 1]).tolist(),
          "baseline_acuracia": float(accuracy_score(yte, base.predict(Xte))),
          "pct_atrasou_no_conjunto": float(df["atrasou"].mean()),
          "linhas_treino": int(len(Xtr)), "linhas_teste": int(len(Xte))}
    clf.fit(X, df["atrasou"])  # modelo final com todos os dados, como nos notebooks
    joblib.dump({"pipeline": clf, "metricas": m2, "features": FEATURES, "usa_mes": False,
                 "categorias_treino": cobertura}, os.path.join(saida, "modelo_atraso.joblib"), compress=3)
    resultado["modelo_atraso"] = m2

    with open(os.path.join(saida, "metricas.json"), "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dados", default=os.path.join(RAIZ, "data", "dados_sp156.csv"))
    ap.add_argument("--saida", default=os.path.join(RAIZ, "models"))
    a = ap.parse_args()
    treinar(a.dados, a.saida)
