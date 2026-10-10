# Experimentos do Analista IA

Este documento registra como o assistente de IA foi avaliado: os dados usados, as decisões de método, os resultados antes e depois de cada mudança, as falhas e as limitações. As seções de resultados serão preenchidas a cada medição.

## Dados de avaliação

Os dados de avaliação são fictícios, gerados uma única vez e congelados em JSON na pasta `dados/`. Os eventos marcantes, que servem de gabarito para as perguntas de texto livre, estão em [dados/eventos.md](../dados/eventos.md).

### Nomes neutros nas obras

Removi do nome das obras um dado que vazava a resposta. No banco de desenvolvimento as obras se chamam "Galpão Logístico (ATRASADA)" e "Casa Condomínio (No Prazo)". Com esses nomes, o modelo responde "qual obra está atrasada?" lendo o nome, sem analisar o cronograma, e isso inflaria o acerto do baseline. Nos dados de avaliação, as obras se chamam Casa Condomínio, Reforma Loja Shopping e Galpão Logístico. O atraso só pode ser descoberto pelas etapas.

### O que conta como "parou"

- **A obra parou:** o diário existe, mas não tem nenhuma linha de efetivo, ou a jornada foi de no máximo 2 h por trabalhador.
- **A chuva parou a obra:** o diário tem chuva ou tempestade, o trabalho foi no exterior (ou a obra é aberta) e a obra parou no sentido acima.
- **Não há registro:** não existe diário naquela data. É diferente de "parou" e exige outra resposta.

No Galpão Logístico (obra mista), em parte dos dias de chuva a equipe vai para a área coberta e trabalha a jornada normal. Nesses dias, a chuva **não** parou a obra.

## Roadmap

- **Quantidade e valor unitário nos gastos.** Hoje o modelo `Gasto` guarda só `item`, `categoria` e `valor` total. Acrescentar `quantidade` e `valor_unitario` permitiria perguntas sobre preço, como "quanto pagamos a mais no cimento de emergência?". Mudaria o frontend, os schemas, o seed e os dados de avaliação, por isso ficou fora desta rodada.
