"""Carrega os modelos .joblib e faz as previsões. Usado pelos endpoints /prever/*.

Contrato (Documento Base 7.3): entrada {categoria, subprefeitura, mes, dia_semana}.
Só usamos informação disponível na ABERTURA da ocorrência.
"""
import os
import threading

import joblib
import pandas as pd

from chatbot.intents import CATEGORIAS

DIR = os.path.dirname(os.path.abspath(__file__))
CAMINHO_PRAZO = os.environ.get("MODELO_PRAZO", os.path.join(DIR, "models", "modelo_prazo.joblib"))
CAMINHO_ATRASO = os.environ.get("MODELO_ATRASO", os.path.join(DIR, "models", "modelo_atraso.joblib"))
FEATURES = ["categoria", "subprefeitura", "mes", "dia_semana"]


class ErroEntrada(ValueError):
    """Entrada inválida -> HTTP 400 com {"erro": "..."}."""


class ModeloIndisponivel(RuntimeError):
    """Arquivo .joblib ausente ou ilegível -> HTTP 503."""


_cache: dict = {}
_lock = threading.Lock()


def _carregar(nome: str, caminho: str):
    with _lock:
        if nome not in _cache:
            if not os.path.exists(caminho):
                raise ModeloIndisponivel(
                    f"modelo '{nome}' não encontrado em {caminho}. Rode scripts/treinar_modelos.py "
                    "ou os notebooks 02 e 03.")
            try:
                _cache[nome] = joblib.load(caminho)
            except Exception as e:  # arquivo corrompido, versão incompatível do sklearn...
                raise ModeloIndisponivel(f"não foi possível ler o modelo '{nome}': {e}") from e
        return _cache[nome]


def limpar_cache():
    with _lock:
        _cache.clear()


def modelos_disponiveis() -> bool:
    try:
        _carregar("prazo", CAMINHO_PRAZO)
        _carregar("atraso", CAMINHO_ATRASO)
        return True
    except ModeloIndisponivel:
        return False


def validar(dados) -> dict:
    """Valida o corpo JSON e devolve um dict limpo. Levanta ErroEntrada."""
    if not isinstance(dados, dict):
        raise ErroEntrada("corpo da requisição deve ser um JSON com categoria, subprefeitura, mes e dia_semana")
    faltando = [c for c in FEATURES if c not in dados or dados[c] in (None, "")]
    if faltando:
        raise ErroEntrada("campo(s) obrigatório(s) ausente(s): " + ", ".join(faltando))
    categoria = dados["categoria"]
    if not isinstance(categoria, str) or categoria not in CATEGORIAS:
        raise ErroEntrada(f"categoria desconhecida: {categoria}")
    sub = dados["subprefeitura"]
    if not isinstance(sub, str) or not sub.strip():
        raise ErroEntrada("subprefeitura deve ser um texto não vazio")
    out = {"categoria": categoria, "subprefeitura": sub.strip()}
    for campo, lo, hi in (("mes", 1, 12), ("dia_semana", 0, 6)):
        v = dados[campo]
        if isinstance(v, bool) or not isinstance(v, int):
            raise ErroEntrada(f"{campo} deve ser um número inteiro entre {lo} e {hi}")
        if not lo <= v <= hi:
            raise ErroEntrada(f"{campo} deve estar entre {lo} e {hi}")
        out[campo] = v
    return out


def _linha(dados: dict) -> pd.DataFrame:
    return pd.DataFrame([dados], columns=FEATURES)


def _pipeline(bundle):
    """O .joblib guarda um dict {"pipeline": ..., "metricas": ...} (ou o próprio pipeline)."""
    return bundle["pipeline"] if isinstance(bundle, dict) else bundle


MINIMO_EXEMPLOS = 200  # abaixo disso, a categoria é considerada SEM histórico suficiente


def info() -> dict:
    """Metadados dos modelos: métricas e quais categorias têm histórico (extra, fora do contrato 7.3)."""
    bundle = _carregar("prazo", CAMINHO_PRAZO)
    cobertura = bundle.get("categorias_treino") if isinstance(bundle, dict) else None
    if cobertura is None:  # modelo antigo, sem a informação: não restringe
        cobertas = sorted(CATEGORIAS)
    else:
        cobertas = sorted(c for c, n in cobertura.items() if n >= MINIMO_EXEMPLOS)
    return {"categorias_cobertas": cobertas,
            "categorias_sem_historico": sorted(set(CATEGORIAS) - set(cobertas)),
            "minimo_exemplos": MINIMO_EXEMPLOS,
            "usa_mes": bool(bundle.get("usa_mes", True)) if isinstance(bundle, dict) else True,
            "categorias_treino": cobertura or {}}


def prever_prazo(dados: dict) -> dict:
    d = validar(dados)
    pipe = _pipeline(_carregar("prazo", CAMINHO_PRAZO))
    dias = float(pipe.predict(_linha(d))[0])
    return {"prazo_previsto_dias": max(1, int(round(dias)))}


def prever_atraso(dados: dict) -> dict:
    d = validar(dados)
    pipe = _pipeline(_carregar("atraso", CAMINHO_ATRASO))
    classes = list(pipe.classes_)
    if 1 not in classes:  # treino sem nenhum atraso: probabilidade 0
        proba = 0.0
    else:
        proba = float(pipe.predict_proba(_linha(d))[0][classes.index(1)])
    return {"risco_atraso": "S" if proba >= 0.5 else "N", "probabilidade": round(proba, 2)}
