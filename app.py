"""API Flask do ZelaBairro IA & Chatbot.

Contrato do Documento Base 7.3:
  GET  /health         -> {"status": "ok"}
  POST /prever/prazo   -> {"prazo_previsto_dias": 12}
  POST /prever/atraso  -> {"risco_atraso": "S", "probabilidade": 0.73}
  erro 400             -> {"erro": "categoria desconhecida: Buraco"}

Extras (não alteram o contrato acima): POST /chat, GET /chat/inicio e a interface em /.
"""
import logging
import os
import uuid

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

import predictor
from chatbot.chatbot import Chatbot, GerenciadorSessoes
from chatbot.clientes import ClienteIA, ClienteZelaAPI

log = logging.getLogger("zelabairro")
STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chatbot", "static")


def criar_app(cliente_zela=None, cliente_ia=None) -> Flask:
    app = Flask(__name__, static_folder=None)
    origens = os.environ.get("CORS_ORIGINS", "*")
    CORS(app, origins=[o.strip() for o in origens.split(",")] if origens != "*" else "*")

    zela = cliente_zela or ClienteZelaAPI(os.environ.get("ZELA_API_URL", ""))
    ia = cliente_ia or ClienteIA(os.environ.get("IA_API_URL", ""))
    sessoes = GerenciadorSessoes()
    bot = Chatbot(zela, ia, front_url=os.environ.get("FRONT_URL", ""))

    # ---------------- contrato da IA ----------------
    @app.get("/health")
    def health():
        if predictor.modelos_disponiveis():
            return jsonify({"status": "ok"})
        return jsonify({"status": "modelos_indisponiveis"}), 503

    def _prever(funcao):
        corpo = request.get_json(silent=True)
        try:
            return jsonify(funcao(corpo))
        except predictor.ErroEntrada as e:
            return jsonify({"erro": str(e)}), 400
        except predictor.ModeloIndisponivel as e:
            log.error("modelo indisponível: %s", e)
            return jsonify({"erro": "modelo indisponível no servidor"}), 503

    @app.post("/prever/prazo")
    def prever_prazo():
        return _prever(predictor.prever_prazo)

    @app.post("/prever/atraso")
    def prever_atraso():
        return _prever(predictor.prever_atraso)

    @app.get("/modelo/info")
    def modelo_info():
        """Extra (fora do contrato): categorias com histórico no treino. O chatbot usa para não
        mostrar previsão sem base."""
        try:
            return jsonify(predictor.info())
        except predictor.ModeloIndisponivel:
            return jsonify({"erro": "modelo indisponível no servidor"}), 503

    # ---------------- chatbot ----------------
    @app.get("/chat/inicio")
    def chat_inicio():
        sid = uuid.uuid4().hex
        return jsonify(bot.iniciar(sessoes.obter(sid), sid))

    @app.post("/chat")
    def chat():
        corpo = request.get_json(silent=True) or {}
        msg = corpo.get("mensagem", "")
        if not isinstance(msg, str):
            return jsonify({"erro": "mensagem deve ser um texto"}), 400
        if len(msg) > 2000:
            return jsonify({"erro": "mensagem muito longa (máximo 2000 caracteres)"}), 400
        sid = corpo.get("sessao") if isinstance(corpo.get("sessao"), str) and corpo.get("sessao") else uuid.uuid4().hex
        try:
            return jsonify(bot.responder(sessoes.obter(sid), sid, msg))
        except Exception:  # nunca mostrar stack trace ao cidadão
            log.exception("erro inesperado no chat")
            return jsonify({"sessao": sid, "resposta": "Ops, algo deu errado do meu lado. Tente de novo em instantes.",
                            "sugestoes": ["Recomeçar"]}), 500

    @app.get("/")
    def interface():
        return send_from_directory(STATIC, "index.html")

    @app.get("/static/<path:nome>")
    def estaticos(nome):
        return send_from_directory(STATIC, nome)

    @app.errorhandler(404)
    def _404(_):
        return jsonify({"erro": "rota não encontrada"}), 404

    @app.errorhandler(405)
    def _405(_):
        return jsonify({"erro": "método não suportado"}), 405

    return app


app = criar_app()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
