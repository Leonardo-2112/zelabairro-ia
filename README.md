# ZelaBairro · IA & Chatbot

**Integrantes (turma 1TDSPV):** Leonardo Afonço Sousa (RM 573982) · Syang Cristina Gomes Souza (RM 569259) ·
Matheus Jones Sousa de Freitas (RM 573559) · Vitor Goncalves de Souza (RM 569023) · Joao Machado Nascimento (RM 572364)

Parte da disciplina **Artificial Intelligence & Chatbot** da Global Solution 2026/2 (FIAP, CitizenTech).
Tudo segue o **Documento Base v1.5** (nomes de categorias, status, campos e contratos), em `docs/ZelaBairro-Documento-Base.pdf` do repositório do grupo.

**O que tem aqui**

| Peça | O que faz | Onde |
|------|-----------|------|
| Modelo 1 (regressão) | Prevê em quantos dias uma ocorrência será resolvida | `notebooks/02_modelo_prazo.ipynb` → `models/modelo_prazo.joblib` |
| Modelo 2 (classificação) | Prevê o risco de passar do prazo da categoria (RN11) | `notebooks/03_modelo_atraso.ipynb` → `models/modelo_atraso.joblib` |
| API Flask | `GET /health`, `POST /prever/prazo`, `POST /prever/atraso` | `app.py`, `predictor.py` |
| Chatbot | Atende o cidadão e usa a API acima | `chatbot/`, interface em `GET /` |

> ## Estado atual
> Treinado com dados **reais** do SP156: **1º tri/2020 a 3º tri/2023**, 982.475 chamados, 7 das 8 categorias. Os notebooks estão executados, e `models/*.joblib` e `data/dados_sp156.csv` estão incluídos. **Leia a seção 3 antes de apresentar**: ela explica a janela escolhida, o que os números significam e o que ainda depende do grupo.

---

## 1. Estrutura

```
zelabairro-ia/
├── data/            dados_sp156.csv (982 mil linhas, 63 MB) · depara_sp156.csv (serviço→categoria) · depara_distrito_subprefeitura.csv
├── notebooks/       01_eda · 02_modelo_prazo · 03_modelo_atraso  (.ipynb)
├── models/          modelo_prazo.joblib · modelo_atraso.joblib
├── chatbot/         chatbot.py (conversa) · intents.py (intenção/categoria) · responses.py (textos)
│                    clientes.py (HTTP) · regras.py (RN10/RN11) · static/index.html (interface)
├── scripts/         preparar_dados.py · treinar_modelos.py · gerar_notebooks.py · gerar_exemplos.py · empacotar.py
├── tests/           99 testes (pytest)
├── docs/            ANALISE_DOCUMENTO_BASE.md · EXEMPLOS_CONVERSAS.md
├── app.py · predictor.py · ml_utils.py · requirements.txt · Procfile · .env.example
├── COMO_RODAR.txt (passo a passo) · identificacao.txt (RM, nome e turma)
```

## 2. Instalação

Python 3.11 ou superior (testado com 3.12).

