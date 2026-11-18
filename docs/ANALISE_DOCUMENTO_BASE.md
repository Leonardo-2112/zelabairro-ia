# Análise do Documento Base × disciplina IA & Chatbot

Feita antes da implementação (como pedido) e **atualizada em 15/11** com as decisões registradas no Documento Base v1.5 (seção 14.1). Aqui estão os conflitos, as lacunas e a decisão tomada em cada um. **Nada foi alterado no escopo aprovado sem estar listado aqui**; o que precisa de aval do grupo está marcado com **[GRUPO]**.

## Conflitos entre os documentos

| # | Conflito | Decisão tomada | Ação |
|---|----------|----------------|------|
| 1 | ~~O Documento Base (seção 4.4) põe "Chatbot" em "Fora do escopo"~~ | **Resolvido (decisão D1, Documento Base v1.3+):** o chatbot é complemento da disciplina de IA, fora do MVP do front, sem gravar ocorrências e sem mudar tabelas, rotas ou regras. | Nenhuma. |
| 2 | A seção 2.1 exige **"API REST em Flask consumindo os modelos"**; o pedido quer o chatbot **usando** essa API. | O chatbot chama `/prever/prazo` e `/prever/atraso` via HTTP quando `IA_API_URL` está definida. Sem a variável, roda o **mesmo código dos endpoints** dentro do processo (`predictor.py`). Os dois caminhos usam o mesmo contrato. | Na demo, defina `IA_API_URL` para mostrar a chamada real. |
| 3 | O pedido lista **"Subprefeitura"** como dado a coletar; no banco ela é atributo do **bairro** (`tb_bairro.nm_subprefeitura`). | O chatbot pergunta só o **bairro** e deriva a subprefeitura dele. Só pergunta a subprefeitura diretamente se a API Java estiver fora do ar. | Nenhuma. |
| 4 | O pedido diz que o chatbot deve **"orientar o registro"**, e o Documento Base não define quem cria a ocorrência quando ela nasce de uma conversa. Registrar exige `idCidadao` (RN01/RN02), e não há login. | O chatbot **não grava** ocorrências: coleta, valida (RN03), evita duplicados (RN07), mostra a previsão e manda o cidadão concluir no front (`/ocorrencias/nova`). | **[GRUPO]** se quiserem registrar pelo chat, é preciso decidir como identificar o cidadão (nome + e-mail) e chamar `POST /ocorrencias`. Fica como "próxima etapa". |
| 5 | O pedido lista **3 endpoints** exatos; o chatbot precisa de rotas próprias. | O contrato dos 3 endpoints ficou **idêntico** ao do Documento Base. Foram **acrescentadas** `GET /chat/inicio`, `POST /chat` e a interface em `GET /`. | Citar como extras na apresentação. |
| 6 | O **Python (disciplina)** proíbe `class` (nota zero). O chatbot usa classes. | A proibição vale para a **entrega de Python**, não para IA. Mas o código **não pode ser copiado** para o ZelaBairro Terminal. | **[GRUPO]** avisar quem faz a disciplina de Python. |

## Lacunas e pendências que bloqueiam entrega

