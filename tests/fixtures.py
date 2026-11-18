"""Apoio dos testes. ATENÇÃO: os dados gerados aqui são SINTÉTICOS e servem só para verificar
que o código funciona (pipeline, API, contrato). Não representam o SP156, não vão para data/
nem para models/, e nenhuma métrica obtida com eles pode ser citada como resultado do projeto.
"""
import numpy as np
import pandas as pd

from chatbot.clientes import ApiIndisponivel, NaoEncontrado
from chatbot.intents import CATEGORIAS

SUBPREFEITURAS = ["Lapa", "Pinheiros", "Campo Limpo", "Itaim Paulista", "Sé"]


def dados_sinteticos(n: int = 600, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    cats = list(CATEGORIAS)
    cat = rng.choice(cats, n)
    sub = rng.choice(SUBPREFEITURAS, n)
    mes = rng.integers(1, 13, n)
    dia = rng.integers(0, 7, n)
    prazo = np.array([CATEGORIAS[c]["prazo_dias"] for c in cat])
    dias = np.maximum(0, (prazo * rng.uniform(0.3, 2.0, n)).astype(int))
    return pd.DataFrame({"categoria": cat, "subprefeitura": sub, "mes": mes, "dia_semana": dia,
                         "dias_para_resolver": dias, "nr_prazo_dias": prazo,
                         "atrasou": (dias > prazo).astype(int)})


BAIRROS = [
    {"id": 1, "nome": "Lapa", "subprefeitura": "Lapa"},
    {"id": 2, "nome": "Pinheiros", "subprefeitura": "Pinheiros"},
    {"id": 3, "nome": "Capão Redondo", "subprefeitura": "Campo Limpo"},
    {"id": 4, "nome": "Itaim Paulista", "subprefeitura": "Itaim Paulista"},
    {"id": 5, "nome": "Sé", "subprefeitura": "Sé"},
]


def ocorrencia(id_, cat="Buraco na via", bairro=None, status="ABERTA", apoios=3, **extra):
    base = {
        "id": id_, "descricao": "Buraco grande na faixa da direita, perto do ponto de ônibus",
        "endereco": "Rua Guaicurus, 1200", "status": status, "dataAbertura": "2026-11-10",
        "dataResolucao": None,
        "categoria": {"id": 1, "nome": cat, "prazoDias": CATEGORIAS[cat]["prazo_dias"],
                      "gravidade": CATEGORIAS[cat]["gravidade"], "orgao": CATEGORIAS[cat]["orgao"]},
        "bairro": bairro or BAIRROS[0], "autor": "Mariana Souza Lima",
        "prazoPrevistoDias": 12, "riscoAtraso": "S", "qtdApoios": apoios, "diasEmAberto": 1,
        "atrasada": False, "pontuacaoPrioridade": 62, "prioridade": "MEDIA",
        # campos que NUNCA podem vazar (RN13), colocados de propósito para o teste
        "email": "mariana@exemplo.com", "telefone": "11 99999-0000",
    }
    base.update(extra)
    return base


class ZelaFalsa:
    """Simula a API Java."""

    def __init__(self, ocorrencias=None, fora=False, bairros=None):
        self.lista = ocorrencias or []
        self.fora = fora
        self.bairros_ = BAIRROS if bairros is None else bairros
        self.chamadas = []

    def _checa(self):
        if self.fora:
            raise ApiIndisponivel("fora do ar")

    def bairros(self):
        self._checa()
        return self.bairros_

    def categorias(self):
        self._checa()
        return []

    def ocorrencias(self, status=None, id_bairro=None, id_categoria=None):
        self._checa()
        self.chamadas.append(("ocorrencias", status, id_bairro, id_categoria))
        return [o for o in self.lista if id_bairro is None or o["bairro"]["id"] == id_bairro]

    def ocorrencia(self, ident):
        self._checa()
        for o in self.lista:
            if o["id"] == ident:
                return o
        raise NaoEncontrado(str(ident))


class IAFalsa:
    """Simula o ClienteIA. Registra os argumentos para conferir o contrato."""

    def __init__(self, fora=False, prazo=12, proba=0.73, cobertas=None):
        self.fora, self.prazo, self.proba = fora, prazo, proba
        self.cobertas = cobertas  # None = todas as categorias têm histórico
        self.chamadas = []

    def categorias_cobertas(self):
        return self.cobertas

    def prever(self, categoria, subprefeitura, mes, dia_semana):
        self.chamadas.append((categoria, subprefeitura, mes, dia_semana))
        if self.fora:
            raise ApiIndisponivel("IA fora do ar")
        return {"prazo_previsto_dias": self.prazo, "risco_atraso": "S" if self.proba >= .5 else "N",
                "probabilidade": self.proba}