```bash
cd zelabairro-ia
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Dados e modelos

### 3.1 Por que 2020–2023 (verificado em todos os arquivos, 2012 → 3º tri/2023)

| Período | Situação | Uso |
|---------|----------|-----|
| 2012–2014 | Estrutura diferente (sem distrito) | não usado |
| 2015 → 3º tri/2016, 2018, 2019 | "Data do Parecer" no **mesmo dia da abertura em 73–100%** dos chamados: não mede atendimento | não usado |
| jan–set/2017 | Serve, mas é um ano parcial e antigo | não usado |
| **1º tri/2020 → 3º tri/2023** | Coluna nova **"Data de Finalização"**: só 8–18% no mesmo dia, tempos plausíveis | **treino** |

* **Faltou o 2º tri/2023** (não veio nos arquivos). O 2º tri/2021 veio em `.xlsx` e foi lido normalmente.
* **Fev–mar/2021 também não aparecem** em `data/dados_sp156.csv` (o 1º tri/2021 só traz janeiro). A causa não foi verificada nos arquivos de origem; diga isso se perguntarem.
* **Subprefeitura:** derivada do distrito por `data/depara_distrito_subprefeitura.csv` (96 → 32). **Conferido:** de 2020 a 2023 o SP156 traz a *Prefeitura Operacional*, e o mapa coincide com ela em **98,4%** de 807 mil chamados (as diferenças são chamados atendidos por outra subprefeitura). Os nomes em `tb_bairro.nm_subprefeitura` precisam ser os mesmos desse arquivo.
* **O que o "prazo previsto" mede:** pelo glossário oficial (`docs/glossario_sp156_2020.txt`), a "Data de Finalização" é a *data de fechamento do protocolo* pelo órgão competente; o SP156 não executa o serviço. Então o prazo é o **tempo até o órgão fechar o protocolo**, não necessariamente o dia do conserto.
* **Abertos e cancelados quase não existem:** nos arquivos de 2020–2023, só 0,0–0,4% dos chamados dessas categorias não estavam finalizados quando o relatório foi gerado. O viés de deixá-los de fora é desprezível.
* **Iluminação pública apagada:** os serviços de iluminação não aparecem no SP156 a partir de 2018, então **não há nenhum chamado dessa categoria na janela**. A API aceita a categoria (contrato), mas o chatbot **não mostra previsão** para ela e avisa o cidadão. `GET /modelo/info` lista as categorias com histórico (mínimo 200 chamados).
* **Pandemia:** 2020–2021 incluem a COVID-19, com atendimento irregular (buraco teve mediana de 32 dias no 1º tri/2020).
* **Fechamento no mesmo dia:** em Bueiro, Descarte e Árvore com risco, 45–53% dos chamados fecham com 0 dia, e o resto forma uma cauda longa.
* **Prazos de referência × realidade** (a tabela 6.4 congela hoje, 13/11):

| Categoria | Prazo 6.4 | Mediana real (dias) | % que atrasou | Chamados |
|-----------|-----|-----|-----|-----|
| Buraco na via | 15 | 9 | 33,0% | 474.597 |
| Poda de árvore | 30 | 28 | 48,5% | 205.595 |
| Descarte irregular de lixo | 10 | 1 | 2,9% | 170.435 |
| Bueiro entupido | 10 | 1 | 19,0% | 86.757 |
| Árvore com risco de queda | 5 | 0 | 11,4% | 19.685 |
| Sinalização de trânsito danificada | 10 | 18 | 61,3% | 16.006 |
| Calçada danificada | 30 | 11 | 30,2% | 9.400 |

  Os prazos da tabela 6.4 são coerentes com 2020–2023, exceto Sinalização (a mediana já passa do prazo). No total, 29,8% dos chamados atrasam.

### 3.2 Resultados

Conjunto de teste: 20%, `random_state=42`, 196 mil chamados. O teste "no tempo" treina em 2020–2022 e avalia em 2023.

| Modelo | Métricas no teste | Baselines |
|--------|----------|----------|
| M1 prazo: `RandomForestRegressor` sobre **log(1+dias)**, sem mês | **MAE 23,3 dias** · RMSE 61,0 · R² 0,06 | MAE 26,6 (mediana geral) · **24,5 (mediana por categoria)** |
| M2 atraso: `RandomForestClassifier` balanceado, sem mês | **ROC AUC 0,754** · recall 0,834 · precisão 0,421 · F1 0,559 · acurácia 0,609 | acurácia 0,702 (sempre "no prazo") |

**Comparação com os modelos vistos em aula** (os notebooks seguem o caminho das Aulas 05 e 06: modelo que chuta → modelos interpretáveis → Random Forest):

| Prazo (MAE em dias, menor é melhor) | | Atraso (F1 / ROC AUC, maior é melhor) | |
|---|---|---|---|
| Regressão Linear (dias brutos) | 30,2 | Regressão Logística | 0,538 / 0,739 |
| Árvore de Decisão (dias brutos) | 28,4 | Árvore de Decisão | 0,549 / 0,736 |
| Tabela de medianas por categoria | 24,5 | Modelo que chuta "no prazo" | 0 / 0,5 |
| Árvore de Decisão (log) | 23,9 | **Random Forest sem mês** | **0,561 / 0,759** |
| **Random Forest (log), final** | **23,3** | | |

Os notebooks também trazem a estatística descritiva do tempo de resolução (média, mediana, desvio padrão, quartis e outliers pela regra do IQR), gráficos no padrão de Dataviz da Aula 04, o desenho de uma Árvore de Decisão de profundidade 3 e a curva ROC dos três classificadores.

**Leitura honesta (para a defesa oral):**
* **M1** ganha da mediana por categoria, mas por pouco (1,1 dia). A categoria explica quase tudo; subprefeitura e dia da semana acrescentam pouco. O alvo em log foi escolhido porque o tempo tem cauda longa: em dias brutos a floresta tem R² melhor (0,17), mas erra mais em MAE (27,8) do que a própria mediana. O notebook 02 mostra as duas versões.
* **M2** fica **abaixo do baseline em acurácia**, porque `class_weight="balanced"` troca acurácia por recall. O valor dele está em ordenar o risco (AUC 0,75) e em pegar 83% dos atrasos, ao custo de muitos falsos positivos.
* **Probabilidade inflada:** o balanceamento empurra as probabilidades para cima (ex.: buraco na Lapa sai com 66%, mas só 33% dos buracos atrasam). Por isso o chatbot mostra só **risco ALTO/BAIXO**, sem porcentagem (decisão D4 do Documento Base; E2 em `docs/ANALISE_DOCUMENTO_BASE.md`). O notebook 03 compara a probabilidade média prevista com a taxa real de atrasos.
* **Mês fora:** no teste "no tempo" o mês **piora** os dois modelos: MAE 38,2 com mês × 37,8 sem; AUC 0,69 com × 0,77 sem. A API continua recebendo `mes`, mas ele é ignorado.

### 3.3 Refazer (se mudar prazo, de-para ou dados)

```bash
python scripts/preparar_dados.py --entrada "uploads/*trimestre-2020.csv" "uploads/arquivo-final-*trim_-202*.csv" \
    "uploads/arquivo-final-2-trim_-2021.xlsx" --inicio 2020-01-01 --fim 2023-09-30
