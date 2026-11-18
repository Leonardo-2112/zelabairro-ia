"""Gera os 3 notebooks em notebooks/ (sem saídas).

Os notebooks são a parte que mais pesa na nota (60 pontos), e as saídas (tabelas, gráficos,
métricas) têm que ser as do SEU CSV real do SP156. Por isso este script NÃO executa nada:
o grupo roda os notebooks com o CSV real e salva com as saídas antes de entregar.

Uso: python scripts/gerar_notebooks.py
"""
import os

import nbformat as nbf

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def md(t):
    return nbf.v4.new_markdown_cell(t.strip("\n"))


def code(t):
    return nbf.v4.new_code_cell(t.strip("\n"))


def salvar(nome, celulas):
    nb = nbf.v4.new_notebook()
    nb["cells"] = celulas
    nb["metadata"] = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                      "language_info": {"name": "python"}}
    caminho = os.path.join(RAIZ, "notebooks", nome)
    nbf.write(nb, caminho)
    print("gerado", caminho)


SETUP = '''
import os, sys, json, warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
warnings.filterwarnings("ignore")

RAIZ = os.path.abspath("..")           # este notebook roda dentro de notebooks/
sys.path.insert(0, RAIZ)               # para importar ml_utils e chatbot
from chatbot.intents import CATEGORIAS # tabela 6.4 do Documento Base (prazos e gravidades)

CAMINHO_DADOS = os.path.join(RAIZ, "data", "dados_sp156.csv")
df = pd.read_csv(CAMINHO_DADOS)
print(f"{len(df):,} linhas e {df.shape[1]} colunas carregadas de {os.path.relpath(CAMINHO_DADOS, RAIZ)}")
df.head()
'''

