# Exemplos de conversa

> Gerado por `scripts/gerar_exemplos.py`. O texto do assistente é o real; a **previsão (12 dias, risco alto) e as ocorrências vêm de APIs simuladas** para demonstrar o formato. Na demonstração, esses números virão dos modelos treinados com o SP156 e da API Java.

## 1. Registro completo (sem ocorrência parecida)

**Cidadão:** Oi

**Assistente:**

> Olá! Eu sou o assistente do ZelaBairro.
> Eu ajudo você a avisar a prefeitura sobre problemas do seu bairro, como buraco, poste apagado, lixo na calçada, árvore perigosa ou bueiro entupido.
> 
> Posso:
> - te ajudar a registrar um problema;
> - ver se alguém já avisou do mesmo problema, para você apoiar;
> - mostrar como está uma ocorrência;
> - explicar prioridade e prazo.
> 
> O que você precisa hoje?

**Cidadão:** O bueiro da minha rua está entupido e alaga tudo, na Pinheiros

**Assistente:**

> Entendi que o problema é: Bueiro entupido.
> Bairro: Pinheiros (subprefeitura Pinheiros).
> Não encontrei ocorrência parecida aberta nesse bairro. Então vamos registrar uma nova.
> Qual é o endereço de referência? Diga a rua, o número aproximado e um ponto de referência (até 200 caracteres).
> Exemplo: "Rua Guaicurus, 1200, em frente à padaria".

**Cidadão:** Rua Teodoro Sampaio, 800, em frente ao mercado

**Assistente:**

> Pronto, juntei as informações:
> - Tipo: Bueiro entupido
> - Bairro: Pinheiros (subprefeitura Pinheiros)
> - Endereço: Rua Teodoro Sampaio, 800, em frente ao mercado
> - Descrição: O bueiro da minha rua está entupido e alaga tudo, na Pinheiros
> 
> Com base no histórico de ocorrências parecidas, a previsão de resolução é de aproximadamente 12 dias. Sobre atraso, o modelo indica risco ALTO de passar do prazo normal desse tipo de problema (10 dias).
> Importante: esses números são uma estimativa calculada por inteligência artificial com base no histórico de chamados parecidos. Não são uma garantia de atendimento.
> 
> Para registrar de verdade, abra https://zelabairro.vercel.app/ocorrencias/nova, informe seu nome e e-mail e preencha esses dados. A ocorrência nasce com a situação ABERTA e você pode acompanhar depois.
> Quer ajuda com mais alguma coisa?

## 2. Evitando duplicidade (RN07): apoiar em vez de criar

**Cidadão:** Quero registrar um problema

**Assistente:**

> Conte com suas palavras qual é o problema. Escreva de 10 a 500 caracteres.
> Exemplo: "Buraco grande na faixa da direita, perto do ponto de ônibus".

**Cidadão:** Tem um buraco enorme na faixa da direita da avenida

**Assistente:**

> Entendi que o problema é: Buraco na via.
> Em qual bairro (ou distrito) fica o problema?

**Cidadão:** Moro na Lapa

**Assistente:**

> Bairro: Lapa (subprefeitura Lapa).
> Já existem ocorrências abertas do mesmo tipo nesse bairro:
> - Ocorrência 15: Buraco grande na faixa da direita, perto do ponto de ônibus (Aberta, 3 apoio(s))
> 
> Apoiar uma ocorrência que já existe é melhor do que criar outra repetida. É o mesmo problema que o seu? Responda sim para apoiar, ou "nova" para registrar outra.

**Cidadão:** sim

**Assistente:**

> Ótimo! Para apoiar a ocorrência 15, abra https://zelabairro.vercel.app/ocorrencias/15 e clique em Apoiar.
> Lembre: você só pode apoiar uma vez e não pode apoiar uma ocorrência que você mesmo registrou.

## 3. Mensagem ambígua: o assistente pergunta em vez de chutar

**Cidadão:** Quero reclamar

**Assistente:**

> Conte com suas palavras qual é o problema. Escreva de 10 a 500 caracteres.
> Exemplo: "Buraco grande na faixa da direita, perto do ponto de ônibus".

**Cidadão:** tem uma árvore perto da minha casa que me preocupa

**Assistente:**

