"""Textos do chatbot. Linguagem simples, frases curtas, sem jargão.

Regras que este módulo garante:
- RN13: nunca mostra e-mail/telefone; só o primeiro nome do autor (lista branca de campos).
- Todo prazo/risco vem acompanhado do aviso de que é ESTIMATIVA (nunca garantia).
"""
from . import intents as I
from .regras import calcular_prioridade

AVISO_ESTIMATIVA = (
    "Importante: esses números são uma estimativa calculada por inteligência artificial "
    "com base no histórico de chamados parecidos. Não são uma garantia de atendimento."
)

SUGESTOES_INICIAIS = [
    "Quero registrar um problema",
    "Consultar uma ocorrência",
    "O que significa prioridade ALTA?",
    "Como funciona o prazo previsto?",
]

_STATUS_TXT = {"ABERTA": "Aberta", "EM_ANDAMENTO": "Em andamento",
               "RESOLVIDA": "Resolvida", "CANCELADA": "Cancelada"}


def _data_br(iso: str | None) -> str:
    if not iso:
        return "-"
    p = str(iso)[:10].split("-")
    return f"{p[2]}/{p[1]}/{p[0]}" if len(p) == 3 else str(iso)


def _link(front_url: str, caminho: str) -> str:
    """Link completo se FRONT_URL estiver configurada; senão o caminho dentro do site."""
    return f"{front_url.rstrip('/')}{caminho}" if front_url else f"{caminho} (no site do ZelaBairro)"


# --- Conversa geral -----------------------------------------------------------------
def boas_vindas() -> str:
    return ("Olá! Eu sou o assistente do ZelaBairro.\n"
            "Eu ajudo você a avisar a prefeitura sobre problemas do seu bairro, como buraco, "
            "poste apagado, lixo na calçada, árvore perigosa ou bueiro entupido.\n\n"
            "Posso:\n"
            "- te ajudar a registrar um problema;\n"
            "- ver se alguém já avisou do mesmo problema, para você apoiar;\n"
            "- mostrar como está uma ocorrência;\n"
            "- explicar prioridade e prazo.\n\n"
            "O que você precisa hoje?")


def ajuda() -> str:
    return ("Veja o que eu sei fazer:\n"
            "1. Registrar um problema: conte o que está acontecendo e eu faço as perguntas.\n"
            "2. Consultar uma ocorrência: diga o número, por exemplo \"ocorrência 15\".\n"
            "3. Explicar a prioridade (ALTA, MEDIA, BAIXA).\n"
            "4. Explicar o prazo previsto e o risco de atraso.\n"
            "5. Explicar como apoiar uma ocorrência que já existe.\n"
            "Para recomeçar a qualquer momento, escreva \"recomeçar\".")


def nao_entendi() -> str:
    return ("Desculpe, não entendi bem. Você pode me contar qual é o problema "
            "(por exemplo: \"tem um buraco na minha rua\") ou escolher uma das opções abaixo.")


def vazia() -> str:
    return "Não recebi nenhuma mensagem. Pode escrever de novo?"


def agradecimento() -> str:
    return "De nada! Se precisar de mais alguma coisa, é só escrever."


def despedida() -> str:
    return "Até logo! Obrigado por cuidar do seu bairro."


def recomecar() -> str:
    return "Tudo bem, vamos recomeçar. O que você precisa?"


def alterar_ocorrencia() -> str:
    return ("Por aqui eu não consigo alterar, cancelar ou apagar ocorrências. Pelo site, as regras são:\n"
            "- só dá para editar uma ocorrência enquanto ela está ABERTA;\n"
            "- uma ocorrência que já tem apoios ou atualizações não é apagada: ela é CANCELADA.")


# --- Explicações --------------------------------------------------------------------
def explicar_prioridade() -> str:
    pontos, classe = calcular_prioridade(5, 3, 2, "S", False)
    return ("A prioridade mostra o que a prefeitura deve atender primeiro. Ela é calculada com:\n"
            "- a gravidade do tipo de problema (risco à segurança pesa mais);\n"
            "- quantas pessoas apoiaram a ocorrência;\n"
            "- há quantos dias ela está aberta;\n"
            "- se existe risco de atraso ou se ela já está atrasada.\n\n"
            "Os níveis são:\n"
            "- ALTA (70 pontos ou mais): atender primeiro.\n"
            "- MEDIA (de 40 a 69 pontos): atenção normal.\n"
            "- BAIXA (menos de 40 pontos): pode esperar um pouco mais.\n\n"
            f"Exemplo: árvore com risco de queda, 3 apoios, aberta há 2 dias e com risco de atraso "
            f"soma {pontos} pontos e fica {classe}.\n"
            "Ocorrências já resolvidas ou canceladas não têm prioridade.")


def explicar_previsao() -> str:
    return ("Quando você descreve um problema, eu consulto um modelo de inteligência artificial "
            "treinado com chamados reais da Prefeitura de São Paulo (SP156). Ele devolve:\n"
            "- o prazo previsto, em dias;\n"
            "- o risco de atraso, ou seja, a chance de passar do prazo normal daquele tipo de problema.\n\n"
            + AVISO_ESTIMATIVA +
            "\n\nQuer registrar um problema para eu mostrar a previsão?")


