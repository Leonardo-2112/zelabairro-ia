"""Reconhecimento de intenção, de categoria e extração de dados do texto do cidadão.

Abordagem deliberadamente simples e explicável (regras + pontuação de palavras-chave +
correção de erros de digitação). Não há dado rotulado de conversas, então não treinamos
um classificador de intenção: seria inventar dados. Tudo aqui é determinístico e testável.

Os nomes das categorias são EXATAMENTE os da tabela 6.4 do Documento Base.
"""
import difflib
import re
import unicodedata

# --- Catálogo fixo (Documento Base, tabela 6.4) -------------------------------------
CATEGORIAS = {
    "Buraco na via": {"prazo_dias": 15, "gravidade": 4, "orgao": "Subprefeitura - Zeladoria"},
    "Iluminação pública apagada": {"prazo_dias": 7, "gravidade": 4, "orgao": "Iluminação Pública"},
    "Descarte irregular de lixo": {"prazo_dias": 10, "gravidade": 3, "orgao": "Limpeza Urbana"},
    "Árvore com risco de queda": {"prazo_dias": 5, "gravidade": 5, "orgao": "Áreas Verdes"},
    "Poda de árvore": {"prazo_dias": 30, "gravidade": 2, "orgao": "Áreas Verdes"},
    "Calçada danificada": {"prazo_dias": 30, "gravidade": 3, "orgao": "Subprefeitura - Zeladoria"},
    "Bueiro entupido": {"prazo_dias": 10, "gravidade": 4, "orgao": "Subprefeitura - Zeladoria"},
    "Sinalização de trânsito danificada": {"prazo_dias": 10, "gravidade": 3,
                                           "orgao": "Trânsito e Sinalização"},
}
STATUS = ("ABERTA", "EM_ANDAMENTO", "RESOLVIDA", "CANCELADA")

# Palavras-chave por categoria: {termo: peso}. Termo terminado em * = qualquer sufixo.
PALAVRAS_CATEGORIA = {
    "Buraco na via": {
        "buraco": 3, "buracos": 3, "cratera": 3, "esburacad*": 3, "asfalto": 2,
        "tapa buraco": 3, "pista quebrada": 3, "rua quebrada": 2,
    },
    "Iluminação pública apagada": {
        "poste": 3, "postes": 3, "iluminacao": 3, "lampada": 3, "lampadas": 3,
        "apagad*": 2, "escur*": 2, "sem luz": 3, "luz da rua": 3, "falta de luz": 2,
    },
    "Descarte irregular de lixo": {
        "lixo": 3, "lixos": 3, "entulho": 3, "descarte": 3, "descartad*": 2,
        "sujeira": 2, "resto de obra": 3, "colchao": 2, "sofa": 2, "dejeto": 2,
    },
    "Árvore com risco de queda": {
        "arvore": 1, "arvores": 1, "queda": 3, "cair": 3, "caindo": 3, "cai": 2,
        "tombad*": 3, "inclinad*": 3, "risco de queda": 4, "vai cair": 4,
        "apodrecid*": 2, "tronco": 2, "perigo": 1,
    },
    "Poda de árvore": {
        "arvore": 1, "arvores": 1, "poda": 3, "podar": 3, "podada": 2, "galho": 2,
        "galhos": 2, "cortar galho": 3, "corte de arvore": 2, "fiacao": 2, "folhagem": 1,
    },
    "Calçada danificada": {
        # "calcada" sozinha pesa pouco: "entulho na calçada" é lixo, não calçada danificada
        "calcada": 1, "calcadas": 1, "quebrad*": 1, "danificad*": 1, "passeio": 1,
        "calcada quebrada": 3, "calcada danificada": 3, "calcada rachada": 3,
        "calcada esburacada": 3, "calcamento": 3, "piso quebrado": 3, "cadeirante": 2,
        "buraco na calcada": 5,
    },
    "Bueiro entupido": {
        "bueiro": 3, "bueiros": 3, "boca de lobo": 4, "entupid*": 3, "alagamento": 2,
        "alag*": 2, "enchente": 2, "galeria": 1, "agua acumulada": 2, "esgoto": 1,
    },
    "Sinalização de trânsito danificada": {
        "semaforo": 3, "semaforos": 3, "placa": 2, "placas": 2, "faixa de pedestre": 3,
        "sinalizacao": 3, "sinal de transito": 3, "lombada": 2, "sinal quebrado": 3,
        "placa de transito": 3,
    },
}

