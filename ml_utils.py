"""Pedaços do pipeline que precisam estar num módulo IMPORTÁVEL.

O joblib grava funções por referência ao módulo. Se `converter_tipos` ficasse num script
(`__main__`) ou num notebook, a API Flask não conseguiria carregar o .joblib depois.
Por isso notebooks, scripts/treinar_modelos.py e app.py importam daqui.
"""
import numpy as np
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder

# Só o que existe no momento da abertura (nunca a data de encerramento).
FEATURES = ["categoria", "subprefeitura", "mes", "dia_semana"]


def converter_tipos(d):
    """A API envia mes e dia_semana como inteiros; o OneHotEncoder os trata como categorias
    (sazonalidade não é linear: dezembro não é 'maior' que janeiro)."""
    return d.assign(mes=d["mes"].astype(str), dia_semana=d["dia_semana"].astype(str))


def montar_pipeline(modelo, usar_mes: bool = False):
    """Pipeline completo. A API continua RECEBENDO `mes` (contrato do Documento Base), mas por padrão
    o modelo NÃO o usa: no teste "no tempo" (treina 2020–2022, testa 2023) o mês piora o resultado, porque
    aprende o que aconteceu em cada mês daqueles anos. Veja a comparação nos notebooks 02 e 03."""
    colunas = FEATURES if usar_mes else [c for c in FEATURES if c != "mes"]
    return Pipeline([
        ("tipos", FunctionTransformer(converter_tipos, validate=False)),
        ("prep", ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), colunas)])),
        ("modelo", modelo),
    ])


def montar_regressor(modelo, usar_mes: bool = False):
    """Regressor do PRAZO: o pipeline acima treinado sobre log(1 + dias).

    O tempo de resolução tem cauda muito longa (poucos chamados levam centenas de dias). Treinando em dias
    brutos, a floresta prevê a MÉDIA, puxada por essa cauda, e erra mais (MAE) do que a mediana. No log, a
    previsão volta (expm1) como algo próximo do tempo TÍPICO, que é o que faz sentido mostrar ao cidadão.
    Os notebooks comparam as duas formas."""
    return TransformedTargetRegressor(regressor=montar_pipeline(modelo, usar_mes), func=np.log1p, inverse_func=np.expm1)
