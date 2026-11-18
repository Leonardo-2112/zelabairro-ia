"""Os 4 exemplos oficiais da seção 5.3 do Documento Base (RN10) e a RN11."""
import pytest

from chatbot.regras import calcular_prioridade, dias_em_aberto, esta_atrasada
from datetime import date


@pytest.mark.parametrize("grav,apoios,dias,risco,atrasada,pontos,classe", [
    (5, 3, 2, "S", False, 73, "ALTA"),     # árvore com risco de queda
    (4, 0, 5, "N", False, 45, "MEDIA"),    # buraco na via
    (2, 0, 10, "N", False, 30, "BAIXA"),   # poda de árvore
    (4, 25, 40, None, True, 125, "ALTA"),  # iluminação atrasada (apoios>20 e dias>30 são limitados)
])
def test_exemplos_oficiais(grav, apoios, dias, risco, atrasada, pontos, classe):
    assert calcular_prioridade(grav, apoios, dias, risco, atrasada) == (pontos, classe)


def test_bonus_de_15_soma_uma_vez_so():
    # risco S e atrasada ao mesmo tempo: +15, não +30
    assert calcular_prioridade(3, 0, 0, "S", True)[0] == 45


@pytest.mark.parametrize("pontos_entrada,classe", [((4, 0, 29, "N", False), "MEDIA"),
                                                   ((4, 0, 30, "N", False), "ALTA"),
                                                   ((3, 0, 9, "N", False), "BAIXA"),
                                                   ((3, 0, 10, "N", False), "MEDIA")])
def test_limites_das_classes(pontos_entrada, classe):
    assert calcular_prioridade(*pontos_entrada)[1] == classe


def test_rn11_atrasada_so_acima_do_prazo():
    assert not esta_atrasada(15, 15)
    assert esta_atrasada(16, 15)


def test_dias_em_aberto():
    assert dias_em_aberto(date(2026, 11, 10), date(2026, 11, 11)) == 1
    assert dias_em_aberto(date(2026, 11, 1), date(2026, 11, 30), date(2026, 11, 5)) == 4