> Não tenho certeza do tipo de problema. Qual destes é o mais parecido?
> 1. Poda de árvore
> 2. Árvore com risco de queda
> Responda com o número.

**Cidadão:** 2

**Assistente:**

> Entendi que o problema é: Árvore com risco de queda.
> Em qual bairro (ou distrito) fica o problema?

**Cidadão:** Pinheiros

**Assistente:**

> Bairro: Pinheiros (subprefeitura Pinheiros).
> Não encontrei ocorrência parecida aberta nesse bairro. Então vamos registrar uma nova.
> Qual é o endereço de referência? Diga a rua, o número aproximado e um ponto de referência (até 200 caracteres).
> Exemplo: "Rua Guaicurus, 1200, em frente à padaria".

**Cidadão:** Rua dos Pinheiros, 100

**Assistente:**

> Pronto, juntei as informações:
> - Tipo: Árvore com risco de queda
> - Bairro: Pinheiros (subprefeitura Pinheiros)
> - Endereço: Rua dos Pinheiros, 100
> - Descrição: tem uma árvore perto da minha casa que me preocupa
> 
> Com base no histórico de ocorrências parecidas, a previsão de resolução é de aproximadamente 12 dias. Sobre atraso, o modelo indica risco ALTO de passar do prazo normal desse tipo de problema (5 dias).
> Importante: esses números são uma estimativa calculada por inteligência artificial com base no histórico de chamados parecidos. Não são uma garantia de atendimento.
> 
> Para registrar de verdade, abra https://zelabairro.vercel.app/ocorrencias/nova, informe seu nome e e-mail e preencha esses dados. A ocorrência nasce com a situação ABERTA e você pode acompanhar depois.
> Quer ajuda com mais alguma coisa?

## 4. Consulta, explicações e ocorrência encerrada

**Cidadão:** como está a ocorrência 15?

**Assistente:**

> Ocorrência 15 - Buraco na via
> Bairro: Lapa (subprefeitura Lapa)
> Registrada por: Mariana
> Situação: Aberta, aberta em 10/11/2026 (1 dia(s) em aberto)
> Apoios: 3
> Prioridade: MEDIA (62 pontos)
> Prazo normal desse tipo de problema: 15 dias
> Previsão da IA: cerca de 12 dias. Risco de atraso: sim.
> Importante: esses números são uma estimativa calculada por inteligência artificial com base no histórico de chamados parecidos. Não são uma garantia de atendimento.
> Atrasada: não
> Histórico completo: https://zelabairro.vercel.app/ocorrencias/15

**Cidadão:** o que significa prioridade ALTA?

**Assistente:**

> A prioridade mostra o que a prefeitura deve atender primeiro. Ela é calculada com:
> - a gravidade do tipo de problema (risco à segurança pesa mais);
> - quantas pessoas apoiaram a ocorrência;
> - há quantos dias ela está aberta;
> - se existe risco de atraso ou se ela já está atrasada.
> 
> Os níveis são:
> - ALTA (70 pontos ou mais): atender primeiro.
> - MEDIA (de 40 a 69 pontos): atenção normal.
> - BAIXA (menos de 40 pontos): pode esperar um pouco mais.
> 
> Exemplo: árvore com risco de queda, 3 apoios, aberta há 2 dias e com risco de atraso soma 73 pontos e fica ALTA.
> Ocorrências já resolvidas ou canceladas não têm prioridade.

**Cidadão:** ocorrência 30

**Assistente:**

> Ocorrência 30 - Poda de árvore
> Bairro: Pinheiros (subprefeitura Pinheiros)
> Registrada por: Mariana
> Situação: Resolvida, aberta em 10/11/2026, encerrada em 12/11/2026
> Apoios: 3
> Prioridade: sem prioridade (ocorrência encerrada)
> Prazo normal desse tipo de problema: 30 dias
> Previsão da IA: cerca de 12 dias. Risco de atraso: sim.
> Importante: esses números são uma estimativa calculada por inteligência artificial com base no histórico de chamados parecidos. Não são uma garantia de atendimento.
> Histórico completo: https://zelabairro.vercel.app/ocorrencias/30

## 5. IA fora do ar (RN12): o registro continua

**Cidadão:** buraco enorme na minha rua na Lapa

**Assistente:**

