import pytest

from chatbot import intents as I
from tests.fixtures import BAIRROS


@pytest.mark.parametrize("texto,esperada", [
    ("Tem um buraco enorme na minha rua", "Buraco na via"),
    ("o poste da esquina está apagado há uma semana", "Iluminação pública apagada"),
    ("jogaram entulho na calçada de casa", "Descarte irregular de lixo"),
    ("a árvore está inclinada e vai cair", "Árvore com risco de queda"),
    ("preciso de poda, os galhos batem na fiação", "Poda de árvore"),
    ("o bueiro está entupido e alaga quando chove", "Bueiro entupido"),
    ("o semáforo da avenida quebrou", "Sinalização de trânsito danificada"),
    ("a calçada está quebrada, cadeirante não passa", "Calçada danificada"),
    ("tem um buraquo grande na rua", "Buraco na via"),  # erro de digitação
])
def test_categoria_clara(texto, esperada):
    assert I.classificar_categoria(texto)["categoria"] == esperada


def test_categoria_ambigua_nao_chuta():
    r = I.classificar_categoria("tem uma árvore perto da minha casa")
    assert r["categoria"] is None and len(r["candidatas"]) >= 2


def test_texto_sem_relacao():
    assert I.classificar_categoria("qual a previsão do tempo?")["ranking"] == []


def test_buraco_na_calcada_vai_para_calcada():
    assert I.classificar_categoria("buraco na calçada")["categoria"] == "Calçada danificada"


@pytest.mark.parametrize("texto,intencao", [
    ("oi", "SAUDACAO"), ("Bom dia!", "SAUDACAO"),
    ("quero registrar um problema", "REGISTRAR"),
    ("tem um buraco na minha rua", "REGISTRAR"),
    ("como está a ocorrência 15?", "CONSULTAR_STATUS"),
    ("status do protocolo 22", "CONSULTAR_STATUS"),
    ("o que significa prioridade ALTA?", "EXPLICAR_PRIORIDADE"),
    ("quanto tempo demora para resolver?", "EXPLICAR_PREVISAO"),
    ("como apoio uma ocorrência?", "COMO_APOIAR"),
    ("recomeçar", "CANCELAR_FLUXO"), ("tchau", "DESPEDIDA"), ("muito obrigado", "AGRADECIMENTO"),
    ("quero cancelar minha ocorrência", "ALTERAR_OCORRENCIA"),
    ("ajuda", "AJUDA"), ("   ", "VAZIA"), ("blablabla xyz", "DESCONHECIDA"),
])
def test_intencoes(texto, intencao):
    assert I.detectar_intencao(texto) == intencao


@pytest.mark.parametrize("texto,ident", [("ocorrência 15", 15), ("#7", 7), ("protocolo 123", 123),
                                         ("42", 42), ("sem número", None)])
def test_extrair_id(texto, ident):
    assert I.extrair_id(texto) == ident


@pytest.mark.parametrize("texto,nome", [("moro na Lapa", "Lapa"), ("Capão Redondo", "Capão Redondo"),
                                        ("capao redondo mesmo", "Capão Redondo"),
                                        ("Pinhieros", "Pinheiros"), ("Sé", "Sé")])
def test_bairro_encontrado(texto, nome):
    assert I.encontrar_correspondencia(texto, BAIRROS)["nome"] == nome


def test_se_comum_nao_vira_bairro_se():
    assert I.encontrar_correspondencia("não sei se é aqui", BAIRROS) is None
    assert I.encontrar_correspondencia("Bairro inexistente", BAIRROS) is None


def test_sim_nao():
    assert I.interpretar_sim_nao("Sim, claro") is True
    assert I.interpretar_sim_nao("não") is False
    assert I.interpretar_sim_nao("talvez") is None
