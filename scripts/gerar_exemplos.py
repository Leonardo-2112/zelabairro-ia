"""Gera docs/EXEMPLOS_CONVERSAS.md rodando o chatbot de verdade com APIs SIMULADAS.

O texto do chatbot é real (sai do código). Os números de previsão vêm de uma IA simulada
(prazo 12 dias, risco alto) e as ocorrências de uma API Java simulada: servem para demonstrar o
FORMATO das respostas, não são resultados do modelo treinado com o SP156.
"""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
from chatbot.chatbot import Chatbot, GerenciadorSessoes  # noqa: E402
from tests.fixtures import BAIRROS, IAFalsa, ZelaFalsa, ocorrencia  # noqa: E402

HOJE = datetime(2026, 11, 11, 14, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))


def rodar(titulo, falas, zela=None, ia=None):
    bot = Chatbot(zela or ZelaFalsa(), ia or IAFalsa(), front_url="https://zelabairro.vercel.app", agora=lambda: HOJE)
    sess = GerenciadorSessoes().obter("x")
    out = [f"## {titulo}\n"]
    for f in falas:
        r = bot.responder(sess, "x", f)["resposta"]
        out.append(f"**Cidadão:** {f}\n\n**Assistente:**\n\n" + "\n".join("> " + l for l in r.split("\n")) + "\n")
    return "\n".join(out)


def main():
    com_similar = ZelaFalsa([ocorrencia(15, "Buraco na via", BAIRROS[0]),
                             ocorrencia(30, "Poda de árvore", BAIRROS[1], status="RESOLVIDA",
                                        dataResolucao="2026-11-12", prioridade=None, pontuacaoPrioridade=None)])
    cobertas = ["Bueiro entupido", "Buraco na via", "Calçada danificada", "Descarte irregular de lixo", "Poda de árvore",
                "Sinalização de trânsito danificada", "Árvore com risco de queda"]   # como nos modelos treinados (2020–2023)
    partes = ["# Exemplos de conversa\n",
              "> Gerado por `scripts/gerar_exemplos.py`. O texto do assistente é o real; a **previsão (12 dias, risco alto) e as "
              "ocorrências vêm de APIs simuladas** para demonstrar o formato. Na demonstração, esses números virão dos "
              "modelos treinados com o SP156 e da API Java.\n",
              rodar("1. Registro completo (sem ocorrência parecida)",
                    ["Oi", "O bueiro da minha rua está entupido e alaga tudo, na Pinheiros", "Rua Teodoro Sampaio, 800, em frente ao mercado"]),
              rodar("2. Evitando duplicidade (RN07): apoiar em vez de criar",
                    ["Quero registrar um problema", "Tem um buraco enorme na faixa da direita da avenida",
                     "Moro na Lapa", "sim"], zela=com_similar),
              rodar("3. Mensagem ambígua: o assistente pergunta em vez de chutar",
                    ["Quero reclamar", "tem uma árvore perto da minha casa que me preocupa", "2", "Pinheiros",
                     "Rua dos Pinheiros, 100"]),
              rodar("4. Consulta, explicações e ocorrência encerrada",
                    ["como está a ocorrência 15?", "o que significa prioridade ALTA?", "ocorrência 30"],
                    zela=com_similar),
              rodar("5. IA fora do ar (RN12): o registro continua",
                    ["buraco enorme na minha rua na Lapa", "Rua das Flores, 10"], ia=IAFalsa(fora=True)),
              rodar("6. API Java fora do ar", ["quero registrar um problema", "calçada quebrada na minha rua", "Lapa", "Rua A, 5"],
                    zela=ZelaFalsa(fora=True)),
              rodar("7. Categoria sem histórico no SP156 (Iluminação): sem previsão, com o prazo de referência",
                    ["Tem um poste apagado na minha rua, na Pinheiros", "Rua Teodoro Sampaio, 800"],
                    ia=IAFalsa(cobertas=cobertas))]
    destino = os.path.join(RAIZ, "docs", "EXEMPLOS_CONVERSAS.md")
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with open(destino, "w", encoding="utf-8") as f:
        f.write("\n".join(partes))
    print("gerado", destino)


if __name__ == "__main__":
    main()