# ======================================================================= 01 EDA
eda = [
    md("""
# 01 · Análise exploratória dos dados (SP156)
**Projeto ZelaBairro · Global Solution 2026/2 · IA & Chatbot**

**Integrantes (turma 1TDSPV):** Leonardo Afonço Sousa (RM 573982) · Syang Cristina Gomes Souza (RM 569259) ·
Matheus Jones Sousa de Freitas (RM 573559) · Vitor Goncalves de Souza (RM 569023) · Joao Machado Nascimento (RM 572364)

Objetivo: entender os chamados reais de zeladoria da Prefeitura de São Paulo antes de treinar os
modelos: o que temos, o quanto está sujo, e se existe sinal para prever **prazo** e **atraso**.

**Fonte e data de acesso dos dados (Documento Base, seção 7.1):**
"""),
    code('''
FONTE = "Dados do SP156 — SMIT, Portal de Dados Abertos da Prefeitura de São Paulo (dados.prefeitura.sp.gov.br, conjunto dados-do-sp156)"
DATA_ACESSO = "15/11/2026"   # dia em que conferimos o conjunto no portal (padrão ABNT: "Acesso em")
VERSAO = "arquivos trimestrais na versão atualizada pelo portal em 10/08/2026"
RECORTE = "chamados abertos de 01/01/2020 a 30/09/2023 (os arquivos usados não traziam o 2º tri/2023)"
print(FONTE); print("Acesso em:", DATA_ACESSO, "|", VERSAO); print("Recorte:", RECORTE)
'''),
    md("## 1. Carga e visão geral"),
    code(SETUP),
    code('''
df.info()
'''),
    code('''
esperadas = ["categoria", "subprefeitura", "mes", "dia_semana", "dias_para_resolver", "nr_prazo_dias", "atrasou"]
faltando = [c for c in esperadas if c not in df.columns]
assert not faltando, f"Colunas ausentes: {faltando}. Rode scripts/preparar_dados.py"
print("Nulos por coluna:"); print(df[esperadas].isna().sum())
print("\\nLinhas idênticas (esperado: sem hora/protocolo, são chamados diferentes no mesmo dia/distrito):", df.duplicated().sum())
print("Categorias fora da tabela 6.4:", sorted(set(df['categoria']) - set(CATEGORIAS)))
'''),
    md("""
## 2. Como os dados foram preparados
O arquivo `data/dados_sp156.csv` vem de `scripts/preparar_dados.py` a partir dos CSVs **trimestrais** do SP156:
1. fica só com os **serviços** que correspondem às categorias do ZelaBairro (de-para por serviço em `data/depara_sp156.csv`);
2. fica só com chamados de status **FINALIZADA**; remove linhas repetidas **entre** arquivos, mas mantém linhas idênticas dentro do mesmo
   arquivo (de 2020 em diante o SP156 não traz hora nem protocolo, então duas linhas iguais são chamados diferentes);
3. `dias_para_resolver = data do parecer − data de abertura` (em dias);
4. a subprefeitura é derivada do **distrito** (`data/depara_distrito_subprefeitura.csv`). Conferência: de 2020 a 2023 o SP156 traz também a
   *Prefeitura Operacional* e, em cada distrito, a subprefeitura do nosso mapa coincide com ela na grande maioria dos chamados (as diferenças são
   chamados atendidos por outra subprefeitura);
5. `atrasou = 1` se `dias_para_resolver > nr_prazo_dias` da categoria (**mesma regra da RN11**);
6. `mes` (1–12) e `dia_semana` (0 = segunda … 6 = domingo, igual ao `weekday()` do Python) saem da data de abertura.

### Por que só 2020–2023? (decisão tomada olhando os dados)
A coluna de encerramento é a única data de fim que o SP156 traz, e o que ela mede **muda com o tempo**:
* **2012–2014:** estrutura diferente (sem distrito). **2015 até 3º tri/2016, 2018 e 2019:** o parecer cai no **mesmo dia da abertura em 73–100% dos
  chamados** (não mede atendimento). jan–set/2017 serve, mas é só um ano parcial e antigo.
* **A partir de 2020** o arquivo passa a ter **"Data de Finalização"**: só 8–18% caem no mesmo dia e as medianas são plausíveis.
Por isso o treino usa **1º tri/2020 a 3º tri/2023** (14 trimestres; o 2º tri/2023 não foi fornecido). A célula abaixo mostra isso no dado usado.
"""),
    code('''
df["_ab"] = pd.to_datetime(df["data_abertura"])
z = df.groupby(df["_ab"].dt.to_period("M"))["dias_para_resolver"].agg(chamados="size", pct_mesmo_dia=lambda s: round(100 * (s == 0).mean(), 1))
print("Janela usada:", df["data_abertura"].min(), "a", df["data_abertura"].max())
z
'''),
    code('''
MINIMO = 200  # mesmo limite do predictor.py: abaixo disso a categoria é "sem histórico suficiente"
cob = df["categoria"].value_counts().reindex(list(CATEGORIAS)).fillna(0).astype(int).to_frame("chamados")
cob["histórico suficiente?"] = np.where(cob["chamados"] >= MINIMO, "sim", "NÃO — o chatbot não mostra previsão")
cob
'''),
    md("""
## 3. Volume por categoria e por subprefeitura

**Como escolhemos os gráficos (framework de Dataviz da Aula 04):** para cada gráfico, (1) a **pergunta de negócio** vira o título,
(2) identificamos as **variáveis** (categoria = nominal; quantidade e % = quantitativas) e (3) escolhemos o gráfico pela **taxonomia**:
comparação entre categorias → **barras horizontais** (comprimento é um dos atributos mais precisos na hierarquia de Cleveland e McGill
e os nomes longos ficam legíveis); distribuição → **histograma** e **boxplot**; evolução no tempo → **linha**. Seguimos a versão
"profissional" da aula: barras 2D em cinza, **só o destaque em cor**, rótulo na ponta da barra e sem grade, pizza ou 3D.
"""),
    code('''
CINZA, DESTAQUE = "#b8bfc6", "#0f5c5a"

def barras(serie, titulo, destaques=(), formato="{:,.0f}", rotulo_x=""):
    """Barras horizontais no padrão da Aula 04: cinza neutro, só os destaques em cor, valor na ponta da barra."""
    serie = serie.sort_values()
    cores = [DESTAQUE if i in destaques else CINZA for i in serie.index]
    fig, ax = plt.subplots(figsize=(8, 0.42 * len(serie) + 1))
    ax.barh(serie.index, serie.values, color=cores)
    for i, v in enumerate(serie.values):
        ax.text(v, i, " " + formato.format(v).replace(",", "."), va="center", fontsize=9)
    ax.set_title(titulo, loc="left", fontsize=12); ax.set_xlabel(rotulo_x)
    for lado in ["top", "right"]:
        ax.spines[lado].set_visible(False)
    ax.margins(x=0.15); plt.tight_layout(); plt.show()
'''),
    code('''
# Pergunta: quais problemas mais aparecem? (comparação entre categorias → barras horizontais)
por_cat = df["categoria"].value_counts()
barras(por_cat, "Quais problemas mais aparecem? Buraco na via é quase metade dos chamados",
       destaques=[por_cat.idxmax()], rotulo_x="chamados")
por_cat.to_frame("chamados")
'''),
    code('''
sub = df["subprefeitura"].value_counts()
print(f"{sub.size} subprefeituras. Menores grupos (poucos dados = previsão menos confiável):")
sub.tail(8).to_frame("chamados")
'''),
    code('''
# Pergunta: onde se concentram os chamados? (comparação → barras horizontais, destaque nas 3 maiores)
top15 = sub.head(15)
barras(top15, "Onde se concentram os chamados? As 15 subprefeituras com mais registros",
       destaques=list(top15.index[:3]), rotulo_x="chamados")
'''),
    md("## 4. Tempo de resolução (`dias_para_resolver`)"),
    code('''
df["dias_para_resolver"].describe(percentiles=[.5, .75, .9, .95, .99]).to_frame("dias")
'''),
    md("""
### Estatística descritiva do tempo de resolução (Aula 02)
Medidas de tendência central (média, mediana, moda), de dispersão (desvio padrão) e de posição (quartis), e a regra do
**intervalo interquartil (IQR)** para identificar outliers: valores acima de Q3 + 1,5 × IQR.
"""),
    code('''
dias = df["dias_para_resolver"]
media, mediana, moda = dias.mean(), dias.median(), dias.mode()[0]
desvio = dias.std()                       # desvio padrão amostral (stdev da aula)
q1, q2, q3 = dias.quantile([.25, .50, .75])
iqr = q3 - q1
limite_superior = q3 + 1.5 * iqr
outliers = (dias > limite_superior).sum()
print(f"Média: {media:.1f} dias | Mediana: {mediana:.0f} dias | Moda: {moda} dias")
print(f"Desvio padrão: {desvio:.1f} dias")
print(f"Q1: {q1:.0f} | Q2 (mediana): {q2:.0f} | Q3: {q3:.0f} | IQR: {iqr:.0f} dias")
print(f"Limite para outlier (Q3 + 1,5 × IQR): {limite_superior:.0f} dias")
print(f"Outliers: {outliers:,} chamados ({outliers / len(dias):.1%}) — o maior levou {dias.max():,} dias")
'''),
    md("""
**Interpretação:** a **média é bem maior que a mediana**, o mesmo fenômeno do exemplo de tempo de entrega da Aula 02 (média 10 × mediana 4,5):
poucos chamados muito demorados puxam a média para cima. O desvio padrão alto e a quantidade de outliers confirmam a **cauda longa**.
Consequências para os modelos: (1) usamos o **MAE** como métrica principal, porque ele não é dominado pelos extremos; (2) no modelo de
prazo treinamos sobre **log(1 + dias)**, que reduz o peso dos outliers sem apagá-los (não removemos os chamados longos porque são reais),
e assim o modelo prevê o tempo **típico**, mais próximo da mediana.
"""),
    code('''
# Pergunta: como o tempo de resolução se distribui? (distribuição → histograma + boxplot)
fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
df["dias_para_resolver"].clip(upper=df["dias_para_resolver"].quantile(.99)).hist(bins=40, ax=ax[0], color="#0f5c5a")
ax[0].set_title("Distribuição (cortada no percentil 99)"); ax[0].set_xlabel("dias"); ax[0].grid(False)
np.log1p(df["dias_para_resolver"]).hist(bins=40, ax=ax[1], color="#f2b134")
ax[1].set_title("log(1 + dias): a escala usada no modelo de prazo"); ax[1].set_xlabel("log(1 + dias)"); ax[1].grid(False)
plt.tight_layout(); plt.show()
'''),
    code('''
resumo = df.groupby("categoria")["dias_para_resolver"].agg(["count", "median", "mean", "std", "max"]).round(1)
resumo["prazo_referencia"] = [CATEGORIAS[c]["prazo_dias"] for c in resumo.index]
resumo.sort_values("median", ascending=False)
'''),
    code('''
ordem = resumo.sort_values("median").index
dados = [df.loc[df["categoria"] == c, "dias_para_resolver"].clip(upper=df["dias_para_resolver"].quantile(.99)) for c in ordem]
fig, ax = plt.subplots(figsize=(9, 5))
ax.boxplot(dados, vert=False, showfliers=False)
ax.set_yticklabels(list(ordem))   # compatível com qualquer versão do matplotlib
for i, c in enumerate(ordem, 1):
    ax.plot(CATEGORIAS[c]["prazo_dias"], i, "r|", markersize=22)
ax.set_title("Quais categorias passam do prazo? Dias para resolver (traço vermelho = prazo de referência)", loc="left")
ax.set_xlabel("dias"); plt.tight_layout(); plt.show()
'''),
    md("""
**Leitura:** compare a mediana de cada categoria com o traço vermelho (prazo de referência da tabela 6.4).
Categorias cuja mediana já passa do prazo terão muitos atrasos: isso define o equilíbrio de classes do modelo 2.
"""),
    md("## 5. Atraso (`atrasou`) — alvo do modelo 2"),
    code('''
print(f"Proporção geral de atrasos: {df['atrasou'].mean():.1%}")
atraso_cat = df.groupby("categoria")["atrasou"].mean() * 100
# Pergunta: quais categorias mais atrasam? (comparação → barras, destaque nas que atrasam mais da metade das vezes)
barras(atraso_cat, "Quais categorias mais atrasam? % de chamados acima do prazo de referência",
       destaques=list(atraso_cat[atraso_cat > 40].index), formato="{:.1f}%", rotulo_x="% que atrasou")
'''),
    code('''
fig, ax = plt.subplots(1, 2, figsize=(11, 3.6))
df.groupby("mes")["atrasou"].mean().plot(marker="o", ax=ax[0], color="#0f5c5a")
ax[0].set_title("O mês influencia o atraso? (linha = evolução)", loc="left"); ax[0].set_xlabel("mês"); ax[0].set_ylim(0, 1)
df.groupby("dia_semana")["atrasou"].mean().plot.bar(ax=ax[1], color=CINZA)
ax[1].set_title("E o dia da semana? (0 = segunda)", loc="left"); ax[1].set_ylim(0, 1)
for a in ax:
    a.spines["top"].set_visible(False); a.spines["right"].set_visible(False)
plt.tight_layout(); plt.show()
'''),
    code('''
tab = df.pivot_table(index="subprefeitura", columns="categoria", values="atrasou", aggfunc="mean")
sub_atraso = df.groupby("subprefeitura")["atrasou"].agg(["mean", "count"]).query("count >= 30").sort_values("mean")
print("Subprefeituras com pelo menos 30 chamados — menor e maior % de atraso:")
pd.concat([sub_atraso.head(5), sub_atraso.tail(5)]).round(3)
'''),
    md("""
## 6. Cuidados com os dados (para citar na apresentação)
* **Viés de sobrevivência quase nulo:** só chamados **finalizados** têm `dias_para_resolver`, mas nos arquivos de 2020–2023 apenas
  0,0–0,4% dos chamados dessas categorias estavam abertos ou cancelados quando o relatório foi gerado. Nenhum veio como "Indeferido".
* **"Data de Finalização" ≠ conserto:** segundo o glossário oficial do SP156 (2020 em diante, `docs/glossario_sp156_2020.txt`), ela é a
  *"data de fechamento do protocolo"*, e o status "Finalizado" significa *"finalizada pelo órgão competente"*. O próprio glossário avisa que o
  SP156 não executa o serviço. O "prazo previsto" do ZelaBairro é, portanto, o **tempo até o órgão fechar o protocolo**.
* **Vários protocolos para o mesmo problema:** o glossário diz que um cidadão pode abrir mais de uma solicitação e várias pessoas podem pedir
  o mesmo serviço. Isso é exatamente o que a RN07 do ZelaBairro (apoiar em vez de duplicar) evita.
* **Categoria sem dados:** "Iluminação pública apagada" não tem chamados no SP156 a partir de 2018 (os serviços de iluminação só aparecem até 2017).
  O modelo não aprendeu nada sobre ela e o chatbot deixa de dar previsão para ela.
* **Pandemia:** 2020 e 2021 incluem a COVID-19, quando o atendimento foi irregular (ex.: buraco teve mediana de 32 dias no 1º tri/2020).
* **Arquivos faltando:** o 2º tri/2023 não foi fornecido. O 2º tri/2021 veio em .xlsx e foi lido normalmente. O CSV também não tem nenhum chamado aberto em fev–mar/2021 (o 1º tri/2021 só traz janeiro); a causa não foi verificada nos arquivos de origem.
* **Fechamento no mesmo dia:** em *Bueiro*, *Descarte* e *Árvore com risco* 45–53% dos chamados têm 0 dia, então o prazo dessas categorias
  é bimodal (muitos em 0–1 dia e uma cauda longa).
* **Prazos de referência × realidade:** compare a mediana real com o prazo da tabela 6.4 (seção 4). Em Sinalização e Poda perto de metade
  ou mais dos chamados passa do prazo; em Descarte quase nenhum passa. Isso define o equilíbrio de classes do modelo 2.
* **Sem vazamento:** os modelos usam só `categoria`, `subprefeitura`, `mes` e `dia_semana`,
  informações que existem **na abertura**. A data de encerramento nunca é entrada.
* **Poucas features:** sem gravidade real do chamado, descrição ou local exato, o poder de previsão é limitado.
  Compare sempre com o baseline (notebooks 02 e 03) antes de afirmar que o modelo "funciona".
* **Subprefeituras pequenas** têm poucos exemplos; o modelo trata nomes nunca vistos sem quebrar
  (`handle_unknown="ignore"`), mas a previsão será mais genérica.
"""),
    md("""## 7. Conclusões da exploração
* **O que temos:** 982.475 chamados finalizados do SP156, abertos entre janeiro de 2020 e setembro de 2023, em 7 das nossas 8 categorias e 32 subprefeituras, sem valores nulos. Iluminação pública não tem nenhum chamado nesse período, então não vamos conseguir prever nada para ela.
* **Buraco na via domina a base:** sozinho é quase metade dos chamados (474.597, 48,3%). Somando Poda de árvore e Descarte de lixo, chegamos a 86,6%. Calçada (9.400) e Sinalização (16.006) têm poucos exemplos.
* **O tempo de resolução tem muitos valores extremos:** a média é de 28,6 dias, mas a mediana é só 7 e a moda é 0 (muita coisa fecha no mesmo dia). O desvio padrão é de 62,3 dias. Pela regra do IQR (Q3 = 24 e IQR = 23), tudo acima de 58 dias é outlier, o que dá 133.691 chamados (13,6%); o maior levou 1.668 dias. É o mesmo caso do exemplo de tempo de entrega da Aula 02: a média engana. Por isso vamos usar o MAE como métrica principal e treinar o modelo de prazo em log(1 + dias).
* **O tipo de problema é o que mais muda o tempo:** pela mediana, Árvore com risco de queda fecha em 0 dia, Bueiro e Descarte em 1 dia e Poda em 28 dias. Sinalização tem mediana de 18 dias, mesmo com prazo de referência de 10.
* **Atraso:** 29,8% dos chamados passam do prazo da tabela 6.4, então as classes são desbalanceadas (cerca de 70/30). Sinalização atrasa 61,3% das vezes, Poda 48,5% e Buraco 33,0%; Descarte, só 2,9%.
* **Subprefeitura:** entre as que têm pelo menos 30 chamados, o atraso vai de 13,7% (Jabaquara) a 46,0% (Pirituba/Jaraguá). Parte dessa diferença pode ser só a mistura de categorias de cada região.
* **O que esperamos dos modelos:** na abertura do chamado só sabemos categoria, subprefeitura, mês e dia da semana. Com tão pouca informação, o ganho sobre uma tabela de medianas por categoria deve ser pequeno. Por isso, nos notebooks 02 e 03, comparamos sempre com baselines."""),
]

