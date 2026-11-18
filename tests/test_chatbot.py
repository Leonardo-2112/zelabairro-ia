"""Conversas completas com API Java e IA simuladas."""
import pytest

from chatbot.chatbot import Chatbot, GerenciadorSessoes
from chatbot import responses as R
from tests.fixtures import BAIRROS, IAFalsa, ZelaFalsa, ocorrencia
from datetime import datetime
from zoneinfo import ZoneInfo

HOJE = datetime(2026, 11, 11, 14, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))  # quarta-feira


def conversa(bot=None, zela=None, ia=None):
    zela = zela or ZelaFalsa()
    ia = ia or IAFalsa()
    bot = bot or Chatbot(zela, ia, front_url="https://zela.exemplo.com", agora=lambda: HOJE)
    sessoes = GerenciadorSessoes()

    def dizer(msg):
        return bot.responder(sessoes.obter("s1"), "s1", msg)["resposta"]
    return dizer, zela, ia


def test_boas_vindas_explica_finalidade():
    bot = Chatbot(ZelaFalsa(), IAFalsa())
    r = bot.iniciar(GerenciadorSessoes().obter("a"), "a")
    assert "ZelaBairro" in r["resposta"] and "registrar" in r["resposta"]
    assert r["sugestoes"]


def test_registro_completo_sem_similares_mostra_previsao_da_ia():
    dizer, _, ia = conversa()
    assert "Conte" in dizer("quero registrar um problema")
    r = dizer("Buraco grande na faixa da direita, perto do ponto de ônibus")
    assert "Buraco na via" in r and "bairro" in r.lower()
    r = dizer("Lapa")
    assert "não encontrei ocorrência parecida" in r.lower() and "endereço" in r.lower()
    r = dizer("Rua Guaicurus, 1200")
    assert "12 dias" in r and "risco ALTO" in r and "%" not in r and "estimativa" in r.lower() and "não são uma garantia" in r.lower()
    assert "ABERTA" in r
    # contrato com a IA: nomes canônicos, mês 11 e quarta-feira = 2 (weekday() do Python)
    assert ia.chamadas == [("Buraco na via", "Lapa", 11, 2)]


def test_frase_unica_ja_pega_categoria_e_bairro():
    dizer, *_ = conversa()
    r = dizer("tem um poste apagado na rua da Lapa há uma semana")
    assert "Iluminação pública apagada" in r and "Lapa" in r
    assert "endereço" in r.lower()  # só falta o endereço


def test_rn07_sugere_apoiar_ocorrencia_existente_mesma_categoria_e_bairro():
    zela = ZelaFalsa([
        ocorrencia(15, "Buraco na via", BAIRROS[0], "ABERTA"),
        ocorrencia(16, "Buraco na via", BAIRROS[0], "RESOLVIDA"),         # status inativo: não sugere
        ocorrencia(17, "Poda de árvore", BAIRROS[0], "ABERTA"),            # outra categoria: não sugere
        ocorrencia(18, "Buraco na via", BAIRROS[1], "ABERTA"),             # outro bairro: não sugere
    ])
    dizer, *_ = conversa(zela=zela)
    r = dizer("tem um buraco enorme na minha rua na Lapa")
    assert "Ocorrência 15" in r and "Ocorrência 16" not in r and "Ocorrência 17" not in r
    assert "Ocorrência 18" not in r and "apoiar" in r.lower()
    r = dizer("sim")
    assert "Apoiar" in r and "/ocorrencias/15" in r


def test_rn07_e_sugestao_nao_bloqueio_cidadao_pode_criar_nova():
    zela = ZelaFalsa([ocorrencia(15, "Buraco na via", BAIRROS[0])])
    dizer, *_ = conversa(zela=zela)
    dizer("tem um buraco enorme na minha rua na Lapa")
    r = dizer("nova")
    assert "endereço" in r.lower()
    assert "12 dias" in dizer("Rua das Flores, 10")


def test_varias_similares_pede_numero():
    zela = ZelaFalsa([ocorrencia(15, "Buraco na via", BAIRROS[0]), ocorrencia(20, "Buraco na via", BAIRROS[0])])
    dizer, *_ = conversa(zela=zela)
    dizer("buraco enorme na Lapa na minha rua")
    assert "Qual delas" in dizer("sim")
    assert "/ocorrencias/20" in dizer("20")


def test_rn03_valida_descricao_e_endereco():
    dizer, *_ = conversa()
    dizer("quero registrar")
    assert "curta" in dizer("buraco")                       # 6 caracteres
    assert "longa" in dizer("a" * 501)
    dizer("Buraco grande na faixa da direita")
    dizer("Lapa")
    assert "Não recebi" in dizer("   ")  # mensagem em branco nunca vira endereço
    assert "limite é 200" in dizer("r" * 201)


def test_categoria_ambigua_pergunta_em_vez_de_chutar():
    dizer, *_ = conversa()
    dizer("quero registrar um problema")
    r = dizer("tem uma árvore perto de casa que me preocupa")
    assert "Não tenho certeza" in r and "Poda de árvore" in r and "Árvore com risco de queda" in r
    r = dizer("2")
    assert "Entendi" in r