| # | Pendência | Situação | O que fazer |
|---|-----------|----------|-------------|
| A | ~~CSV do SP156 ausente~~ | **Resolvido em 13/11:** recebidos todos os CSVs trimestrais de 2012 ao 3º tri/2023 (falta o 2º tri/2023). Treino com **1º tri/2020 a 3º tri/2023** (982.475 chamados). O CSV final também não tem chamados de fev–mar/2021 (causa não verificada nos arquivos de origem). | Ver README 3.1. |
| B | **Colunas reais** | Até 2019 a data de fim é a "Data do Parecer", que em 2015–16 e 2018–19 cai no mesmo dia da abertura (não mede atendimento). De 2020 em diante há **"Data de Finalização"** e **"Prefeitura Operacional"**. Os arquivos mudam de separador (`,` ou `;`), codificação (UTF-8 ou latin-1), formato de data (ISO ou dd/mm/aaaa) e alguns nomes de coluna; o 2º tri/2021 vem em `.xlsx`. | `preparar_dados.py` trata tudo isso por arquivo. Sem hora nem protocolo a partir de 2020, linhas idênticas são chamados diferentes: só se removem repetições **entre** arquivos. |
| C | **Dados não são de 2026.** A fonte vai só até set/2023. | O modelo reflete o atendimento de 2020–2023, incluindo o período da pandemia. | Dizer isso na apresentação e no notebook 01. Preencher a data de download na 1ª célula do notebook 01. |
| D | **De-para** | Feito por **serviço** (`data/depara_sp156.csv`). O de-para distrito → subprefeitura foi **conferido** com a Prefeitura Operacional: coincide em 98,4% dos chamados. | Revisar `depara_sp156.csv`: por exemplo, "Calçada particular" ficou de fora de propósito (responsabilidade do dono do imóvel) e "Queda de árvore" (árvore já caída) não entra em "Árvore com risco de queda". |
| D2 | **"Iluminação pública apagada" sem dados** | Os serviços de iluminação não aparecem no SP156 a partir de 2018. | API aceita a categoria; chatbot não dá previsão e avisa. **[GRUPO]** apresentar como limitação, ou treinar só essa categoria com 2017 (não recomendado: outra época, outra data de fim). |
| D3 | ~~Prazos da tabela 6.4 × realidade~~ | **Resolvido (decisão D5):** prazos mantidos como congelados em 13/11; Sinalização (prazo 10, mediana 18, 61% atrasam) vira ponto de atenção na apresentação. | Nenhuma. |
| D4 | **Mês fora do modelo** | No teste "no tempo" (treina 2020–2022, testa 2023), o mês piora os dois modelos. | Decisão tomada no notebook. A API mantém `mes` no contrato. |
| E | ~~Limiar do risco de atraso~~ | **Resolvido (decisão D2):** `risco_atraso = "S"` quando probabilidade ≥ 0,5 (recall 0,83, precisão 0,42). O notebook 03 mostra o efeito de 0,3 a 0,7. | Nenhuma. |
| E2 | ~~Probabilidade mostrada ao cidadão está inflada~~ | **Resolvido em 15/11 (opção a, decisão D4 do Documento Base v1.3):** o chatbot mostra só "risco ALTO/BAIXO", sem porcentagem. A API continua devolvendo `probabilidade` (contrato 7.3). | Nenhuma. |
| F | **Prazos e gravidades congelam hoje (13/11)** (seção 6.4). Os modelos usam `nr_prazo_dias` para criar o alvo do modelo 2. | O catálogo está em `chatbot/intents.py` (`CATEGORIAS`) exatamente como a tabela 6.4. | Se mudar prazo/gravidade, mude lá, nos testes e refaça `preparar_dados.py` + treino. |
| G | **Versão do scikit-learn.** O `.joblib` só carrega em versão compatível. | Se treinar na sua máquina e publicar no Render com outra versão, pode dar erro ao carregar. | Depois de treinar: `pip freeze > requirements.lock` e use as mesmas versões no deploy. |
| H | **Flask publicada** (desejável): sem ela, a Java cai na RN12 e a demo de IA é local. | Há `Procfile` pronto (`gunicorn app:app`). | Publicar no Render até 17/11. O plano gratuito dorme (~1 min): abra antes da demo. |

## Limitações dos modelos (para a defesa oral)

* **Viés de sobrevivência desprezível:** só chamados FINALIZADOS entram no treino, mas em 2020–2023 só 0,0–0,4% estavam abertos ou cancelados no relatório.
* **Período 2020–2023:** inclui a pandemia; os modelos refletem como o atendimento funcionava nesses anos.
* **"Prazo previsto" = tempo até o órgão fechar o protocolo** (glossário oficial do SP156), não até o conserto físico.
* **Chamados fechados no mesmo dia** (45–53% em Bueiro, Descarte e Árvore com risco): o glossário **não explica** o motivo. Eles ficaram no treino; tirar sem justificativa oficial seria escolher o resultado.
* **Ganhos modestos:** M1 ganha da mediana por categoria por ~1 dia de MAE; M2 tem acurácia abaixo do baseline (ganha em AUC e recall). Diga isso com clareza.
* **Poucas variáveis:** categoria, subprefeitura, mês e dia da semana. Não há descrição, local exato nem gravidade real do chamado. Compare sempre com o baseline antes de dizer que o modelo "funciona"; se não ganhar do baseline, diga.
* **Chatbot sem login:** desde a v1.2 o site tem login por e-mail e senha, mas o chatbot continua anônimo (não sabe quem é o cidadão) e por isso não lista "minhas ocorrências".
* **Chatbot baseado em regras:** reconhecimento de intenção e de categoria por palavras-chave e correção de digitação, sem dado de conversas para treinar. É explicável e testado, mas não entende frases muito livres: nesses casos ele pergunta em vez de chutar.
