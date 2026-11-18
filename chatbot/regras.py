"""Regras de negócio do Documento Base (RN10 e RN11) que o chatbot precisa conhecer.

RN10 (prioridade) e RN11 (atrasada) são CALCULADAS pela API Java. Aqui elas existem
apenas para (1) explicar a fórmula ao cidadão com um exemplo e (2) testar que o
nosso entendimento bate com os exemplos oficiais da seção 5.3 do documento.
O chatbot nunca recalcula a prioridade de uma ocorrência real: usa o valor da API.
"""
from datetime import date


def esta_atrasada(dias_em_aberto: int, prazo_dias: int) -> bool:
    """RN11: atrasada = dias em aberto MAIOR que o prazo de referência da categoria."""
    return dias_em_aberto > prazo_dias


def dias_em_aberto(abertura: date, hoje: date, resolucao: date | None = None) -> int:
    """Dias inteiros entre a abertura e hoje (ou a resolução, se já resolvida)."""
    fim = resolucao or hoje
    return (fim - abertura).days


def calcular_prioridade(gravidade: int, qtd_apoios: int, dias: int,
                        risco_atraso: str | None, atrasada: bool) -> tuple[int, str]:
    """RN10: devolve (pontos, classe).

    pontos = gravidade*10 + min(apoios,20)*2 + min(dias,30)
             + 15 (se risco_atraso == 'S' OU atrasada; soma uma vez só)
    classe: >=70 ALTA | 40..69 MEDIA | <40 BAIXA
    """
    pontos = gravidade * 10 + min(qtd_apoios, 20) * 2 + min(dias, 30)
    if risco_atraso == "S" or atrasada:
        pontos += 15
    if pontos >= 70:
        classe = "ALTA"
    elif pontos >= 40:
        classe = "MEDIA"
    else:
        classe = "BAIXA"
    return pontos, classe
