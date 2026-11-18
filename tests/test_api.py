"""Contrato da API Flask (Documento Base 7.3). Modelos treinados com dados SINTÉTICOS (ver fixtures)."""
import pytest

CORPO = {"categoria": "Buraco na via", "subprefeitura": "Lapa", "mes": 11, "dia_semana": 2}


def test_health(cliente_flask):
    r = cliente_flask.get("/health")
    assert r.status_code == 200 and r.get_json() == {"status": "ok"}


def test_prever_prazo_contrato(cliente_flask):
    r = cliente_flask.post("/prever/prazo", json=CORPO)
    j = r.get_json()
    assert r.status_code == 200 and set(j) == {"prazo_previsto_dias"}
    assert isinstance(j["prazo_previsto_dias"], int) and j["prazo_previsto_dias"] >= 1


def test_prever_atraso_contrato(cliente_flask):
    r = cliente_flask.post("/prever/atraso", json=CORPO)
    j = r.get_json()
    assert r.status_code == 200 and set(j) == {"risco_atraso", "probabilidade"}
    assert j["risco_atraso"] in ("S", "N") and 0 <= j["probabilidade"] <= 1
    assert (j["risco_atraso"] == "S") == (j["probabilidade"] >= 0.5)


def test_categoria_desconhecida_400_com_mensagem_do_contrato(cliente_flask):
    r = cliente_flask.post("/prever/prazo", json={**CORPO, "categoria": "Buraco"})
    assert r.status_code == 400 and r.get_json() == {"erro": "categoria desconhecida: Buraco"}
    assert cliente_flask.post("/prever/atraso", json={**CORPO, "categoria": "Buraco"}).status_code == 400


@pytest.mark.parametrize("alteracao", [
    {"mes": 13}, {"mes": 0}, {"dia_semana": 7}, {"dia_semana": -1}, {"mes": "11"},
    {"mes": True}, {"mes": 11.5}, {"subprefeitura": ""}, {"subprefeitura": 5},
])
def test_entradas_invalidas_400(cliente_flask, alteracao):
    r = cliente_flask.post("/prever/prazo", json={**CORPO, **alteracao})
    assert r.status_code == 400 and "erro" in r.get_json()


def test_campo_ausente_e_corpo_invalido(cliente_flask):
    incompleto = {k: v for k, v in CORPO.items() if k != "mes"}
    r = cliente_flask.post("/prever/prazo", json=incompleto)
    assert r.status_code == 400 and "mes" in r.get_json()["erro"]
    assert cliente_flask.post("/prever/prazo", data="isso nao e json",
                              content_type="application/json").status_code == 400
    assert cliente_flask.post("/prever/prazo", json=[1, 2]).status_code == 400


def test_subprefeitura_nunca_vista_nao_quebra(cliente_flask):
    r = cliente_flask.post("/prever/prazo", json={**CORPO, "subprefeitura": "Subprefeitura Nova"})
    assert r.status_code == 200


def test_todas_as_categorias_funcionam(cliente_flask):
    from chatbot.intents import CATEGORIAS
    for cat in CATEGORIAS:
        assert cliente_flask.post("/prever/prazo", json={**CORPO, "categoria": cat}).status_code == 200


def test_metodo_e_rota_invalidos(cliente_flask):
    assert cliente_flask.get("/prever/prazo").status_code == 405
    assert cliente_flask.get("/nao-existe").status_code == 404


def test_sem_modelos_health_503_e_prever_503(tmp_path, monkeypatch):
    import predictor
    monkeypatch.setattr(predictor, "CAMINHO_PRAZO", str(tmp_path / "x.joblib"))
    monkeypatch.setattr(predictor, "CAMINHO_ATRASO", str(tmp_path / "y.joblib"))
    predictor.limpar_cache()
    from app import criar_app
    c = criar_app().test_client()
    assert c.get("/health").status_code == 503
    r = c.post("/prever/prazo", json=CORPO)
    assert r.status_code == 503 and "caminho" not in r.get_json()["erro"].lower()


def test_modelo_gravado_pode_ser_carregado_em_outro_processo(modelos_sinteticos):
    """Garante que o .joblib não depende de __main__ (erro clássico de pickle)."""
    import subprocess, sys
    codigo = ("import joblib,sys,pandas as pd;"
              f"m=joblib.load(r'{modelos_sinteticos}/modelo_prazo.joblib')['pipeline'];"
              "print(m.predict(pd.DataFrame([{'categoria':'Buraco na via','subprefeitura':'Lapa','mes':1,'dia_semana':0}])))")
    import os
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    r = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True, cwd=raiz)
    assert r.returncode == 0, r.stderr


def test_metricas_gravadas_no_modelo(modelos_sinteticos):
    import joblib
    m1 = joblib.load(modelos_sinteticos / "modelo_prazo.joblib")["metricas"]
    m2 = joblib.load(modelos_sinteticos / "modelo_atraso.joblib")["metricas"]
    assert {"MAE", "RMSE", "R2"} <= set(m1)
    assert {"acuracia", "precisao", "recall", "f1", "matriz_confusao"} <= set(m2)


def test_chat_endpoints_basicos(cliente_flask):
    r = cliente_flask.get("/chat/inicio").get_json()
    assert "ZelaBairro" in r["resposta"] and r["sessao"]
    r2 = cliente_flask.post("/chat", json={"sessao": r["sessao"], "mensagem": "como funciona o prazo?"})
    assert r2.status_code == 200 and "estimativa" in r2.get_json()["resposta"]
    assert cliente_flask.post("/chat", json={"mensagem": 123}).status_code == 400
    assert cliente_flask.post("/chat", json={"mensagem": "x" * 2001}).status_code == 400
    assert cliente_flask.get("/").status_code in (200, 404)


def test_modelo_info_lista_categorias_com_historico(cliente_flask):
    j = cliente_flask.get("/modelo/info").get_json()
    assert len(j["categorias_cobertas"]) == 8 and j["categorias_sem_historico"] == []
    assert j["minimo_exemplos"] >= 1


def test_modelo_info_marca_categoria_com_poucos_exemplos(tmp_path, monkeypatch):
    import joblib, predictor
    from tests.fixtures import dados_sinteticos
    from scripts.treinar_modelos import treinar
    df = dados_sinteticos(4000)
    poda = df[df.categoria == "Poda de árvore"].index[100:]            # sobram 100 (< 200 mínimo)
    df = df.drop(poda)
    csv = tmp_path / "d.csv"; df.to_csv(csv, index=False)
    treinar(str(csv), str(tmp_path))
    monkeypatch.setattr(predictor, "CAMINHO_PRAZO", str(tmp_path / "modelo_prazo.joblib"))
    predictor.limpar_cache()
    j = predictor.info()
    assert "Poda de árvore" in j["categorias_sem_historico"] and "Buraco na via" in j["categorias_cobertas"]
    predictor.limpar_cache()


def test_modelo_ignora_o_mes_mas_a_api_continua_aceitando(cliente_flask):
    """O mês é validado (contrato) mas não entra no modelo (ver ml_utils.montar_pipeline)."""
    a = cliente_flask.post("/prever/prazo", json={**CORPO, "mes": 1}).get_json()
    b = cliente_flask.post("/prever/prazo", json={**CORPO, "mes": 11}).get_json()
    assert a == b
    assert cliente_flask.post("/prever/prazo", json={**CORPO, "mes": 13}).status_code == 400