> Entendi que o problema é: Buraco na via.
> Bairro: Lapa (subprefeitura Lapa).
> Não encontrei ocorrência parecida aberta nesse bairro. Então vamos registrar uma nova.
> Qual é o endereço de referência? Diga a rua, o número aproximado e um ponto de referência (até 200 caracteres).
> Exemplo: "Rua Guaicurus, 1200, em frente à padaria".

**Cidadão:** Rua das Flores, 10

**Assistente:**

> Pronto, juntei as informações:
> - Tipo: Buraco na via
> - Bairro: Lapa (subprefeitura Lapa)
> - Endereço: Rua das Flores, 10
> - Descrição: buraco enorme na minha rua na Lapa
> 
> Não consegui calcular a previsão agora, mas isso não impede o registro. O prazo normal desse tipo de problema é de 15 dias.
> 
> Para registrar de verdade, abra https://zelabairro.vercel.app/ocorrencias/nova, informe seu nome e e-mail e preencha esses dados. A ocorrência nasce com a situação ABERTA e você pode acompanhar depois.
> Quer ajuda com mais alguma coisa?

## 6. API Java fora do ar

**Cidadão:** quero registrar um problema

**Assistente:**

> Conte com suas palavras qual é o problema. Escreva de 10 a 500 caracteres.
> Exemplo: "Buraco grande na faixa da direita, perto do ponto de ônibus".

**Cidadão:** calçada quebrada na minha rua

**Assistente:**

> Entendi que o problema é: Calçada danificada.
> Não consegui consultar o sistema agora, então não posso verificar se alguém já registrou esse problema. Você ainda pode registrar normalmente no site.
> Em qual subprefeitura fica o problema? (Exemplo: Lapa, Pinheiros, Campo Limpo.)

**Cidadão:** Lapa

**Assistente:**

> Qual é o endereço de referência? Diga a rua, o número aproximado e um ponto de referência (até 200 caracteres).
> Exemplo: "Rua Guaicurus, 1200, em frente à padaria".

**Cidadão:** Rua A, 5

**Assistente:**

> Pronto, juntei as informações:
> - Tipo: Calçada danificada
> - Subprefeitura: Lapa
> - Endereço: Rua A, 5
> - Descrição: calçada quebrada na minha rua
> 
> Com base no histórico de ocorrências parecidas, a previsão de resolução é de aproximadamente 12 dias. Sobre atraso, o modelo indica risco ALTO de passar do prazo normal desse tipo de problema (30 dias).
> Importante: esses números são uma estimativa calculada por inteligência artificial com base no histórico de chamados parecidos. Não são uma garantia de atendimento.
> 
> Para registrar de verdade, abra https://zelabairro.vercel.app/ocorrencias/nova, informe seu nome e e-mail e preencha esses dados. A ocorrência nasce com a situação ABERTA e você pode acompanhar depois.
> Quer ajuda com mais alguma coisa?

## 7. Categoria sem histórico no SP156 (Iluminação): sem previsão, com o prazo de referência

**Cidadão:** Tem um poste apagado na minha rua, na Pinheiros

**Assistente:**

> Entendi que o problema é: Iluminação pública apagada.
> Bairro: Pinheiros (subprefeitura Pinheiros).
> Não encontrei ocorrência parecida aberta nesse bairro. Então vamos registrar uma nova.
> Qual é o endereço de referência? Diga a rua, o número aproximado e um ponto de referência (até 200 caracteres).
> Exemplo: "Rua Guaicurus, 1200, em frente à padaria".

**Cidadão:** Rua Teodoro Sampaio, 800

**Assistente:**

> Pronto, juntei as informações:
> - Tipo: Iluminação pública apagada
> - Bairro: Pinheiros (subprefeitura Pinheiros)
> - Endereço: Rua Teodoro Sampaio, 800
> - Descrição: Tem um poste apagado na minha rua, na Pinheiros
> 
> Para esse tipo de problema ainda não tenho histórico suficiente para estimar o prazo, então prefiro não chutar um número. O prazo de referência desse tipo de problema é de 7 dias.
> 
> Para registrar de verdade, abra https://zelabairro.vercel.app/ocorrencias/nova, informe seu nome e e-mail e preencha esses dados. A ocorrência nasce com a situação ABERTA e você pode acompanhar depois.
> Quer ajuda com mais alguma coisa?
