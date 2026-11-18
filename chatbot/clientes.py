"""Clientes HTTP: API Java do ZelaBairro e API de IA (Flask).

RN12: se qualquer API estiver fora do ar, o chatbot continua conversando.
Toda falha de rede vira ApiIndisponivel e quem chama decide o fallback.
"""
import logging

import requests

log = logging.getLogger("zelabairro.clientes")
TIMEOUT = 8  # segundos. O Render gratuito pode demorar ~1 min para acordar.


class ApiIndisponivel(Exception):
    """API fora do ar, lenta demais ou com resposta inesperada."""


class NaoEncontrado(Exception):
    """A API respondeu 404."""


def _get(url: str, params: dict | None = None, timeout: int = TIMEOUT):
    try:
        r = requests.get(url, params=params, timeout=timeout)
    except requests.RequestException as e:
        raise ApiIndisponivel(str(e)) from e
    if r.status_code == 404:
        raise NaoEncontrado(url)
    if r.status_code >= 400:
        raise ApiIndisponivel(f"HTTP {r.status_code} em {url}")
    try:
        return r.json()
    except ValueError as e:
        raise ApiIndisponivel("resposta não é JSON") from e


class ClienteZelaAPI:
    """Consome a API Java (Documento Base 8.2). Sem base_url = sempre indisponível."""

    def __init__(self, base_url: str = ""):
        self.base = (base_url or "").rstrip("/")

    @property
    def configurada(self) -> bool:
        return bool(self.base)

    def _url(self, caminho: str) -> str:
        if not self.base:
            raise ApiIndisponivel("ZELA_API_URL não configurada")
        return self.base + caminho

    def bairros(self) -> list[dict]:
        return _get(self._url("/bairros"))

    def categorias(self) -> list[dict]:
        return _get(self._url("/categorias"))

    def ocorrencias(self, status: str | None = None, id_bairro: int | None = None,
                    id_categoria: int | None = None) -> list[dict]:
        params = {k: v for k, v in (("status", status), ("idBairro", id_bairro),
                                    ("idCategoria", id_categoria)) if v is not None}
        return _get(self._url("/ocorrencias"), params)

    def ocorrencia(self, ident: int) -> dict:
        return _get(self._url(f"/ocorrencias/{int(ident)}"))


class ClienteIA:
    """Consome a API Flask de IA (Documento Base 7.3).

    Com base_url (variável IA_API_URL) faz HTTP de verdade. Sem base_url usa o mesmo
    código dos endpoints /prever/* dentro do processo (predictor.py), útil na demo local.
    Nos dois casos o valor vem do modelo treinado, nunca de texto fixo.
    """

    def __init__(self, base_url: str = ""):
        self.base = (base_url or "").rstrip("/")

    def _post(self, rota: str, payload: dict) -> dict:
        if self.base:
            try:
                r = requests.post(self.base + rota, json=payload, timeout=TIMEOUT)
            except requests.RequestException as e:
                raise ApiIndisponivel(str(e)) from e
            if r.status_code != 200:
                raise ApiIndisponivel(f"HTTP {r.status_code} em {rota}")
            try:
                return r.json()
            except ValueError as e:
                raise ApiIndisponivel("resposta não é JSON") from e
        import predictor  # import tardio: evita ciclo e só carrega sklearn se precisar
        try:
            funcao = predictor.prever_prazo if rota.endswith("prazo") else predictor.prever_atraso
            return funcao(payload)
        except (predictor.ModeloIndisponivel, predictor.ErroEntrada) as e:
            raise ApiIndisponivel(str(e)) from e

    def categorias_cobertas(self):
        """Conjunto de categorias com histórico no treino, ou None se não der para saber
        (nesse caso o chatbot assume que todas têm)."""
        try:
            if self.base:
                try:
                    r = requests.get(self.base + "/modelo/info", timeout=TIMEOUT)
                except requests.RequestException as e:
                    raise ApiIndisponivel(str(e)) from e
                if r.status_code != 200:
                    return None
                return set(r.json().get("categorias_cobertas", []))
            import predictor
            return set(predictor.info()["categorias_cobertas"])
        except Exception:
            return None

    def prever(self, categoria: str, subprefeitura: str, mes: int, dia_semana: int) -> dict:
        """Devolve {"prazo_previsto_dias", "risco_atraso", "probabilidade"}."""
        payload = {"categoria": categoria, "subprefeitura": subprefeitura,
                   "mes": mes, "dia_semana": dia_semana}
        prazo = self._post("/prever/prazo", payload)
        atraso = self._post("/prever/atraso", payload)
        try:
            return {"prazo_previsto_dias": int(prazo["prazo_previsto_dias"]),
                    "risco_atraso": atraso["risco_atraso"],
                    "probabilidade": float(atraso["probabilidade"])}
        except (KeyError, TypeError, ValueError) as e:
            raise ApiIndisponivel("resposta da IA fora do contrato") from e
