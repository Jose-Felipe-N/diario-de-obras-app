# Experimentos do Analista IA

Este documento registra como o assistente de IA foi avaliado: os dados usados, as decisões de método, os resultados antes e depois de cada mudança, as falhas e as limitações. As seções de resultados serão preenchidas a cada medição.

## Dados de avaliação

Os dados de avaliação são fictícios, gerados uma única vez e congelados em JSON na pasta `dados/`. Os eventos marcantes, que servem de gabarito para as perguntas de texto livre, estão em [dados/eventos.md](../dados/eventos.md).

O esqueleto (obras, diários, equipes, equipamentos, gastos e orçamentos) é produzido por [scripts/gerar_esqueleto.py](../scripts/gerar_esqueleto.py) com semente fixa. Um teste confirma que o arquivo versionado é exatamente o que o gerador produz, então qualquer pessoa pode reproduzir os dados. O gerador não faz parte do produto: ele só fabrica o cenário de teste. O `seed.py` carrega esses dados num banco, para desenvolvimento, demonstração ou avaliação.

### Comparação entre orçado e gasto

O orçamento tem custo de material e de mão de obra, mas os diários registram a equipe própria só em horas, sem valor em reais. Por isso, a comparação "dentro do orçamento" usada no gabarito é **material com material**: o custo de material orçado contra a soma dos gastos de Material de Construção lançados nos diários da obra.

### Nomes neutros nas obras

Removi do nome das obras um dado que vazava a resposta. No banco de desenvolvimento as obras se chamam "Galpão Logístico (ATRASADA)" e "Casa Condomínio (No Prazo)". Com esses nomes, o modelo responde "qual obra está atrasada?" lendo o nome, sem analisar o cronograma, e isso inflaria o acerto do baseline. Nos dados de avaliação, as obras se chamam Casa Condomínio, Reforma Loja Shopping e Galpão Logístico. O atraso só pode ser descoberto pelas etapas.

### O que conta como "parou"

- **A obra parou:** o diário existe, mas não tem nenhuma linha de efetivo, ou a jornada foi de no máximo 2 h por trabalhador.
- **A chuva parou a obra:** o diário tem chuva ou tempestade, o trabalho foi no exterior (ou a obra é aberta) e a obra parou no sentido acima.
- **Não há registro:** não existe diário naquela data. É diferente de "parou" e exige outra resposta.

No Galpão Logístico (obra mista), em parte dos dias de chuva a equipe vai para a área coberta e trabalha a jornada normal. Nesses dias, a chuva **não** parou a obra.

## Método

### Conjunto de perguntas

São **20 perguntas** em [dados/perguntas.json](../dados/perguntas.json), cobrindo sete grupos: texto livre, clima com texto, números, premissa errada, orçado contra gasto, segurança (fora de escopo, injeção de prompt e isolamento entre obras) e dados novos. 15 têm uma obra selecionada e 5 são gerais. O plano inicial era de 30; o conjunto foi reduzido por prazo, mantendo todos os grupos. Os números do gabarito são calculados por SQL em [scripts/calcular_gabarito.py](../scripts/calcular_gabarito.py), e um teste confere que batem com os dados.

Com 20 perguntas, cada uma vale 5 pontos percentuais, por isso os resultados são reportados em contagens ("17 de 20"), por grupo, e não em porcentagens.

### Conjunto reservado

Das 20 perguntas, 4 são **reservadas** (Q7, Q12, Q14 e Q17, uma por grupo principal): escolhidas antes do baseline e com o resultado pergunta a pergunta fechado até a medição final. Elas entram nas duas medições oficiais (antes e depois), mas não são usadas para depurar o assistente durante as etapas de melhoria.

O objetivo é detectar sobreajuste: se o acerto subir nas 16 perguntas visíveis e não nas 4 reservadas, a melhora provavelmente veio de ajustes feitos para o conjunto de avaliação, e não de um assistente melhor. Com só 4 perguntas, a comparação é um sinal, não uma prova estatística.

## Busca por tema (RAG)

