"""O regressor do prazo (log1p) tem que prever dias >= 0 e sobreviver ao joblib (a API o carrega)."""
import io

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from ml_utils import FEATURES, montar_regressor


def _dados():
    rng = np.random.default_rng(0)
    n = 400
    d = pd.DataFrame({"categoria": rng.choice(["Buraco na via", "Poda de árvore"], n),
                      "subprefeitura": rng.choice(["Sé", "Lapa", "Mooca"], n),
                      "mes": rng.integers(1, 13, n), "dia_semana": rng.integers(0, 7, n)})
    d["dias"] = np.where(d.categoria == "Buraco na via", 8, 30) + rng.integers(0, 5, n)
    return d


def test_regressor_log_preve_tempo_tipico_e_nao_negativo():
    d = _dados()
    m = montar_regressor(RandomForestRegressor(n_estimators=20, min_samples_leaf=5, random_state=0)).fit(d[FEATURES], d["dias"])
    p = m.predict(d[FEATURES])
    assert (p >= 0).all()
    assert abs(p[d.categoria == "Buraco na via"].mean() - 10) < 3 and abs(p[d.categoria == "Poda de árvore"].mean() - 32) < 4


def test_regressor_sobrevive_ao_joblib_e_ignora_mes():
    d = _dados()
    m = montar_regressor(RandomForestRegressor(n_estimators=10, random_state=0)).fit(d[FEATURES], d["dias"])
    buf = io.BytesIO(); joblib.dump(m, buf); buf.seek(0); m2 = joblib.load(buf)
    a = d[FEATURES].iloc[:1].copy(); b = a.assign(mes=(a.mes % 12) + 1)
    assert m2.predict(a)[0] == m2.predict(b)[0]            # o mês não entra no modelo
    assert m2.predict(a.assign(subprefeitura="Nunca vista"))[0] > 0   # categoria desconhecida não quebra