# ======================================================================= 02 PRAZO
prazo = [
    md("""
# 02 · Modelo 1 — Previsão de prazo (regressão)
**Projeto ZelaBairro · Global Solution 2026/2 · IA & Chatbot**

**Integrantes (turma 1TDSPV):** Leonardo Afonço Sousa (RM 573982) · Syang Cristina Gomes Souza (RM 569259) ·
Matheus Jones Sousa de Freitas (RM 573559) · Vitor Goncalves de Souza (RM 569023) · Joao Machado Nascimento (RM 572364)

**Pergunta:** dado o tipo de problema, a subprefeitura e quando foi aberto, em quantos dias ele deve ser resolvido?

* Alvo: `dias_para_resolver`
* Entradas: `categoria`, `subprefeitura`, `mes`, `dia_semana`
* Caminho seguido (como nas Aulas 05 e 06): começamos pelo **modelo que chuta** (baseline), depois os modelos **interpretáveis** vistos em aula
  (**Regressão Linear** e **Árvore de Decisão**) e só então o **Random Forest**, que tem mais acurácia mas é mais "caixa preta"
* Algoritmo final: `RandomForestRegressor` treinado sobre **log(1 + dias)**
* Métricas: **MAE, RMSE e R²** (no conjunto de teste)
"""),
    code(SETUP),
    md("## 1. Preparação"),
    code('''
from sklearn.model_selection import train_test_split, cross_val_score, KFold
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.dummy import DummyRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from ml_utils import FEATURES, montar_pipeline, montar_regressor

SEED = 42
X, y = df[FEATURES], df["dias_para_resolver"]
X_treino, X_teste, y_treino, y_teste = train_test_split(X, y, test_size=0.2, random_state=SEED)
print(f"treino: {len(X_treino):,} | teste: {len(X_teste):,} | features: {FEATURES}")
'''),
    md("""
**Por que precisamos transformar as entradas:** os algoritmos só entendem números, mas `categoria` e `subprefeitura` são textos.
`montar_pipeline` e `montar_regressor` (em `ml_utils.py`) fazem o **one-hot**: cada valor vira uma coluna 0/1 (ex.: `categoria_Buraco na via = 1`).
`mes` e `dia_semana` também viram categorias, porque dezembro não é "maior" que janeiro. O `Pipeline` é a "esteira" da Aula 02:
transforma e treina sempre na mesma ordem, e fica num módulo à parte para que o `.joblib` possa ser carregado pela API Flask.
**Normalização Min-Max não se aplica aqui:** depois do one-hot todas as entradas já são 0 ou 1.
"""),
    md("## 2. Baseline e comparação de modelos"),
    code('''
def avaliar(nome, pipe):
    p = pipe.predict(X_teste)
    return {"modelo": nome, "MAE": mean_absolute_error(y_teste, p),
            "RMSE": float(np.sqrt(mean_squared_error(y_teste, p))), "R2": r2_score(y_teste, p)}

RF = dict(n_estimators=60, min_samples_leaf=20, n_jobs=-1, random_state=SEED)
ARVORE = dict(max_depth=10, min_samples_leaf=50, random_state=SEED)   # limitar a árvore evita overfitting (Aula 06)
candidatos = {
    "1. Modelo que chuta a mediana geral (baseline)": montar_pipeline(DummyRegressor(strategy="median")),
    "2. Regressão Linear, dias brutos": montar_pipeline(LinearRegression()),
    "3. Árvore de Decisão, dias brutos": montar_pipeline(DecisionTreeRegressor(**ARVORE)),
    "4. Árvore de Decisão, log(1+dias)": montar_regressor(DecisionTreeRegressor(**ARVORE)),
    "5. Random Forest, dias brutos, sem mês": montar_pipeline(RandomForestRegressor(**RF)),
    "6. Random Forest, log(1+dias), COM mês": montar_regressor(RandomForestRegressor(**RF), usar_mes=True),
    "7. Random Forest, log(1+dias), SEM mês": montar_regressor(RandomForestRegressor(**RF), usar_mes=False),
}
resultados = []
for nome, pipe in candidatos.items():
    pipe.fit(X_treino, y_treino)
    resultados.append(avaliar(nome, pipe))
# baseline mais exigente: a mediana de CADA categoria (o que se faria sem IA, só com uma tabela)
med_cat = y_treino.groupby(X_treino["categoria"]).median()
p_cat = X_teste["categoria"].map(med_cat).fillna(y_treino.median())
resultados.append({"modelo": "0. Tabela de medianas por categoria (baseline sem IA)", "MAE": mean_absolute_error(y_teste, p_cat),
                   "RMSE": float(np.sqrt(mean_squared_error(y_teste, p_cat))), "R2": r2_score(y_teste, p_cat)})
pd.DataFrame(resultados).round(3).set_index("modelo")
'''),
    md("""
**Como ler:** o MAE é o erro médio em **dias**; o RMSE pune mais os erros grandes; R² perto de 0 significa que o modelo explica pouco da variação.

**A história da comparação (trade-off acurácia × interpretabilidade, Aula 06):** a Regressão Linear e a Árvore de Decisão são fáceis de explicar,
mas, treinadas em **dias brutos**, erram mais em MAE do que a simples tabela de medianas (30,2 e 28,4 contra 24,5 dias): o tempo não cresce
"em linha reta" com as entradas e tem muitos outliers. Treinada em **log(1 + dias)**, a própria árvore já passa a tabela (23,9 dias), e o
Random Forest (várias árvores votando, Aula 05) erra menos ainda (23,3 dias sem mês). Por isso a floresta é o modelo final, mesmo sendo
menos interpretável; a árvore fica como a versão "explicável" do mesmo raciocínio (veja o desenho logo abaixo).
O tempo de resolução tem **cauda longa** (alguns chamados levam centenas de dias), e isso muda quem "ganha": a floresta em dias brutos
prevê a *média* (boa em RMSE/R², mas pior em MAE do que um baseline que chuta a mediana), enquanto a floresta em log(1+dias) prevê um valor
*típico* (melhor em MAE). Como o ZelaBairro mostra o tempo típico ao cidadão, o modelo final usa **log(1+dias)** e o MAE é a métrica principal;
o baseline que importa é a **mediana por categoria** (uma tabela simples, sem IA). Diga na apresentação o quanto o modelo ganha *além* dela.
"""),
    md("""
### Como a Árvore de Decisão "pensa" (modelo caixa branca)
Uma árvore pequena (profundidade 3), treinada em log(1 + dias), mostra as regras do tipo **se… então** que a Aula 06 descreve:
nó raiz, nós de decisão e folhas. O valor da folha está em log; `np.expm1` volta para dias.
"""),
    code('''
from sklearn.tree import plot_tree
arvore_pequena = montar_regressor(DecisionTreeRegressor(max_depth=3, random_state=SEED)).fit(X_treino, y_treino)
interno_arvore = arvore_pequena.regressor_
nomes_arvore = [n.replace("cat__", "") for n in interno_arvore.named_steps["prep"].get_feature_names_out()]
plt.figure(figsize=(16, 6))
plot_tree(interno_arvore.named_steps["modelo"], feature_names=nomes_arvore, filled=True, rounded=True, fontsize=8, impurity=False)
plt.title("Árvore de Decisão (profundidade 3) sobre log(1 + dias)"); plt.show()
print("Exemplo de leitura: uma folha com value = 2.0 equivale a", round(float(np.expm1(2.0)), 1), "dias")
'''),
    md("""
### Teste "no tempo": treinar em 2020–2022 e testar em 2023
A divisão aleatória mistura os anos; o uso real é **prever o futuro** com dados do passado. Esta comparação decide se o **mês** entra no modelo:
"""),
    code('''
ano = pd.to_datetime(df["data_abertura"]).dt.year
tr_t = df[ano <= 2022].sample(250_000, random_state=SEED); te_t = df[ano == 2023].sample(80_000, random_state=SEED)
med = tr_t.groupby("categoria")["dias_para_resolver"].median()
linhas = [{"modelo": "Tabela de medianas por categoria (baseline sem IA)",
           "MAE": mean_absolute_error(te_t["dias_para_resolver"], te_t["categoria"].map(med).fillna(tr_t["dias_para_resolver"].median()))}]
for nome, com_mes in [("Random Forest SEM mês", False), ("Random Forest COM mês", True)]:
    m_t = montar_regressor(RandomForestRegressor(n_estimators=60, min_samples_leaf=20, n_jobs=-1, random_state=SEED), usar_mes=com_mes).fit(tr_t[FEATURES], tr_t["dias_para_resolver"])
    linhas.append({"modelo": nome, "MAE": mean_absolute_error(te_t["dias_para_resolver"], m_t.predict(te_t[FEATURES]))})
pd.DataFrame(linhas).round(2).set_index("modelo")
'''),
    md("""
Treinando no passado (2020–2022) e testando em 2023, o modelo **com** mês erra **mais** que o **sem** mês: o mês aprende o que aconteceu em cada mês
daqueles anos (pandemia, mutirões), e isso não se repete. **Decisão:** o modelo final **não usa o mês** (a API continua aceitando `mes`, conforme o
contrato do Documento Base, mas o ignora). Para mudar, use `usar_mes=True` em `montar_pipeline` e retreine.
"""),
    md("## 3. Ajuste de hiperparâmetros (busca pequena, modelo SEM mês)"),
    code('''
from sklearn.model_selection import GridSearchCV

grade = {"regressor__modelo__min_samples_leaf": [10, 20, 50], "regressor__modelo__max_depth": [None, 16]}
busca = GridSearchCV(montar_regressor(RandomForestRegressor(n_estimators=60, n_jobs=-1, random_state=SEED)), grade,
                     scoring="neg_mean_absolute_error", cv=3, n_jobs=1)
# A busca roda numa AMOSTRA do treino (com ~790 mil linhas, a busca completa levaria muitos minutos);
# o modelo final é então treinado com TODO o conjunto de treino.
amostra = X_treino.sample(min(30_000, len(X_treino)), random_state=SEED).index
busca.fit(X_treino.loc[amostra], y_treino.loc[amostra])
print("Melhores parâmetros (busca na amostra):", busca.best_params_)
print(f"MAE médio na validação cruzada (amostra): {-busca.best_score_:.2f} dias")
'''),
    md("## 4. Modelo final e avaliação no teste"),
    code('''
melhores = {k.replace("regressor__modelo__", ""): v for k, v in busca.best_params_.items()}
modelo = montar_regressor(RandomForestRegressor(n_estimators=100, n_jobs=-1, random_state=SEED, **melhores)).fit(X_treino, y_treino)
previsoes = modelo.predict(X_teste)
base = candidatos["1. Modelo que chuta a mediana geral (baseline)"]
metricas = {
    "MAE": float(mean_absolute_error(y_teste, previsoes)),
    "RMSE": float(np.sqrt(mean_squared_error(y_teste, previsoes))),
    "R2": float(r2_score(y_teste, previsoes)),
    "baseline_mediana_MAE": float(mean_absolute_error(y_teste, base.predict(X_teste))),
    "baseline_mediana_por_categoria_MAE": float(mean_absolute_error(y_teste, p_cat)),
    "linhas_treino": int(len(X_treino)), "linhas_teste": int(len(X_teste)),
}
pd.Series(metricas).round(3).to_frame("valor")
'''),
    code('''
amostra_cv = X.sample(min(60_000, len(X)), random_state=SEED).index   # amostra para a validação cruzada ser rápida
cv = cross_val_score(modelo, X.loc[amostra_cv], y.loc[amostra_cv], cv=KFold(5, shuffle=True, random_state=SEED), scoring="neg_mean_absolute_error")
print(f"Validação cruzada (5 folds, amostra de {len(amostra_cv):,}) — MAE: {-cv.mean():.2f} ± {cv.std():.2f} dias")
'''),
    md("### Real × previsto e resíduos"),
    code('''
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
lim = float(np.quantile(y_teste, .99))
ax[0].scatter(y_teste, previsoes, s=6, alpha=.25, color="#0f5c5a")
ax[0].plot([0, lim], [0, lim], "r--", label="previsão perfeita")
ax[0].set_xlim(0, lim); ax[0].set_ylim(0, lim); ax[0].set_xlabel("dias reais"); ax[0].set_ylabel("dias previstos")
ax[0].set_title("Real × previsto (teste)"); ax[0].legend()
res = (y_teste - previsoes).clip(-lim, lim)
ax[1].hist(res, bins=40, color="#f2b134"); ax[1].axvline(0, color="r", ls="--")
ax[1].set_title("Resíduos (real − previsto)"); ax[1].set_xlabel("dias")
plt.tight_layout(); plt.show()
'''),
    code('''
erro_cat = (pd.DataFrame({"categoria": X_teste["categoria"].values, "erro_abs": np.abs(y_teste.values - previsoes)})
            .groupby("categoria")["erro_abs"].agg(["mean", "count"]).round(2).sort_values("mean"))
erro_cat.columns = ["MAE (dias)", "n no teste"]
erro_cat
'''),
    md("### O que o modelo aprendeu (importância das variáveis)"),
    code('''
interno = modelo.regressor_   # o pipeline dentro do TransformedTargetRegressor
nomes = interno.named_steps["prep"].get_feature_names_out()
imp = pd.Series(interno.named_steps["modelo"].feature_importances_, index=nomes).sort_values(ascending=False)
imp.index = [i.replace("cat__", "") for i in imp.index]
imp.head(12).sort_values().plot.barh(figsize=(8, 4), color="#0f5c5a")
plt.title("12 variáveis mais importantes"); plt.tight_layout(); plt.show()
'''),
    md("## 5. Exportar o modelo (`models/modelo_prazo.joblib`)"),
    code('''
import joblib
os.makedirs(os.path.join(RAIZ, "models"), exist_ok=True)
modelo.fit(X, y)   # versão final usa todos os dados; as métricas acima são do treino/teste separado
joblib.dump({"pipeline": modelo, "metricas": metricas, "features": FEATURES, "usa_mes": False, "alvo": "log1p(dias)",
             "categorias_treino": {k: int(v) for k, v in df["categoria"].value_counts().items()}},
            os.path.join(RAIZ, "models", "modelo_prazo.joblib"), compress=3)
print("salvo em models/modelo_prazo.joblib")
'''),
    code('''
# Teste de sanidade: exatamente o corpo que a API recebe (Documento Base 7.3)
exemplo = pd.DataFrame([{"categoria": "Buraco na via", "subprefeitura": df["subprefeitura"].iloc[0], "mes": 11, "dia_semana": 2}])
print("Prazo previsto (dias):", int(round(float(joblib.load(os.path.join(RAIZ, "models", "modelo_prazo.joblib"))["pipeline"].predict(exemplo)[0]))))
'''),
    md("""## 6. Conclusões
* **Comparação dos modelos (na ordem das aulas):** em dias brutos, a Regressão Linear (MAE 30,2) e a Árvore de Decisão (28,4) erraram mais do que uma simples tabela com a mediana de cada categoria (24,5). Quando treinamos em log(1 + dias), a Árvore já passou a tabela (23,9) e o Random Forest foi o melhor (23,3, sem o mês). Escolhemos o Random Forest sabendo que ele é mais difícil de explicar do que a árvore.
* **Ganhou do baseline, mas por pouco:** 23,3 dias de erro médio contra 24,5 da tabela de medianas, uma diferença de 1,1 dia (4,6%). Na validação cruzada com 5 folds deu 23,28 ± 0,35, então o resultado não foi sorte da divisão dos dados.
* **Por que o R² é baixo:** R² de 0,058 e RMSE de 61,0. O modelo explica pouco da variação porque alguns chamados levam centenas de dias e nenhuma das 4 informações da abertura explica o motivo.
* **Onde erra menos e onde erra mais:** Árvore com risco (2,6 dias) e Descarte (2,8) fecham rápido e são fáceis de prever. Buraco erra 20,3 dias; Bueiro, 25,6; Calçada, 37,6; Poda, 45,8; e Sinalização, 48,6.
* **Teste no tempo (treino 2020–2022, teste 2023):** 37,8 dias sem o mês, 38,2 com o mês e 38,7 na tabela de medianas. O mês piora a previsão do futuro, então tiramos o mês do modelo (a API continua aceitando o campo). Também vimos que prever o futuro é mais difícil do que prever chamados sorteados do mesmo período.
* **Limitações:** temos poucas variáveis; o "prazo" do SP156 vai até o órgão fechar o protocolo, não necessariamente até o conserto; os dados incluem a pandemia e não têm fev–mar/2021 nem abr–jun/2023 (o portal hoje já publica o 2º e o 4º trimestres de 2023, que podem entrar num próximo treino); e Iluminação fica sem previsão. Para o cidadão, mostramos a previsão como estimativa, nunca como garantia."""),
]