Cada observação não vazia vira um documento no ChromaDB, com o texto prefixado por obra, data e clima (`title: ... | text: ...`) e metadados de obra e data para filtrar. Os vetores vêm do `gemini-embedding-2` com 768 dimensões; como esse modelo não tem `task_type`, a tarefa vai num prefixo da consulta (`task: question answering | query: ...`). Antes de cada busca, o índice é reconciliado com o banco por id e hash do texto: diários criados, editados ou apagados entram na busca sem ganchos espalhados pelo código. Se um embedding falhar, a ferramenta avisa que há diários indisponíveis, em vez de concluir que não há registro.

**Por que ChromaDB.** Com 142 observações, uma busca exata em memória seria suficiente e até mais simples. O ChromaDB foi uma escolha didática, para aprender na prática um banco vetorial usado em produção (coleções, metadados, filtros e reindexação). Em escala (dezenas de milhares de documentos), a busca aproximada de um banco vetorial passa a compensar.

**Limite do nível gratuito.** O limite de embeddings conta cada texto do lote como uma requisição (100 por minuto). A primeira indexação foi cortada no terceiro lote; a reconciliação deixou os textos restantes pendentes e os indexou na busca seguinte. A indexação agora respeita 90 textos por minuto.

**Primeiro teste de recuperação (sem o modelo, só a busca).** Com a pergunta do engenheiro como consulta, o evento certo ficou em 1º lugar em "problema com água" (E01), "deu pau em máquina" (E13) e "o cliente pediu mudança" (E10 e E17 em 1º e 2º). Em "algum fornecedor furou", a armadilha E07 ("esquecemos de pedir o diesel", uma falha interna) ficou em 1º: a busca vetorial aproxima "faltou material" de "o fornecedor não entregou", mas não distingue a causa. Com a consulta reescrita como o modelo faria ("material não chegou, atraso na entrega do fornecedor"), E11 e E12 sobem para 2º e 3º, e a E07 continua em 1º. Cabe ao modelo descartá-la, que é exatamente o item proibido do gabarito da Q5.

## Limitações

- **Dados sintéticos escritos pelo autor.** A mesma pessoa escreveu os eventos, as perguntas e as melhorias do assistente. Isso cria risco de sobreajuste ao conjunto de avaliação. As proteções adotadas: perguntas e gabarito congelados antes de mexer no assistente (tag `baseline`); melhorias por técnicas gerais (ferramentas SQL, busca por tema, saída validada), sem regras para estas obras; perguntas na voz do usuário, com paráfrases, erros de digitação e premissas erradas; um grupo que cria e apaga diários durante o teste; e o conjunto reservado.
- **Conjunto pequeno.** 20 perguntas, 1 rodada por medição (nível gratuito da API). Diferenças de 1 ou 2 perguntas entre o antes e o depois podem ser variação do modelo, não melhora real.
- **Injeção de prompt só direta.** O conjunto testa um usuário tentando manipular o assistente, mas não um texto malicioso escondido numa observação de diário (injeção indireta).
- **Sem usuários reais.** As perguntas imitam um engenheiro de obra, mas não vieram de um. O conjunto não mostra como o assistente se sai com o vocabulário, os erros e as necessidades de usuários reais.
- **Avaliação não é garantia.** Ela dá evidência de que o assistente acerta em dados representativos; a segurança em uso real depende também das proteções em tempo de execução (saída validada, obra aplicada pelo servidor, recusa fora do escopo) e do monitoramento em produção.

## Roadmap

- **Monitoramento em produção.** Registrar perguntas e respostas (com consentimento e dados anonimizados), coletar a avaliação do usuário (👍/👎) e transformar as perguntas reais que falharem em novas perguntas do conjunto de avaliação. Assim o conjunto deixa de ser só sintético e passa a refletir o uso real. Depende de haver usuários.

- **Listas da tela persistidas no banco.** O usuário pode acrescentar funções, equipamentos e itens de gasto para adaptar o sistema à sua obra, mas essas edições vivem só na sessão do navegador: somem quando o app reinicia e cada navegador tem a sua lista. Persistir exige uma tabela de catálogo e uma rota na API. Ficou para depois da avaliação, para não alterar o sistema durante a medição.
- **Quantidade e valor unitário nos gastos.** Hoje o modelo `Gasto` guarda só `item`, `categoria` e `valor` total. Acrescentar `quantidade` e `valor_unitario` permitiria perguntas sobre preço, como "quanto pagamos a mais no cimento de emergência?". Mudaria o frontend, os schemas, o seed e os dados de avaliação, por isso ficou fora desta rodada.