# o script imprime o % de chamados com 0 dia por trimestre e AVISA se passar de 40%
jupyter notebook   # rode 01, 02 e 03 do início ao fim e salve com as saídas (01 e 03: minutos; 02: até ~3 h numa máquina comum)
pip freeze > requirements.lock   # use as mesmas versões do scikit-learn no deploy
```
`python scripts/treinar_modelos.py` refaz os dois modelos com os mesmos algoritmos e hiperparâmetros dos notebooks (sem a busca nem a validação cruzada) e grava em `models/`. Os `.joblib` entregues vêm dos notebooks.

## 4. Rodar a API e o chatbot

```bash
python app.py                         # http://localhost:5000
```
Abra <http://localhost:5000> para o chatbot. Teste a API:

```bash
curl localhost:5000/health
curl -X POST localhost:5000/prever/prazo  -H "Content-Type: application/json" \
     -d '{"categoria":"Buraco na via","subprefeitura":"Lapa","mes":11,"dia_semana":2}'
curl -X POST localhost:5000/prever/atraso -H "Content-Type: application/json" \
     -d '{"categoria":"Buraco na via","subprefeitura":"Lapa","mes":11,"dia_semana":2}'
```
Respostas: `{"prazo_previsto_dias": N}` e `{"risco_atraso": "S|N", "probabilidade": 0.xx}`. Erro de entrada: `400 {"erro": "categoria desconhecida: ..."}`. `dia_semana`: 0 = segunda … 6 = domingo (`weekday()` do Python).

### Variáveis de ambiente (`.env.example`)

| Variável | Para quê |
|----------|----------|
| `PORT` | Porta (o Render define sozinho) |
| `ZELA_API_URL` | URL da **API Java**. Com ela o chatbot checa ocorrências parecidas (RN07) e consulta status. Sem ela, o chatbot conversa, mas sem essas duas funções |
| `IA_API_URL` | URL pública **desta** API. Vazia = o chatbot usa os modelos dentro do processo (mesmo código dos endpoints) |
| `FRONT_URL` | URL do front na Vercel, usada nos links mostrados ao cidadão |
| `CORS_ORIGINS` | Origens liberadas (lista separada por vírgula). Em produção, coloque a URL da Vercel |

**Integração com a Java:** a API Java deve ter `IA_API_URL` apontando para este serviço (Documento Base 7.4) e usar o fallback da RN12 se ele estiver fora do ar.

### O que o chatbot faz

* Recebe o cidadão, explica a finalidade e entende o que ele quer (registrar, consultar, apoiar, explicar prioridade/prazo).
* **Registro guiado:** descrição (RN03: 10 a 500 caracteres) → categoria (reconhece pelo texto; se tiver dúvida, pergunta) → bairro → **sugere apoiar ocorrências abertas/em andamento da mesma categoria e bairro (RN07)** → endereço (RN03: até 200) → **previsão de prazo e risco vinda da API de IA** → orienta a concluir no site.
* **Consulta** `ocorrência 15`: mostra situação, apoios, prioridade e a previsão, **sem e-mail nem telefone** e só com o primeiro nome do autor (RN13).
* Sempre avisa que prazo e risco são **estimativas**, não garantias.
* **Falhas:** IA fora do ar → registra assim mesmo, sem previsão (RN12). API Java fora do ar → pergunta a subprefeitura e segue.
* O chatbot **não grava** ocorrências: quem grava é o front/API Java, com o cidadão identificado. Veja `docs/ANALISE_DOCUMENTO_BASE.md`.

Exemplos completos: `docs/EXEMPLOS_CONVERSAS.md` (gerado com APIs simuladas: os números de previsão ali são ilustrativos).

## 5. Testes

```bash
python -m pytest tests -q
```
Cobrem (99 testes): os 4 exemplos oficiais da RN10, RN11, contrato da API (inclusive o 400 exato), entradas inválidas, reconhecimento de categoria/intenção, fluxos de conversa, RN07, RN12 e RN13. Os testes de API treinam modelos com **dados sintéticos em pasta temporária** (nunca em `models/`); as métricas deles não valem como resultado.

## 6. Deploy no Render (API Flask)

* Build: `pip install -r requirements.txt` · Start: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 60` (já no `Procfile`).
* Suba `models/*.joblib` (9 MB no total) junto com o código, senão o Render não terá os modelos.
* Variáveis: `CORS_ORIGINS`, `ZELA_API_URL`, `FRONT_URL`; não coloque senha de banco aqui (este serviço não acessa o Oracle).
* Plano gratuito dorme: **abra `/health` alguns minutos antes da demo**.