# Palavras que não ajudam a achar o nome do bairro
_FILLER = r"\b(no|na|nos|nas|do|da|de|em|bairro|distrito|moro|mora|fica|fico|estou|e|o|a|subprefeitura|na regiao|regiao)\b"


def normalizar(texto: str) -> str:
    """minúsculas, sem acento, sem pontuação, espaços únicos (mantém # para ids)."""
    t = unicodedata.normalize("NFKD", texto or "")
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    t = re.sub(r"[^\w\s#]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _padrao(termo: str) -> re.Pattern:
    if termo.endswith("*"):
        return re.compile(r"\b" + re.escape(termo[:-1]) + r"\w*")
    return re.compile(r"\b" + re.escape(termo) + r"\b")


_PADROES_CAT = {
    cat: [(_padrao(t), peso) for t, peso in termos.items()]
    for cat, termos in PALAVRAS_CATEGORIA.items()
}
# vocabulário de palavras simples para corrigir erros de digitação ("buraquo" -> "buraco")
_VOCAB = sorted({t for termos in PALAVRAS_CATEGORIA.values() for t in termos
                 if " " not in t and not t.endswith("*") and len(t) >= 5})


def _corrigir_digitacao(t: str) -> str:
    """Corrige erros de digitação só quando a palavra é MUITO parecida: mesmo início e tamanho
    quase igual. Evita 'quebrada' virar 'queda'."""
    palavras = []
    for p in t.split():
        if len(p) >= 5 and p not in _VOCAB:
            candidatos = [v for v in _VOCAB if v[:2] == p[:2] and abs(len(v) - len(p)) <= 1]
            m = difflib.get_close_matches(p, candidatos, n=1, cutoff=0.75)
            if m:
                p = m[0]
        palavras.append(p)
    return " ".join(palavras)


def classificar_categoria(texto: str) -> dict:
    """Pontua cada categoria pelo texto.

    Devolve {"ranking": [(categoria, pontos), ...] (só pontos > 0),
             "categoria": nome ou None,   # só quando há confiança
             "candidatas": [nomes]}       # quando há dúvida (até 3)
    Confiança: melhor >= 3 pontos e vantagem >= 2 sobre a segunda, ou única categoria com >= 2.
    """
    t = _corrigir_digitacao(normalizar(texto))
    pontos = {}
    for cat, padroes in _PADROES_CAT.items():
        total = sum(peso for pad, peso in padroes if pad.search(t))
        if total > 0:
            pontos[cat] = total
    ranking = sorted(pontos.items(), key=lambda x: (-x[1], x[0]))
    categoria, candidatas = None, []
    if ranking:
        melhor = ranking[0][1]
        segundo = ranking[1][1] if len(ranking) > 1 else 0
        unica = len(ranking) == 1 and melhor >= 2  # só uma categoria bateu e com 2+ pontos
        if (melhor >= 3 and melhor - segundo >= 2) or unica:
            categoria = ranking[0][0]
        else:
            candidatas = [c for c, _ in ranking[:3]]
    return {"ranking": ranking, "categoria": categoria, "candidatas": candidatas}


# --- Intenções ----------------------------------------------------------------------
_RE_ID = re.compile(r"(?:\b(?:ocorrencia|protocolo|numero|num|nro|no|n|id)|#)\s*[:#.]?\s*(\d{1,9})\b")


def extrair_id(texto: str) -> int | None:
    """Acha o número da ocorrência ('ocorrência 15', '#15', 'protocolo 15' ou só '15')."""
    t = normalizar(texto)
    m = _RE_ID.search(t) or re.fullmatch(r"#?\s*(\d{1,9})", t)
    return int(m.group(1)) if m else None


def detectar_intencao(texto: str) -> str:
    """Devolve uma destas intenções:
    VAZIA, ALTERAR_OCORRENCIA, CANCELAR_FLUXO, DESPEDIDA, AGRADECIMENTO, CONSULTAR_STATUS,
    EXPLICAR_PRIORIDADE, EXPLICAR_PREVISAO, COMO_APOIAR, COMO_ACOMPANHAR, REGISTRAR,
    AJUDA, SAUDACAO, DESCONHECIDA
    """
    t = normalizar(texto)
    if not t:
        return "VAZIA"
    if re.search(r"\b(editar|alterar|corrigir|excluir|apagar|deletar|cancelar)\b.*"
                 r"\b(ocorrencia|registro|reclamacao|pedido)\b", t):
        return "ALTERAR_OCORRENCIA"
    if re.search(r"\b(recomecar|reiniciar|comecar de novo|voltar ao inicio|deixa pra la|"
                 r"esquece isso|cancelar tudo|cancelar|desistir)\b", t):
        return "CANCELAR_FLUXO"
    if re.search(r"\b(tchau|ate logo|ate mais|adeus|encerrar|ate a proxima|flw|falou)\b", t):
        return "DESPEDIDA"
    if re.search(r"\b(obrigad[oa]|valeu|agradeco|grat[oa])\b", t):
        return "AGRADECIMENTO"
    if extrair_id(texto) is not None and not re.fullmatch(r"#?\s*\d+", t) \
            or re.search(r"\b(status|andamento|situacao|protocolo)\b", t):
        return "CONSULTAR_STATUS"
    if re.search(r"\b(prioridade|prioridades|urgencia|urgente|classe)\b", t) or \
            re.search(r"significa\s+(alta|media|baixa)", t):
        return "EXPLICAR_PRIORIDADE"
    if re.search(r"\b(prazo|prazos|previsao|previsto|estimativa|quanto tempo|demora|demorar|"
                 r"quando (vai|sera)|risco de atraso|atraso|atrasada)\b", t):
        return "EXPLICAR_PREVISAO"
    if re.search(r"\b(apoiar|apoio|apoios|apoiei|apoiado|ja (existe|reclamaram|registraram)|"
                 r"eu tambem)\b", t):
        return "COMO_APOIAR"
    if re.search(r"\b(acompanhar|historico|minhas ocorrencias|ver ocorrencia)\b", t):
        return "COMO_ACOMPANHAR"
    if re.search(r"\b(registrar|reclamar|denunciar|comunicar|relatar|reportar|avisar|"
                 r"abrir ocorrencia|criar ocorrencia|nova ocorrencia|tem um problema|"
                 r"ha um problema|existe um problema)\b", t):
        return "REGISTRAR"
    if re.search(r"\b(ajuda|ajudar|o que (voce )?(faz|pode)|como funciona|menu|opcoes|help|comandos)\b", t):
        return "AJUDA"
    if re.match(r"(oi|ola|oie|opa|e ai|bom dia|boa tarde|boa noite|hello|hey|salve)\b", t):
        return "SAUDACAO"
    if classificar_categoria(texto)["ranking"]:
        return "REGISTRAR"
    return "DESCONHECIDA"


# --- Extração de campos -------------------------------------------------------------
def interpretar_sim_nao(texto: str) -> bool | None:
    t = normalizar(texto)
    if re.match(r"(sim|s|isso|claro|quero|pode|ok|certo|confirmo|aham|uhum|com certeza)\b", t):
        return True
    if re.match(r"(nao|n|negativo|nem|jamais)\b", t):
        return False
    return None


def encontrar_correspondencia(texto: str, itens: list[dict], chave: str = "nome") -> dict | None:
    """Acha o item (bairro, subprefeitura...) citado no texto.

    1) nome contido no texto (mais longo primeiro); 2) correspondência aproximada quando o
    texto é curto. Nomes de até 3 letras (ex.: 'Sé') só valem se forem a resposta inteira,
    para 'se' (palavra comum) não virar o bairro Sé.
    """
    t = normalizar(texto)
    limpo = re.sub(r"\s+", " ", re.sub(_FILLER, " ", t)).strip()
    por_nome = {}
    for it in itens:
        por_nome.setdefault(normalizar(it[chave]), it)
    for n in sorted(por_nome, key=len, reverse=True):
        if not n:
            continue
        if len(n) <= 3:
            if limpo == n:
                return por_nome[n]
        elif f" {n} " in f" {t} ":
            return por_nome[n]
    if 0 < len(limpo.split()) <= 4:
        m = difflib.get_close_matches(limpo, [n for n in por_nome if len(n) > 3], n=1, cutoff=0.8)
        if m:
            return por_nome[m[0]]
    return None


def escolher_numero(texto: str, maximo: int) -> int | None:
    """Número de 1..maximo digitado pelo cidadão (escolha em uma lista)."""
    m = re.search(r"\b(\d{1,3})\b", normalizar(texto))
    if m and 1 <= int(m.group(1)) <= maximo:
        return int(m.group(1))
    return None