def como_apoiar(front_url: str = "") -> str:
    return ("Se alguém já avisou do mesmo problema, o melhor é apoiar a ocorrência em vez de criar outra. "
            "Isso mostra que muita gente é afetada e ajuda a subir a prioridade.\n\n"
            f"Para apoiar, abra a ocorrência em {_link(front_url, '/ocorrencias')} e use o botão Apoiar.\n"
            "Regras: você só apoia uma vez, não pode apoiar a que você mesmo registrou e só dá para "
            "apoiar ocorrências ABERTAS ou EM ANDAMENTO.")


def como_acompanhar(front_url: str = "") -> str:
    return ("Para acompanhar, diga o número da ocorrência (ex.: \"ocorrência 15\") e eu mostro a situação. "
            f"O histórico completo de atualizações fica na página da ocorrência, em "
            f"{_link(front_url, '/ocorrencias')}.")


# --- Registro -----------------------------------------------------------------------
def pedir_descricao() -> str:
    return ("Conte com suas palavras qual é o problema. Escreva de 10 a 500 caracteres.\n"
            "Exemplo: \"Buraco grande na faixa da direita, perto do ponto de ônibus\".")


def descricao_invalida(tamanho: int) -> str:
    if tamanho < 10:
        return (f"A descrição ficou curta ({tamanho} caracteres). Preciso de pelo menos 10. "
                "Pode contar um pouco mais?")
    return (f"A descrição ficou longa ({tamanho} caracteres). O limite é 500. "
            "Pode resumir um pouco?")


def categoria_entendida(cat: str) -> str:
    return f"Entendi que o problema é: {cat}."


def pedir_categoria(candidatas: list[str]) -> str:
    if candidatas and len(candidatas) < len(I.CATEGORIAS):
        intro = "Não tenho certeza do tipo de problema. Qual destes é o mais parecido?"
    else:
        intro = "Qual é o tipo de problema?"
    linhas = [f"{i}. {c}" for i, c in enumerate(candidatas or list(I.CATEGORIAS), 1)]
    return intro + "\n" + "\n".join(linhas) + "\nResponda com o número."


def pedir_bairro() -> str:
    return "Em qual bairro (ou distrito) fica o problema?"


def bairro_nao_encontrado(exemplos: list[str]) -> str:
    ex = (" Exemplos: " + ", ".join(exemplos) + ".") if exemplos else ""
    return "Não achei esse bairro na minha lista. Confira a escrita e tente de novo." + ex


def pedir_subprefeitura() -> str:
    return "Em qual subprefeitura fica o problema? (Exemplo: Lapa, Pinheiros, Campo Limpo.)"


def subprefeitura_invalida() -> str:
    return "Não reconheci essa subprefeitura. Confira a escrita e tente de novo."


def bairro_confirmado(b: dict) -> str:
    return f"Bairro: {b['nome']} (subprefeitura {b['subprefeitura']})."


def pedir_endereco() -> str:
    return ("Qual é o endereço de referência? Diga a rua, o número aproximado e um ponto de referência "
            "(até 200 caracteres).\nExemplo: \"Rua Guaicurus, 1200, em frente à padaria\".")


def endereco_invalido(tamanho: int) -> str:
    if tamanho == 0:
        return "O endereço é obrigatório. Pode me dizer a rua e um ponto de referência?"
    return f"O endereço ficou com {tamanho} caracteres e o limite é 200. Pode resumir?"


def api_offline_consulta() -> str:
    return ("Não consegui falar com o sistema do ZelaBairro agora. Por favor, tente de novo em alguns "
            "minutos. Se preferir, consulte direto no site.")


def api_offline_registro() -> str:
    return ("Não consegui consultar o sistema agora, então não posso verificar se alguém já registrou "
            "esse problema. Você ainda pode registrar normalmente no site.")


def sem_similares() -> str:
    return "Não encontrei ocorrência parecida aberta nesse bairro. Então vamos registrar uma nova."


def sugerir_apoio(similares: list[dict]) -> str:
    linhas = []
    for o in similares:
        desc = (o.get("descricao") or "").strip()
        if len(desc) > 80:
            desc = desc[:77] + "..."
        extra = f"{o.get('qtdApoios', 0)} apoio(s)"
        st = _STATUS_TXT.get(o.get("status"), o.get("status") or "")
        linhas.append(f"- Ocorrência {o.get('id')}: {desc} ({st}, {extra})")
    if len(similares) == 1:
        pergunta = "É o mesmo problema que o seu? Responda sim para apoiar, ou \"nova\" para registrar outra."
    else:
        pergunta = ("Algum desses é o mesmo problema? Responda com o número da ocorrência para apoiar, "
                    "ou \"nova\" se o seu problema é diferente.")
    return ("Já existem ocorrências abertas do mesmo tipo nesse bairro:\n" + "\n".join(linhas) +
            "\n\nApoiar uma ocorrência que já existe é melhor do que criar outra repetida. " + pergunta)