def test_rn12_ia_fora_do_ar_registro_continua():
    dizer, *_ = conversa(ia=IAFalsa(fora=True))
    dizer("buraco enorme na minha rua na Lapa")
    r = dizer("Rua das Flores, 10")
    assert "Não consegui calcular a previsão" in r and "15 dias" in r and "ABERTA" in r
    assert "None" not in r and "12 dias" not in r


def test_api_java_fora_do_ar_nao_trava_registro():
    dizer, *_ = conversa(zela=ZelaFalsa(fora=True))
    r = dizer("buraco enorme na minha rua")
    assert "não consegui consultar" in r.lower() and "subprefeitura" in r.lower()
    r = dizer("Lapa")
    assert "endereço" in r.lower()
    assert "12 dias" in dizer("Rua das Flores, 10")


def test_consulta_de_ocorrencia_e_rn13_nao_vaza_dados_pessoais():
    zela = ZelaFalsa([ocorrencia(15)])
    dizer, *_ = conversa(zela=zela)
    r = dizer("como está a ocorrência 15?")
    assert "Ocorrência 15" in r and "MEDIA" in r and "Registrada por: Mariana" in r
    assert "Souza" not in r and "Lima" not in r                       # só o primeiro nome
    assert "@" not in r and "99999" not in r and "mariana@" not in r  # RN13
    assert "estimativa" in r.lower()


def test_consulta_pede_numero_e_trata_inexistente():
    dizer, *_ = conversa(zela=ZelaFalsa([ocorrencia(15)]))
    assert "número" in dizer("quero ver o status")
    assert "Não encontrei a ocorrência 99" in dizer("99")
    assert "não consegui falar" in conversa(zela=ZelaFalsa(fora=True))[0]("ocorrência 15").lower()


def test_ocorrencia_encerrada_nao_tem_prioridade():
    oc = ocorrencia(30, status="RESOLVIDA", dataResolucao="2026-11-12", prioridade=None, pontuacaoPrioridade=None)
    r = conversa(zela=ZelaFalsa([oc]))[0]("ocorrência 30")
    assert "sem prioridade" in r and "encerrada em 12/11/2026" in r


def test_explicacoes():
    dizer, *_ = conversa()
    p = dizer("o que significa prioridade ALTA?")
    assert "ALTA" in p and "MEDIA" in p and "BAIXA" in p and "73 pontos" in p  # exemplo oficial
    assert "estimativa" in dizer("quanto tempo demora?").lower()
    assert "Apoiar" in dizer("como apoio uma ocorrência?")


def test_recomecar_e_despedida_em_qualquer_ponto():
    dizer, *_ = conversa()
    dizer("quero registrar")
    assert "recomeçar" in dizer("recomeçar").lower()
    assert "Conte" in dizer("quero registrar")  # voltou ao início
    assert "Até logo" in dizer("tchau")


def test_mensagens_estranhas_nao_quebram():
    dizer, *_ = conversa()
    assert "Não recebi" in dizer("   ")
    assert "não entendi" in dizer("asdf qwer").lower()
    assert "Veja o que eu sei" in dizer("zxcv poiu")  # segunda incompreendida mostra ajuda
    assert dizer("🙂🙂🙂")
    assert "não consigo alterar" in dizer("quero cancelar minha ocorrência").lower()


def test_pergunta_no_meio_do_registro_responde_e_volta():
    dizer, *_ = conversa()
    dizer("quero registrar")
    r = dizer("o que significa prioridade alta?")
    assert "ALTA" in r and "Voltando ao registro" in r and "Conte" in r


def test_bairro_invalido_pede_de_novo():
    dizer, *_ = conversa()
    dizer("buraco enorme na minha rua")
    assert "Não achei esse bairro" in dizer("Atlântida")
    assert "endereço" in dizer("Pinheiros").lower()


def test_sessoes_sao_independentes():
    bot = Chatbot(ZelaFalsa(), IAFalsa(), agora=lambda: HOJE)
    g = GerenciadorSessoes()
    bot.responder(g.obter("a"), "a", "quero registrar")
    assert g.obter("a")["estado"] == "DESCRICAO" and g.obter("b")["estado"] is None


def test_respostas_sempre_terminam_com_aviso_de_estimativa_quando_mostram_previsao():
    dizer, *_ = conversa()
    dizer("buraco enorme na minha rua na Lapa")
    assert R.AVISO_ESTIMATIVA in dizer("Rua das Flores, 10")


def test_categoria_sem_historico_no_modelo_nao_inventa_previsao():
    ia = IAFalsa(cobertas={"Buraco na via"})
    dizer, *_ = conversa(ia=ia)
    dizer("a árvore na minha rua está inclinada e vai cair, na Lapa")
    r = dizer("Rua das Flores, 10")
    assert "histórico suficiente" in r and "5 dias" in r      # cita só o prazo de referência (tabela 6.4)
    assert "12 dias" not in r and "risco ALTO" not in r
    assert ia.chamadas == []                                   # nem chamou o modelo


def test_categoria_com_historico_continua_mostrando_previsao():
    dizer, *_ = conversa(ia=IAFalsa(cobertas={"Buraco na via"}))
    dizer("buraco enorme na minha rua na Lapa")
    assert "12 dias" in dizer("Rua das Flores, 10")