## 7. Roteiro para a apresentação (20 pontos da demo da API)

1. `GET /health` → ok. 2. `POST /prever/prazo` e `/prever/atraso` com a Lapa (mostre o **400** com categoria errada).
3. Abra o chatbot: registre um problema, mostre a **sugestão de apoio (RN07)** e a **previsão vindo da API**.
4. Derrube a IA (ou aponte `IA_API_URL` para uma URL inválida) e mostre a **RN12**.
5. Tenha à mão as métricas **do seu CSV** e o baseline: diga o que o modelo acerta e o que não acerta (limitações em `docs/ANALISE_DOCUMENTO_BASE.md`).

## 8. Entrega (19/11, até 23h55, sem prorrogação)

`python scripts/empacotar.py` monta o `.zip` sem `__pycache__`, sem `.env` e **recusa empacotar** se faltar CSV, modelos ou se um notebook estiver sem saídas. O `identificacao.txt` (RM, nome e turma de cada integrante) já está na raiz do projeto e vai também na raiz do `.zip`.
Lembre do **registro de uso de IA** (ferramentas, prompts, o que foi aceito, corrigido ou descartado): este código foi gerado com apoio do Claude e deve ser revisado e entendido por todos, pois qualquer integrante pode ser arguido.

## 9. Mapa dos critérios de nota (slides oficiais da disciplina)

**Entrega (100 pts)** — falta de arquivo ou arquivo corrompido **zera o item**.

| Critério | Pts | Onde está |
|----------|-----|-----------|
| Dados usados no treino | 10 | `data/dados_sp156.csv` + de-paras (seção 3) |
| Notebooks (EDA, treino, avaliação) | 60 | `notebooks/01…03` **executados, com saídas** |
| Modelos pré-treinados | 10 | `models/modelo_prazo.joblib`, `models/modelo_atraso.joblib` (já gerados) |
| API Flask e integração | 20 | `app.py`, `predictor.py` (consome os `.joblib`) |
| `.txt` com nomes e RMs | — | `identificacao.txt` (pronto) |

Penalidades: fora do prazo (19/11, 23h55) = zero; menos de 2 modelos = até −30; API que não executa ou não consome os modelos = até −20.
Os slides **não exigem chatbot**: ele é um complemento. Se faltar tempo, priorize dados, notebooks e modelos.

**Apresentação (23 a 27/11, 100 pts)** — como se preparar:

| Critério | Pts | O que mostrar |
|----------|-----|---------------|
| Problema CitizenTech e papel da IA | 15 | Seções 3 e 4 do Documento Base |
| Dados e EDA | 15 | Fonte, data de download, de-para, insights do notebook 01 |
| Escolha dos modelos e justificativa | 20 | Por que regressão (prazo) e classificação (atraso); comparação com baseline |
| Métricas e interpretação | 20 | MAE/RMSE/R² e matriz de confusão **do seu CSV**; falso negativo é o erro mais caro |
| Demo ao vivo da API | 20 | Roteiro da seção 7 |
| Domínio técnico (todos respondem) | 10 | Cada integrante deve saber explicar `ml_utils.py`, o alvo `atrasou` e a RN11 |