# ======================================================================= 03 ATRASO
atraso = [
    md("""
# 03 · Modelo 2 — Risco de atraso (classificação)
**Projeto ZelaBairro · Global Solution 2026/2 · IA & Chatbot**

**Integrantes (turma 1TDSPV):** Leonardo Afonço Sousa (RM 573982) · Syang Cristina Gomes Souza (RM 569259) ·
Matheus Jones Sousa de Freitas (RM 573559) · Vitor Goncalves de Souza (RM 569023) · Joao Machado Nascimento (RM 572364)

**Pergunta:** esta ocorrência vai passar do prazo de referência da sua categoria?

* Alvo: `atrasou` (1 = sim, 0 = não), com a **mesma regra da RN11**: `dias_para_resolver > nr_prazo_dias`
* Entradas: `categoria`, `subprefeitura`, `mes`, `dia_semana`
* Caminho seguido (como nas Aulas 05 e 06): **modelo que chuta** (baseline) → modelos interpretáveis (**Regressão Logística** e **Árvore de Decisão**)
  → **Random Forest**
* Métricas (as da Aula 06): **matriz de confusão, acurácia, precisão, recall, F1 e curva ROC / AUC**
"""),
    code(SETUP),
    md("## 1. Preparação e equilíbrio das classes"),
    code('''
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.dummy import DummyClassifier
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, roc_curve,
                             confusion_matrix, classification_report, ConfusionMatrixDisplay)
from ml_utils import FEATURES, montar_pipeline

SEED = 42
X, y = df[FEATURES], df["atrasou"]
print("Distribuição do alvo:"); print(y.value_counts().rename({0: "no prazo (0)", 1: "atrasou (1)"}).to_frame("n").assign(pct=lambda d: (d.n / d.n.sum()).round(3)))
X_treino, X_teste, y_treino, y_teste = train_test_split(X, y, test_size=0.2, random_state=SEED, stratify=y)
print(f"\\ntreino: {len(X_treino):,} | teste: {len(X_teste):,}")
'''),
    md("""
A divisão é **estratificada** para manter a proporção de atrasos no treino e no teste. Se as classes forem
muito desiguais, a acurácia sozinha engana (um modelo que sempre diz "não atrasa" acertaria muito),
por isso olhamos também precisão, recall e F1 (Aula 06: **F1 é a métrica recomendada em base desbalanceada**; **recall** quando o falso
negativo é caro) e usamos `class_weight="balanced"`: ele dá mais peso aos atrasos durante o treino, para o modelo não "chutar" sempre
"no prazo" (o problema da acurácia ilusória da Aula 05).
"""),
    md("## 2. Baseline e comparação de modelos"),
    code('''
def metricas_de(pipe):
    p = pipe.predict(X_teste)
    proba = pipe.predict_proba(X_teste)[:, 1]
    return {"acuracia": accuracy_score(y_teste, p), "precisao": precision_score(y_teste, p, zero_division=0),
            "recall": recall_score(y_teste, p, zero_division=0), "f1": f1_score(y_teste, p, zero_division=0),
            "roc_auc": roc_auc_score(y_teste, proba)}

candidatos = {
    "Baseline (classe mais comum)": montar_pipeline(DummyClassifier(strategy="most_frequent")),
    "Regressão Logística (sem mês)": montar_pipeline(LogisticRegression(max_iter=1000, class_weight="balanced")),
    "Árvore de Decisão (sem mês)": montar_pipeline(DecisionTreeClassifier(max_depth=10, min_samples_leaf=50, class_weight="balanced", random_state=SEED)),
    "Random Forest COM mês": montar_pipeline(RandomForestClassifier(n_estimators=60, min_samples_leaf=20, class_weight="balanced", n_jobs=-1, random_state=SEED), usar_mes=True),
    "Random Forest SEM mês": montar_pipeline(RandomForestClassifier(n_estimators=60, min_samples_leaf=20, class_weight="balanced", n_jobs=-1, random_state=SEED), usar_mes=False),
}
linhas = []
for nome, pipe in candidatos.items():
    pipe.fit(X_treino, y_treino)
    linhas.append({"modelo": nome, **metricas_de(pipe)})
pd.DataFrame(linhas).round(3).set_index("modelo")
'''),
    md("""
**Como ler:** o baseline mostra a acurácia "de graça": como só ~30% dos chamados atrasam, dizer sempre "no prazo" acerta ~70%.
A Regressão Logística e a Árvore de Decisão são os modelos interpretáveis da aula; o Random Forest combina muitas árvores (Aula 05)
e é escolhido se ganhar deles em F1 e ROC AUC.
**Resultado honesto:** com `class_weight="balanced"` as florestas ficam **abaixo do baseline em acurácia**, porque trocam acurácia por recall
(preferem avisar risco a deixar passar um atraso). O ganho real está no **ROC AUC (~0,75 sem mês)**, que mostra que o modelo **ordena** bem
quem tem mais risco, e no **recall (~0,8)** para a classe "atrasou". O preço são muitos falsos positivos (veja a matriz de confusão e a
tabela de limiares). Diga isso na apresentação em vez de citar só a acurácia.
"""),
    md("""
### Teste "no tempo": treinar em 2020–2022 e testar em 2023
A divisão aleatória mistura os anos; o uso real é **prever o futuro** com dados do passado. Esta comparação decide se o **mês** entra no modelo:
"""),
    code('''
ano = pd.to_datetime(df["data_abertura"]).dt.year
tr_t = df[ano <= 2022].sample(250_000, random_state=SEED); te_t = df[ano == 2023].sample(80_000, random_state=SEED)
linhas = [{"modelo": "Baseline (classe mais comum)",
           "acuracia": max(te_t["atrasou"].mean(), 1 - te_t["atrasou"].mean()), "f1": 0.0, "roc_auc": 0.5}]
for nome, com_mes in [("Random Forest SEM mês", False), ("Random Forest COM mês", True)]:
    m_t = montar_pipeline(RandomForestClassifier(n_estimators=60, min_samples_leaf=20, class_weight="balanced", n_jobs=-1, random_state=SEED), usar_mes=com_mes).fit(tr_t[FEATURES], tr_t["atrasou"])
    pr = m_t.predict_proba(te_t[FEATURES])[:, 1]
    linhas.append({"modelo": nome, "acuracia": accuracy_score(te_t["atrasou"], pr >= .5), "f1": f1_score(te_t["atrasou"], pr >= .5), "roc_auc": roc_auc_score(te_t["atrasou"], pr)})
pd.DataFrame(linhas).round(3).set_index("modelo")
'''),
    md("""
Treinando em 2020–2022 e testando em 2023, o modelo **com** mês fica **pior** (principalmente no ROC AUC) que o **sem** mês: o mês aprende o que aconteceu
em cada mês daqueles anos (pandemia, mutirões), e isso não se repete. **Decisão:** o modelo final **não usa o mês** (a API ainda aceita `mes`, mas o
ignora). Para mudar: `usar_mes=True` em `montar_pipeline` e retreinar.
"""),
    md("## 3. Ajuste de hiperparâmetros (busca pequena, modelo SEM mês)"),
    code('''
from sklearn.model_selection import GridSearchCV

grade = {"modelo__min_samples_leaf": [10, 20, 50], "modelo__max_depth": [None, 16]}
busca = GridSearchCV(montar_pipeline(RandomForestClassifier(n_estimators=100, class_weight="balanced", n_jobs=-1, random_state=SEED)), grade,
                     scoring="f1", cv=StratifiedKFold(3, shuffle=True, random_state=SEED), n_jobs=1)
# Busca numa AMOSTRA do treino (rápida); o modelo final usa TODO o treino.
amostra = X_treino.sample(min(30_000, len(X_treino)), random_state=SEED).index
busca.fit(X_treino.loc[amostra], y_treino.loc[amostra])
print("Melhores parâmetros (busca na amostra):", busca.best_params_)
print(f"F1 médio na validação cruzada (amostra): {busca.best_score_:.3f}")
'''),
    md("## 4. Modelo final: avaliação no teste"),
    code('''
melhores = {k.replace("modelo__", ""): v for k, v in busca.best_params_.items()}
modelo = montar_pipeline(RandomForestClassifier(n_estimators=100, class_weight="balanced", n_jobs=-1, random_state=SEED, **melhores)).fit(X_treino, y_treino)
previsoes = modelo.predict(X_teste)
print(classification_report(y_teste, previsoes, target_names=["no prazo", "atrasou"], zero_division=0))
'''),
    code('''
cm = confusion_matrix(y_teste, previsoes, labels=[0, 1])
ConfusionMatrixDisplay(cm, display_labels=["no prazo", "atrasou"]).plot(cmap="Greens", values_format="d")
plt.title("Matriz de confusão (conjunto de teste)"); plt.show()
tn, fp, fn, tp = cm.ravel()
print(f"Verdadeiros negativos: {tn} | Falsos positivos: {fp} | Falsos negativos: {fn} | Verdadeiros positivos: {tp}")
'''),
    md("""
**Interpretação dos erros** (para a apresentação):
* *Falso positivo* — o modelo avisa risco de atraso e não atrasa: custo baixo (um alerta a mais).
* *Falso negativo* — o modelo não avisa e a ocorrência atrasa: é o erro mais caro para o cidadão.
"""),
    code('''
base = candidatos["Baseline (classe mais comum)"]
metricas = {
    "acuracia": float(accuracy_score(y_teste, previsoes)), "precisao": float(precision_score(y_teste, previsoes, zero_division=0)),
    "recall": float(recall_score(y_teste, previsoes, zero_division=0)), "f1": float(f1_score(y_teste, previsoes, zero_division=0)),
    "roc_auc": float(roc_auc_score(y_teste, modelo.predict_proba(X_teste)[:, 1])),
    "matriz_confusao": cm.tolist(), "baseline_acuracia": float(accuracy_score(y_teste, base.predict(X_teste))),
    "pct_atrasou_no_conjunto": float(y.mean()), "linhas_treino": int(len(X_treino)), "linhas_teste": int(len(X_teste)),
}
{k: (round(v, 3) if isinstance(v, float) else v) for k, v in metricas.items()}
'''),
    code('''
amostra_cv = X.sample(min(60_000, len(X)), random_state=SEED).index
cv = cross_val_score(modelo, X.loc[amostra_cv], y.loc[amostra_cv], cv=StratifiedKFold(5, shuffle=True, random_state=SEED), scoring="f1")
print(f"Validação cruzada (5 folds, amostra de {len(amostra_cv):,}) — F1: {cv.mean():.3f} ± {cv.std():.3f}")
'''),
    md("""
### Curva ROC (Aula 06)
A curva ROC mostra o compromisso entre a taxa de acertos genuínos (verdadeiros positivos) e a de alarmes falsos em todos os limiares.
Quanto mais a curva se afasta da diagonal (que é o "chute"), melhor; a **AUC** é a área sob a curva (0,5 = chute, 1 = perfeito).
Como na aula, usamos `predict_proba(X_teste)[:, 1]`, a probabilidade da classe "atrasou".
"""),
    code('''
proba = modelo.predict_proba(X_teste)[:, 1]
fig, ax = plt.subplots(figsize=(6, 5))
for nome, pipe_cmp, cor in [("Regressão Logística", candidatos["Regressão Logística (sem mês)"], "#b8bfc6"),
                            ("Árvore de Decisão", candidatos["Árvore de Decisão (sem mês)"], "#f2b134"),
                            ("Random Forest (final)", modelo, "#0f5c5a")]:
    p_cmp = pipe_cmp.predict_proba(X_teste)[:, 1]
    taxa_falso_positivo, taxa_verdadeiro_positivo, limiares = roc_curve(y_teste, p_cmp)
    ax.plot(taxa_falso_positivo, taxa_verdadeiro_positivo, color=cor, lw=2, label=f"{nome} (AUC = {roc_auc_score(y_teste, p_cmp):.3f})")
ax.plot([0, 1], [0, 1], "r--", label="chute (AUC = 0,5)")
ax.set_xlabel("taxa de falsos positivos (alarmes falsos)"); ax.set_ylabel("taxa de verdadeiros positivos (recall)")
ax.set_title("Curva ROC no conjunto de teste", loc="left"); ax.legend(loc="lower right")
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False); plt.show()
'''),
    md("""
**A probabilidade é uma chance real?** Não exatamente. O `class_weight="balanced"` empurra as probabilidades para cima, então a
média prevista fica acima da taxa real de atrasos (célula abaixo). Por isso o ZelaBairro mostra ao cidadão só **risco alto/baixo**,
sem porcentagem.
"""),
    code('''
print(f"Probabilidade média prevista de atraso: {proba.mean():.1%} | taxa real de atraso no teste: {y_teste.mean():.1%}")
'''),
    md("""
### Limiar de decisão
A API devolve `risco_atraso = "S"` quando `probabilidade >= 0.5`. Esse limiar **não** vem do Documento Base:
é a escolha padrão deste projeto. A tabela abaixo mostra o efeito de outros limiares; se o grupo quiser
mudar, atualize o documento (nova versão) e o `predictor.py`.
"""),
    code('''
linhas = []
for lim in [0.3, 0.4, 0.5, 0.6, 0.7]:
    p = (proba >= lim).astype(int)
    linhas.append({"limiar": lim, "precisao": precision_score(y_teste, p, zero_division=0),
                   "recall": recall_score(y_teste, p, zero_division=0), "f1": f1_score(y_teste, p, zero_division=0)})
pd.DataFrame(linhas).round(3).set_index("limiar")
'''),
    md("### Importância das variáveis"),
    code('''
nomes = modelo.named_steps["prep"].get_feature_names_out()
imp = pd.Series(modelo.named_steps["modelo"].feature_importances_, index=nomes).sort_values(ascending=False)
imp.index = [i.replace("cat__", "") for i in imp.index]
imp.head(12).sort_values().plot.barh(figsize=(8, 4), color="#0f5c5a")
plt.title("12 variáveis mais importantes"); plt.tight_layout(); plt.show()
'''),
    md("## 5. Exportar o modelo (`models/modelo_atraso.joblib`)"),
    code('''
import joblib
os.makedirs(os.path.join(RAIZ, "models"), exist_ok=True)
modelo.fit(X, y)
joblib.dump({"pipeline": modelo, "metricas": metricas, "features": FEATURES, "usa_mes": False,
             "categorias_treino": {k: int(v) for k, v in df["categoria"].value_counts().items()}},
            os.path.join(RAIZ, "models", "modelo_atraso.joblib"), compress=3)
print("salvo em models/modelo_atraso.joblib")
'''),
    code('''
exemplo = pd.DataFrame([{"categoria": "Buraco na via", "subprefeitura": df["subprefeitura"].iloc[0], "mes": 11, "dia_semana": 2}])
pipe = joblib.load(os.path.join(RAIZ, "models", "modelo_atraso.joblib"))["pipeline"]
p = float(pipe.predict_proba(exemplo)[0][list(pipe.classes_).index(1)])
print({"risco_atraso": "S" if p >= 0.5 else "N", "probabilidade": round(p, 2)})
'''),
    md("""## 6. Conclusões
* **Comparação dos modelos (na ordem das aulas):** a Regressão Logística (F1 0,538, AUC 0,739) e a Árvore de Decisão (F1 0,549, AUC 0,736) já são bem melhores que chutar (AUC 0,5). A Árvore pega mais atrasos (recall 0,903), mas dá mais alarmes falsos (precisão 0,395). O Random Forest sem mês foi o melhor em F1 (0,561) e em AUC (0,759), as métricas que a aula indica para base desbalanceada. Com mês ele parece ainda melhor no teste aleatório (AUC 0,807), mas piora no teste no tempo, então ficou sem o mês.
* **A acurácia engana aqui:** o modelo final tem 0,609, menos que os 0,702 de quem sempre diz "no prazo". Isso acontece porque usamos `class_weight="balanced"` para o modelo não ignorar os atrasos. O que vale olhar é o AUC de 0,754 e o recall de 0,834.
* **Matriz de confusão (196.495 chamados de teste):** acertamos 48.841 atrasos e deixamos passar 9.710 (16,6% dos atrasos). Foram 67.199 alarmes falsos e 70.745 acertos de "no prazo". Precisão de 0,421 e F1 de 0,559. Na validação cruzada o F1 foi 0,556 ± 0,002, então o resultado se mantém.
* **Por que aceitamos tantos alarmes falsos:** para o cidadão, o pior erro é não avisar e o problema atrasar (falso negativo). Um alarme a mais só faz a ocorrência subir um pouco na fila do gestor.
* **Curva ROC:** a curva do Random Forest fica acima das curvas da Logística e da Árvore em quase todos os pontos (AUC 0,754 contra 0,739 e 0,736).
* **Limiar de decisão:** em 0,5, recall de 0,834 e precisão de 0,421. Em 0,3 o recall vai a 0,973 (precisão de 0,367). Em 0,6 a precisão sobe para 0,564, mas o recall cai para 0,438; em 0,7 fica em 0,646 e 0,298. Ficamos com 0,5.
* **A probabilidade não é uma chance real:** a média prevista é de 46,2%, mas só 29,8% dos chamados do teste atrasaram. Por isso, no site e no chatbot, mostramos só "risco alto" ou "risco baixo".
* **Hiperparâmetros:** o GridSearchCV, rodado numa amostra de 30 mil chamados, escolheu `max_depth=16`. No teste completo, a versão sem limite de profundidade ficou um pouco melhor (AUC 0,759 contra 0,754). A diferença é pequena; uma busca com amostra maior seria o próximo passo.
* **Limitações:** as mesmas do notebook 02. Com mais informação sobre cada chamado (descrição, gravidade real, local exato), o modelo poderia melhorar."""),
]

if __name__ == "__main__":
    os.makedirs(os.path.join(RAIZ, "notebooks"), exist_ok=True)
    salvar("01_eda.ipynb", eda)
    salvar("02_modelo_prazo.ipynb", prazo)
    salvar("03_modelo_atraso.ipynb", atraso)