def orientar_apoio(ident: int, front_url: str = "") -> str:
    return (f"Ótimo! Para apoiar a ocorrência {ident}, abra {_link(front_url, f'/ocorrencias/{ident}')} "
            "e clique em Apoiar.\n"
            "Lembre: você só pode apoiar uma vez e não pode apoiar uma ocorrência que você mesmo registrou.")


def qual_ocorrencia() -> str:
    return "Qual delas? Responda com o número da ocorrência."


def resumo_registro(d: dict, previsao: dict | None, prazo_ref: int, front_url: str = "",
                    sem_historico: bool = False) -> str:
    b = d["bairro"]
    partes = ["Pronto, juntei as informações:",
              f"- Tipo: {d['categoria']}",
              (f"- Bairro: {b['nome']} (subprefeitura {b['subprefeitura']})" if b.get("id") or b["nome"] != "(não informado)"
               else f"- Subprefeitura: {b['subprefeitura']}"),
              f"- Endereço: {d['endereco']}",
              f"- Descrição: {d['descricao']}", ""]
    if previsao:
        # Decisão D4 (Documento Base 7.2): sem porcentagem. Com class_weight="balanced" a probabilidade
        # fica inflada, então mostramos só o nível de risco, que é o que o modelo acerta bem (AUC 0,75).
        risco = ("risco ALTO de passar" if previsao["risco_atraso"] == "S"
                 else "risco BAIXO de passar")
        partes += [f"Com base no histórico de ocorrências parecidas, a previsão de resolução é de "
                   f"aproximadamente {previsao['prazo_previsto_dias']} dias. "
                   f"Sobre atraso, o modelo indica {risco} do prazo normal desse tipo de "
                   f"problema ({prazo_ref} dias).",
                   AVISO_ESTIMATIVA, ""]
    elif sem_historico:
        partes += ["Para esse tipo de problema ainda não tenho histórico suficiente para estimar o prazo, "
                   "então prefiro não chutar um número. "
                   f"O prazo de referência desse tipo de problema é de {prazo_ref} dias.", ""]
    else:
        partes += ["Não consegui calcular a previsão agora, mas isso não impede o registro. "
                   f"O prazo normal desse tipo de problema é de {prazo_ref} dias.", ""]
    partes += [f"Para registrar de verdade, abra {_link(front_url, '/ocorrencias/nova')}, informe seu nome e "
               "e-mail e preencha esses dados. A ocorrência nasce com a situação ABERTA e você pode "
               "acompanhar depois.",
               "Quer ajuda com mais alguma coisa?"]
    return "\n".join(partes)


# --- Consulta -----------------------------------------------------------------------
def pedir_id() -> str:
    return "Qual é o número da ocorrência? Exemplo: \"ocorrência 15\"."


def ocorrencia_nao_encontrada(ident: int) -> str:
    return f"Não encontrei a ocorrência {ident}. Confira o número e tente de novo."


def formatar_ocorrencia(oc: dict, front_url: str = "") -> str:
    """Lista branca de campos: e-mail e telefone nunca aparecem (RN13)."""
    cat = oc.get("categoria") or {}
    bai = oc.get("bairro") or {}
    status = oc.get("status")
    linhas = [f"Ocorrência {oc.get('id')} - {cat.get('nome', 'tipo não informado')}"]
    if bai:
        linhas.append(f"Bairro: {bai.get('nome', '-')} (subprefeitura {bai.get('subprefeitura', '-')})")
    autor = (oc.get("autor") or "").split()
    if autor:
        linhas.append(f"Registrada por: {autor[0]}")
    sit = f"Situação: {_STATUS_TXT.get(status, status)}, aberta em {_data_br(oc.get('dataAbertura'))}"
    if oc.get("dataResolucao"):
        sit += f", encerrada em {_data_br(oc['dataResolucao'])}"
    elif oc.get("diasEmAberto") is not None:
        sit += f" ({oc['diasEmAberto']} dia(s) em aberto)"
    linhas.append(sit)
    linhas.append(f"Apoios: {oc.get('qtdApoios', 0)}")
    if oc.get("prioridade"):
        linhas.append(f"Prioridade: {oc['prioridade']} ({oc.get('pontuacaoPrioridade')} pontos)")
    else:
        linhas.append("Prioridade: sem prioridade (ocorrência encerrada)")
    if cat.get("prazoDias"):
        linhas.append(f"Prazo normal desse tipo de problema: {cat['prazoDias']} dias")
    if oc.get("prazoPrevistoDias") is not None:
        risco = {"S": "sim", "N": "não"}.get(oc.get("riscoAtraso"), "não calculado")
        linhas.append(f"Previsão da IA: cerca de {oc['prazoPrevistoDias']} dias. Risco de atraso: {risco}.")
        linhas.append(AVISO_ESTIMATIVA)
    if status in ("ABERTA", "EM_ANDAMENTO") and oc.get("atrasada") is not None:
        linhas.append("Atrasada: " + ("sim" if oc["atrasada"] else "não"))
    linhas.append(f"Histórico completo: {_link(front_url, '/ocorrencias/' + str(oc.get('id')))}")
    return "\n".join(linhas)
