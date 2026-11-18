"""Máquina de estados do chatbot ZelaBairro.

Fluxo de registro (Documento Base 4.2):
  descrição -> categoria -> bairro -> [ocorrências parecidas? apoiar (RN07)] -> endereço
  -> previsão de prazo/risco (modelos de IA) -> resumo e orientação para registrar.

O chatbot NÃO grava ocorrências: a gravação é feita pelo front/API Java com o cidadão
identificado (nome e e-mail). Aqui ele coleta, valida (RN03), evita duplicados (RN07),
mostra a previsão e orienta. RN12: nada aqui depende da IA ou da API Java estar no ar.
"""
import threading
import time
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from . import intents as I
from . import responses as R
from .clientes import ApiIndisponivel, NaoEncontrado

FUSO = ZoneInfo("America/Sao_Paulo")
ESTADOS_ATIVOS = ("ABERTA", "EM_ANDAMENTO")  # RN07
EXEMPLOS_BAIRROS = ["Lapa", "Pinheiros", "Capão Redondo", "Itaim Paulista", "Sé"]


class GerenciadorSessoes:
    """Guarda a conversa de cada visitante em memória (com validade e limite)."""

    def __init__(self, ttl_segundos: int = 3600, maximo: int = 5000):
        self.ttl, self.maximo = ttl_segundos, maximo
        self._d: dict[str, dict] = {}
        self._lock = threading.Lock()

    def obter(self, sid: str) -> dict:
        agora = time.time()
        with self._lock:
            if len(self._d) > self.maximo:  # limpeza simples das mais antigas
                for k in sorted(self._d, key=lambda k: self._d[k]["_visto"])[: self.maximo // 10]:
                    self._d.pop(k, None)
            s = self._d.get(sid)
            if s is None or agora - s["_visto"] > self.ttl:
                s = self._d[sid] = self._nova()
            s["_visto"] = agora
            return s

    @staticmethod
    def _nova() -> dict:
        return {"estado": None, "dados": {}, "incompreendidas": 0, "_visto": time.time()}


class Chatbot:
    def __init__(self, cliente_zela, cliente_ia, front_url: str = "", agora=None):
        self.zela, self.ia, self.front = cliente_zela, cliente_ia, front_url
        self.agora = agora or (lambda: datetime.now(FUSO))

    # ------------------------------------------------------------------ API pública
    def iniciar(self, sessao: dict, sid: str) -> dict:
        self._resetar(sessao)
        return self._saida(sid, R.boas_vindas(), R.SUGESTOES_INICIAIS)

    def responder(self, sessao: dict, sid: str, texto: str) -> dict:
        texto = (texto or "").strip()
        if not texto:
            return self._saida(sid, R.vazia(), self._sugestoes(sessao))

        intencao = I.detectar_intencao(texto)
        # comandos que valem em qualquer ponto da conversa
        if intencao == "CANCELAR_FLUXO":
            self._resetar(sessao)
            return self._saida(sid, R.recomecar(), R.SUGESTOES_INICIAIS)
        if intencao == "DESPEDIDA":
            self._resetar(sessao)
            return self._saida(sid, R.despedida(), [])

        estado = sessao["estado"]
        if estado in ("DESCRICAO", "ENDERECO") and texto.endswith("?") and intencao in (
                "EXPLICAR_PRIORIDADE", "EXPLICAR_PREVISAO", "AJUDA", "COMO_APOIAR"):
            resp = self._responder_intencao(sessao, intencao, texto)
            return self._saida(sid, resp + "\n\nVoltando ao registro:\n" + self._pergunta_estado(sessao),
                               self._sugestoes(sessao))

        if estado:
            resp = self._tratar_estado(sessao, estado, texto)
        else:
            resp = self._tratar_ocioso(sessao, intencao, texto)
        return self._saida(sid, resp, self._sugestoes(sessao))

    # ------------------------------------------------------------------ utilidades
    @staticmethod
    def _saida(sid: str, resposta: str, sugestoes: list[str]) -> dict:
        return {"sessao": sid, "resposta": resposta, "sugestoes": sugestoes}

    @staticmethod
    def _resetar(sessao: dict):
        sessao["estado"], sessao["dados"], sessao["incompreendidas"] = None, {}, 0

    def _sugestoes(self, sessao: dict) -> list[str]:
        e, d = sessao["estado"], sessao["dados"]
        if e is None:
            return R.SUGESTOES_INICIAIS
        if e == "CATEGORIA":
            return [str(i) for i in range(1, len(d.get("_opcoes_cat", [])) + 1)] + ["Recomeçar"]
        if e == "APOIO":
            return ["nova"] + [str(o["id"]) for o in d.get("_similares", [])[:3]]
        return ["Recomeçar"]

    def _bairros(self):
        """Lista de bairros da API Java, ou None se indisponível."""
        try:
            lista = self.zela.bairros()
            if isinstance(lista, list):
                return [b for b in lista if isinstance(b, dict) and b.get("nome")]
        except ApiIndisponivel:
            pass
        return None

    # ------------------------------------------------------------------ sem fluxo ativo
    def _tratar_ocioso(self, sessao, intencao, texto) -> str:
        if intencao not in ("DESCONHECIDA", "VAZIA"):
            sessao["incompreendidas"] = 0
        if intencao == "REGISTRAR":
            return self._iniciar_registro(sessao, texto)
        if intencao == "DESCONHECIDA":
            sessao["incompreendidas"] += 1
            return R.ajuda() if sessao["incompreendidas"] >= 2 else R.nao_entendi()
        return self._responder_intencao(sessao, intencao, texto)

    def _responder_intencao(self, sessao, intencao, texto) -> str:
        if intencao == "SAUDACAO":
            return R.boas_vindas()
        if intencao == "AJUDA":
            return R.ajuda()
        if intencao == "AGRADECIMENTO":
            return R.agradecimento()
        if intencao == "EXPLICAR_PRIORIDADE":
            return R.explicar_prioridade()
        if intencao == "EXPLICAR_PREVISAO":
            return R.explicar_previsao()
        if intencao == "COMO_APOIAR":
            return R.como_apoiar(self.front)
        if intencao == "COMO_ACOMPANHAR":
            return R.como_acompanhar(self.front)
        if intencao == "ALTERAR_OCORRENCIA":
            return R.alterar_ocorrencia()
        if intencao == "CONSULTAR_STATUS":
            ident = I.extrair_id(texto)
            if ident is None:
                sessao["estado"] = "ID"
                return R.pedir_id()
            return self._consultar(ident)
        return R.nao_entendi()

    # ------------------------------------------------------------------ consulta
    def _consultar(self, ident: int) -> str:
        try:
            return R.formatar_ocorrencia(self.zela.ocorrencia(ident), self.front)
        except NaoEncontrado:
            return R.ocorrencia_nao_encontrada(ident)
        except ApiIndisponivel:
            return R.api_offline_consulta()

    # ------------------------------------------------------------------ registro
    def _iniciar_registro(self, sessao, texto) -> str:
        sessao["dados"] = {}
        d = sessao["dados"]
        cls = I.classificar_categoria(texto)
        # a frase já descreve o problema? ("tem um buraco na rua da Lapa")
        if cls["ranking"] and 10 <= len(texto) <= 500:
            d["descricao"] = texto
            if cls["categoria"]:
                d["categoria"] = cls["categoria"]
            else:
                d["_candidatas"] = cls["candidatas"]
            return self._avancar(sessao, prefixo=self._achar_bairro_no_texto(d, texto))
        sessao["estado"] = "DESCRICAO"
        return R.pedir_descricao()

    def _achar_bairro_no_texto(self, d: dict, texto: str) -> str:
        bairros = self._bairros()
        d["_bairros_ok"] = bairros is not None
        if bairros:
            b = I.encontrar_correspondencia(texto, bairros)
            if b:
                d["bairro"] = b
        return ""

    def _avancar(self, sessao, prefixo: str = "") -> str:
        """Decide a próxima pergunta olhando o que ainda falta."""
        d = sessao["dados"]
        msg = []
        if prefixo:
            msg.append(prefixo)
        if "categoria" not in d:
            return self._pedir_categoria(sessao, msg)
        if "_cat_avisada" not in d:
            d["_cat_avisada"] = True
            msg.append(R.categoria_entendida(d["categoria"]))
        if "bairro" not in d and "subprefeitura" not in d:
            if "_bairros_ok" not in d:
                d["_bairros_ok"] = self._bairros() is not None
            if d["_bairros_ok"]:
                sessao["estado"] = "BAIRRO"
                msg.append(R.pedir_bairro())
            else:
                msg.append(R.api_offline_registro())
                sessao["estado"] = "SUBPREF"
                msg.append(R.pedir_subprefeitura())
            return "\n".join(msg)
        if "bairro" in d and "_similares_checados" not in d:
            d["_similares_checados"] = True
            msg.append(R.bairro_confirmado(d["bairro"]))
            similares = self._buscar_similares(d)
            if similares is None:
                msg.append(R.api_offline_registro())
            elif similares:
                d["_similares"] = similares
                sessao["estado"] = "APOIO"
                msg.append(R.sugerir_apoio(similares))
                return "\n".join(msg)
            else:
                msg.append(R.sem_similares())
        if "endereco" not in d:
            sessao["estado"] = "ENDERECO"
            msg.append(R.pedir_endereco())
            return "\n".join(msg)
        return self._finalizar(sessao, msg)

    def _pedir_categoria(self, sessao, msg: list) -> str:
        d = sessao["dados"]
        opcoes = d.get("_candidatas") or list(I.CATEGORIAS)
        d["_opcoes_cat"] = opcoes
        sessao["estado"] = "CATEGORIA"
        msg.append(R.pedir_categoria(opcoes))
        return "\n".join(msg)

    def _buscar_similares(self, d: dict):
        """RN07: ocorrências ABERTA/EM_ANDAMENTO da mesma categoria e bairro. None = API fora."""
        try:
            lista = self.zela.ocorrencias(id_bairro=d["bairro"].get("id"))
        except ApiIndisponivel:
            return None
        out = []
        for o in lista if isinstance(lista, list) else []:
            if o.get("status") in ESTADOS_ATIVOS and (o.get("categoria") or {}).get("nome") == d["categoria"]:
                out.append(o)
        return out[:5]  # a API já devolve ordenado por prioridade

    def _finalizar(self, sessao, msg: list) -> str:
        d = sessao["dados"]
        sub = d["bairro"]["subprefeitura"] if "bairro" in d else d["subprefeitura"]
        bairro = d.get("bairro") or {"nome": "(não informado)", "subprefeitura": sub}
        agora = self.agora()
        previsao, sem_historico = None, False
        cobertas = self.ia.categorias_cobertas() if hasattr(self.ia, "categorias_cobertas") else None
        if cobertas is not None and d["categoria"] not in cobertas:
            sem_historico = True  # não inventa previsão para categoria que o modelo nunca viu
        else:
            try:
                previsao = self.ia.prever(d["categoria"], sub, agora.month, agora.weekday())
            except ApiIndisponivel:
                previsao = None  # RN12: o registro nunca depende da IA
        resumo = R.resumo_registro(
            {"categoria": d["categoria"], "bairro": bairro, "endereco": d["endereco"],
             "descricao": d["descricao"]},
            previsao, I.CATEGORIAS[d["categoria"]]["prazo_dias"], self.front, sem_historico)
        self._resetar(sessao)
        return "\n".join(msg + [resumo])

    def _pergunta_estado(self, sessao) -> str:
        e = sessao["estado"]
        d = sessao["dados"]
        if e == "DESCRICAO":
            return R.pedir_descricao()
        if e == "ENDERECO":
            return R.pedir_endereco()
        if e == "CATEGORIA":
            return R.pedir_categoria(d.get("_opcoes_cat", []))
        if e == "BAIRRO":
            return R.pedir_bairro()
        if e == "SUBPREF":
            return R.pedir_subprefeitura()
        if e == "APOIO":
            return R.sugerir_apoio(d.get("_similares", []))
        return R.pedir_id()

    # ------------------------------------------------------------------ respostas por estado
    def _tratar_estado(self, sessao, estado, texto) -> str:
        d = sessao["dados"]

        if estado == "ID":
            ident = I.extrair_id(texto)
            if ident is None:
                return R.pedir_id()
            sessao["estado"] = None
            return self._consultar(ident)

        if estado == "DESCRICAO":
            n = len(texto)
            if not 10 <= n <= 500:  # RN03
                return R.descricao_invalida(n)
            d["descricao"] = texto
            cls = I.classificar_categoria(texto)
            if cls["categoria"]:
                d["categoria"] = cls["categoria"]
            else:
                d["_candidatas"] = cls["candidatas"]
            return self._avancar(sessao, prefixo=self._achar_bairro_no_texto(d, texto))

        if estado == "CATEGORIA":
            opcoes = d.get("_opcoes_cat") or list(I.CATEGORIAS)
            n = I.escolher_numero(texto, len(opcoes))
            escolhida = opcoes[n - 1] if n else None
            if not escolhida:
                cls = I.classificar_categoria(texto)
                escolhida = cls["categoria"] or next((c for c in I.CATEGORIAS
                                                      if I.normalizar(c) == I.normalizar(texto)), None)
            if not escolhida:
                return "Não consegui identificar o tipo.\n" + R.pedir_categoria(opcoes)
            d["categoria"] = escolhida
            d.pop("_candidatas", None)
            return self._avancar(sessao)

        if estado == "BAIRRO":
            bairros = self._bairros()
            if bairros is None:  # API caiu no meio da conversa
                d["_bairros_ok"] = False
                return self._avancar(sessao)
            b = I.encontrar_correspondencia(texto, bairros)
            if not b:
                return R.bairro_nao_encontrado(EXEMPLOS_BAIRROS)
            d["bairro"] = b
            return self._avancar(sessao)

        if estado == "SUBPREF":
            nome = " ".join(texto.split())
            if len(nome) < 3 or len(nome) > 80:
                return R.subprefeitura_invalida()
            d["subprefeitura"] = nome.title()
            d["_similares_checados"] = True  # sem API não há como checar parecidas
            return self._avancar(sessao)

        if estado == "APOIO":
            return self._tratar_apoio(sessao, texto)

        if estado == "ENDERECO":
            n = len(texto)
            if not 1 <= n <= 200:  # RN03
                return R.endereco_invalido(n)
            d["endereco"] = texto
            return self._avancar(sessao)

        self._resetar(sessao)
        return R.nao_entendi()

    def _tratar_apoio(self, sessao, texto) -> str:
        d = sessao["dados"]
        similares = d.get("_similares", [])
        t = I.normalizar(texto)
        ids = {o["id"] for o in similares}
        ident = I.extrair_id(texto)
        if ident in ids:
            self._resetar(sessao)
            return R.orientar_apoio(ident, self.front)
        sn = I.interpretar_sim_nao(texto)
        if t.startswith(("nova", "outra", "diferente", "registrar")) or sn is False:
            sessao["estado"] = None
            return self._avancar(sessao)
        if sn is True:
            if len(similares) == 1:
                self._resetar(sessao)
                return R.orientar_apoio(similares[0]["id"], self.front)
            return R.qual_ocorrencia()
        return R.sugerir_apoio(similares)
