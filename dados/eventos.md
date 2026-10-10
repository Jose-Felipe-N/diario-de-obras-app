# Eventos marcantes dos dados de avaliação

Rascunho escrito pelo Claude Code e revisado pelo autor do projeto. A versão lida por máquina, usada pelo gerador e pelo validador, é [eventos.json](eventos.json). Os dois arquivos devem ser alterados juntos.

Os eventos são o **gabarito** das perguntas de texto livre e dos testes de busca por tema (RAG). Cada um ocupa uma data única e é coerente com a etapa, o clima, o local e o diário do dia.

## Convenções

- **Data de referência ("hoje"):** quinta-feira, 08/10/2026. Nenhuma obra tem diário nessa data.
- **Ontem:** 07/10. **Essa semana:** 05/10 a 08/10. **Semana passada:** 28/09 a 04/10. **Últimas duas semanas:** 24/09 a 07/10.
- **R-n:** n dias antes da referência. **Dn:** n dias desde o início da obra, **contando o primeiro dia como D0** (na Reforma Loja Shopping, sex 10/07 = D0). O gerador e o validador usam as **datas** do `eventos.json`, nunca esses rótulos.
- **Clima "seco":** Sol ou Nublado nos dois períodos.
- **Local:** só vale para o Galpão Logístico (obra mista). A Casa Condomínio é sempre Exterior; a Reforma Loja Shopping é sempre Interior, e nela o clima não interfere.
- **Jornada:** "normal" = 8 h por trabalhador; "reduzida" = menos de 8 h; "parado" = diário sem linha de efetivo ou no máximo 2 h.
- Os nomes das obras são neutros, porque os nomes do banco de desenvolvimento ("ATRASADA", "No Prazo") entregavam a resposta.

## Obras e etapas

| Obra | Ambiente | Situação | Etapas com diário |
|---|---|---|---|
| Casa Condomínio | Aberto | Em andamento | Fundação 24/08–07/09; Alvenaria 08/09–06/10 (sem diário em 07/10) |
| Reforma Loja Shopping | Fechado | Concluída em 29/08 | Demolição 10/07–19/07; Revestimento e Pintura 20/07–29/08 |
| Galpão Logístico | Misto | Em andamento | Terraplanagem 10/06–10/07; intervalo 11/07–14/07; Estrutura Metálica 15/07–07/10 (sem diário em 30/09) |

## Restrições que o gerador precisa cumprir

| Data | Obra | Restrição | Motivo |
|---|---|---|---|
| 17/06 | Galpão Logístico | Tempestade em pelo menos um período, local Exterior, jornada "parado" | Véspera do atolamento (E05) |
| 28/09–04/10 | Galpão Logístico | Só 02/10 tem chuva | Gabarito da Q2 |
| 29/08 | Reforma Loja Shopping | O diário existe (sábado, jornada normal) | Data de conclusão da obra |
| 07/10 | Casa Condomínio | Sem diário | Furo: "ontem" sem registro |
| 30/09 | Galpão Logístico | Sem diário | Furo: premissa errada na semana passada |
| 08/10 | Todas | Sem diário | "Hoje" ainda não foi registrado |

## Calendário

| Cód. | Data | Quando | Obra | Etapa | Clima exigido (manhã/tarde) | Local | Jornada | Texto |
|---|---|---|---|---|---|---|---|---|
| E05 | qui 18/06 | D8, R-112 | Galpão Logístico | Terraplanagem | Nublado/Nublado | Exterior | reduzida (4 h) | Retro e caminhão atolaram no barro logo cedo, a manhã toda foi pra desatolar. |
| E06 | ter 30/06 | D20, R-100 | Galpão Logístico | Terraplanagem | Sol/Sol | Exterior | normal | Vizinho reclamou da poeira. Caminhão ficou molhando a pista de acesso o dia todo. |
| E12 ★ | seg 13/07 | D33, R-87 | Galpão Logístico | Intervalo | seco | Exterior | normal | Perfis da estrutura ainda não chegaram, ficamos só na organização do canteiro. |
| E02 | ter 14/07 | D4, R-86 | Reforma Loja Shopping | Demolição | livre | Interior | normal | Demolindo a copa antiga rompeu um ponto de água. Manutenção do shopping fechou o registro e consertou. |
| E16 ★ | qui 16/07 | D6, R-84 | Reforma Loja Shopping | Demolição | livre | Interior | reduzida (4 h) | Administração do shopping proibiu barulho até as 14 h, quebradeira só à tarde. |
| E17 | qua 05/08 | D26, R-64 | Reforma Loja Shopping | Revestimento e Pintura | livre | Interior | normal | Cliente mudou a cor da parede do fundo, vai ter que repintar. |
| E18 | qui 20/08 | D41, R-49 | Reforma Loja Shopping | Revestimento e Pintura | livre | Interior | normal | Vistoria da administração do shopping hoje, nenhuma pendência. |
| E01 ★ | qui 27/08 | D3, R-42 | Casa Condomínio | Fundação | Sol/Sol | Exterior | normal | Retro acertou o cano da rua abrindo a vala do baldrame. Concessionária veio consertar, vala parada umas 2 h. |
| E07 | seg 31/08 | D7, R-38 | Casa Condomínio | Fundação | seco | Exterior | normal | Esquecemos de pedir o diesel, a retro ficou parada boa parte da manhã. |
| E03 | qui 03/09 | D10, R-35 | Casa Condomínio | Fundação | Tempestade/Chuva | Exterior | parado (até 2 h) | Temporal desde cedo, concretagem do baldrame ficou pra depois. Turma só cobriu as formas e foi liberada. |
| E08 | ter 15/09 | D22, R-23 | Casa Condomínio | Alvenaria | seco | Exterior | normal | Erramos a conta do cimento, tivemos que comprar uns sacos no depósito do bairro pra não parar. |
| E09 | ter 22/09 | D29, R-16 | Casa Condomínio | Alvenaria | seco | Exterior | normal | Parede da sala saiu fora de prumo, desmanchamos e subimos de novo. |
| E10 | sex 25/09 | D32, R-13 | Casa Condomínio | Alvenaria | seco | Exterior | normal | Cliente passou aqui e pediu uma janela a mais no quarto dos fundos. Vão já ficou marcado. |
| E15 | ter 29/09 | D111, R-9 | Galpão Logístico | Estrutura Metálica | Sol/Sol | Exterior | normal | Montador cortou a mão na rebarba de um perfil, luva tava rasgada. Curativo no canteiro e voltou. |
| E11 ★ | qui 01/10 | D38, R-7 | Casa Condomínio | Alvenaria | seco | Exterior | normal | Tijolo não chegou. Pedreiros sem serviço, serventes ficaram na limpeza do canteiro. |
| E04 ★ | sex 02/10 | D114, R-6 | Galpão Logístico | Estrutura Metálica | Sol/Chuva | Interior | normal | Choveu à tarde, levamos a pré-montagem pra área coberta e o ritmo não caiu. |
| E13 ★ | seg 05/10 | D117, R-3 | Galpão Logístico | Estrutura Metálica | Sol/Sol | Exterior | normal | Guindaste deu defeito no hidráulico de manhã, locadora trocou depois do almoço. Montagem rendeu meio dia. |
| E14 ★ | qua 07/10 | D119, R-1 | Galpão Logístico | Estrutura Metálica | Nublado/Nublado | Interior | normal | Caiu a energia umas 4 h, gerador segurou a máquina de solda e a pré-montagem seguiu. |

## Pares parecidos

| Par | Eventos | O que difere |
|---|---|---|
| Água | E01 × E02 | Obra, causa (máquina abrindo vala × demolição) e local (Exterior × Interior) |
| Chuva | E03 × E04 | A obra parou × não parou (obra aberta × refúgio no interior do Galpão) |
| Fornecedor | E11 × E12 | Obra, material (tijolo × perfis) e etapa (Alvenaria × intervalo) |
| Pedido do cliente | E10 × E17 | Obra e o que mudou (janela × cor da parede) |

O E07 e o E08 são **falhas internas** (esquecemos, erramos a conta). Eles não podem casar com a Q5, que pergunta sobre fornecedores.

## Detalhes por evento

As palavras-chave são só os termos **distintivos** de cada evento. Palavras comuns do catálogo (cimento, tijolo, guindaste, solda, diesel, concretagem) continuam liberadas para a rotina. O validador proíbe as palavras-chave fora do evento.

| Cód. | Palavras-chave | Pergunta que responde | Diário do dia (efetivo · equipamentos · gastos) |
|---|---|---|---|
| E01 | cano da rua, concessionária, vala parada | "teve problema com água?" | Pedreiro, Servente, Armador, 8 h · Retroescavadeira · Vergalhão (Material de Construção); conserto sem custo |
| E02 | ponto de água, fechou o registro, manutenção do shopping, copa | "teve vazamento na loja?" | Servente, Pedreiro, Mestre de Obras, 8 h · Caminhão · Aluguel de caçamba (Locação) |
| E03 | concretagem ficou pra depois, foi liberada (*temporal* é palavra de clima) | "por que não concretaram o baldrame?" | Pedreiro e Servente, até 2 h · nenhum equipamento operando · sem gastos |
| E04 | área coberta, ritmo não caiu | "a chuva parou o galpão?" | Soldador, Montador, Servente, 8 h · Máquina de solda · Eletrodo (Material de Construção) |
| E05 | atolaram, barro, desatolar | "teve máquina atolada?" | Operador de Máquinas e Servente, 4 h · Retroescavadeira, Caminhão · Diesel (Combustível) |
| E06 | vizinho, poeira, molhando a pista | "teve reclamação de vizinho?" | Operador de Máquinas, Servente, Mestre de Obras, 8 h · Retroescavadeira, Compactador, Caminhão · Diesel (Combustível); Aluguel de rolo compactador (Locação) |
| E07 | esquecemos de pedir, diesel ... parada | "a retro ficou parada por quê?" | Pedreiro, Servente, Armador, 8 h (a parte manual seguiu) · Retroescavadeira · Diesel (Combustível) |
| E08 | erramos a conta, depósito do bairro | "faltou material alguma vez?" | Pedreiro e Servente, 8 h · Betoneira · Cimento (Material de Construção), sem preço diferenciado |
| E09 | fora de prumo, desmanchamos | "teve retrabalho?" | Pedreiro e Servente, 8 h · Betoneira, Andaime · Tijolo, Cimento (Material de Construção) |
| E10 | janela a mais, vão ... marcado | "o cliente pediu alguma mudança?" | Pedreiro, Servente, Mestre de Obras, 8 h · Andaime · Tijolo (Material de Construção) |
| E11 | não chegou, sem serviço, limpeza do canteiro | "algum fornecedor atrasou?" | Só Servente, 8 h (pedreiros dispensados) · nenhum equipamento · nenhum gasto de material |
| E12 | não chegaram, organização do canteiro | "algum fornecedor atrasou?" | Servente e Mestre de Obras, 8 h (equipe normal do intervalo) · Caminhão · Marmitex (Alimentação) |
| E13 | defeito no hidráulico, locadora trocou | "deu problema em máquina?" | Montador, Soldador, Servente, 8 h · Guindaste · Aluguel de guindaste (Locação), sem custo extra pela troca |
| E14 | caiu a energia, gerador segurou | "o que aconteceu ontem?" | Soldador, Montador, Eletricista, Servente, 8 h · Gerador, Máquina de solda · Diesel (Combustível), Eletrodo (Material de Construção) |
| E15 | cortou a mão, rebarba, luva, curativo | "alguém se machucou?" (no conjunto de 30, não é ★) | Montador, Soldador, Servente, 8 h · Guindaste · Perfil metálico, Parafuso (Material de Construção); sem gasto de EPI (o catálogo não tem esse item) |
| E16 | proibiu barulho, até as 14 h, quebradeira | "por que a demolição rendeu pouco?" | Servente e Pedreiro, 4 h · Caminhão · Aluguel de caçamba (Locação) |
| E17 | mudou a cor, repintar | "o cliente pediu alguma mudança?" | Pintor e Servente, 8 h · Andaime · Tinta (Material de Construção) |
| E18 | vistoria, nenhuma pendência | "a loja passou na vistoria?" | Pintor, Pedreiro, Eletricista, 8 h · Andaime · Massa corrida (Material de Construção) |

## Perguntas ★ da avaliação

| ★ | Eventos | Modo | Pergunta | Paráfrase | Ferramenta esperada |
|---|---|---|---|---|---|
| Q1 | E01 | Casa Condomínio | "teve algum problema com água aí na casa?" | sim | busca por tema |
| Q2 | E04 | Galpão Logístico | "semana passada choveu aí no galpão, a turma parou?" | parcial | ambas |
| Q3 | E13 | Galpão Logístico | "deu pau em alguma máquina essa semana?" | sim | busca por tema com filtro de período |
| Q4 | E14 | Galpão Logístico | "o que rolou ontem no galpão?" | sim | SQL (diário de 07/10, com a observação) |
| Q5 | E11, E12 | sem obra (pergunta geral) | "algum fornecedor furou com a gente?" | sim | busca por tema, sem filtro de obra |
| Q6 | E16 | Reforma Loja Shopping | "por que a demolição rendeu pouco?" | sim | ambas (SQL para as 4 h, busca para o motivo) |

Paráfrase em 5 das 6 perguntas.

### Gabaritos

**Q1, "teve algum problema com água aí na casa?"**
- Obrigatório: 27/08; a retroescavadeira acertou a tubulação da rua ao abrir a vala do baldrame; a concessionária consertou; a escavação ficou parada cerca de 2 h.
- Aceitável: etapa de Fundação; a turma seguiu na armação; o conserto não teve custo para a obra.
- Proibido: citar o E02 (copa, shopping ou qualquer coisa da Reforma Loja Shopping); dizer que não houve problema; inventar custo de conserto.

**Q2, "semana passada choveu aí no galpão, a turma parou?"**
- Obrigatório: declarar o período (28/09 a 04/10); não parou; só choveu na tarde de 02/10; a pré-montagem foi para a área coberta.
- Aceitável: jornada de 8 h e efetivo do dia; mencionar que não há diário em 30/09.
- Proibido: dizer que a obra parou; citar chuva em outro dia da semana; usar dias fora do período.

**Q3, "deu pau em alguma máquina essa semana?"**
- Obrigatório: declarar o período (05/10 a 08/10); E13: em 05/10 o guindaste teve defeito no hidráulico, a locadora trocou depois do almoço e a montagem rendeu meio dia.
- Aceitável: E14 (queda de energia em 07/10, gerador manteve a máquina de solda), **desde que não seja chamado de defeito de máquina**.
- Proibido: chamar a queda de energia de defeito de máquina; citar eventos fora do período (por exemplo, o E05); dizer que não houve problema.

**Q4, "o que rolou ontem no galpão?"**
- Obrigatório: 07/10; a energia caiu por cerca de 4 h; o gerador manteve a máquina de solda; a pré-montagem seguiu.
- Aceitável: efetivo e gastos do dia (Diesel, Eletrodo); trabalho no interior.
- Proibido: usar o diário de outro dia; dizer que não há registro.

**Q5, "algum fornecedor furou com a gente?"** (pergunta geral, sem obra selecionada)
- Obrigatório: E11, com obra e data (Casa Condomínio, 01/10, o tijolo não chegou); E12, com obra e data (Galpão Logístico, 13/07, os perfis da estrutura não chegaram).
- Aceitável: as consequências (pedreiros sem serviço; equipe só na organização do canteiro); citar o E13 (guindaste trocado pela locadora).
- Proibido: citar o E07 ou o E08 (falhas internas); perguntar de qual obra se trata (a pergunta é geral); descrever o E13 como atraso de entrega ou dizer que a locadora não resolveu.

**Q6, "por que a demolição rendeu pouco?"**
- Obrigatório: 16/07; jornada de 4 h; a administração do shopping proibiu barulho até as 14 h.
- Aceitável: efetivo e gastos do dia (aluguel de caçamba); a etapa de Demolição.
- Proibido: atribuir ao clima (a obra é fechada); citar outras obras.

## Perguntas relacionadas que não vêm de eventos

Vão para o conjunto de 30 perguntas.

| Pergunta | Modo | Ferramenta | Resposta esperada |
|---|---|---|---|
| "alguém se machucou aí no galpão?" (E15) | Galpão Logístico | busca por tema | Em 29/09, um montador cortou a mão na rebarba de um perfil; a luva estava rasgada; fez curativo no canteiro e voltou. |
| "o que rolou ontem?" | Casa Condomínio | SQL | Não há registro em 07/10, sem usar o diário de outro dia. |
| "o que rolou ontem?" | Reforma Loja Shopping | SQL | Sem registro; a obra foi concluída em 29/08. |
| "quanto gastamos de mão de obra na casa?" | Casa Condomínio | SQL | R$ 0 em Mão de Obra Externa. A equipe própria registra horas (total pelo SQL), não custo. Diferenciar "categoria sem gasto" de "sem registro". |
| "o cliente pediu alguma mudança?" | sem obra (pergunta geral) | busca, sem filtro de obra | **Exige o E10 e o E17, com obra e data:** Casa Condomínio, 25/09, janela a mais no quarto dos fundos; Reforma Loja Shopping, 05/08, troca da cor da parede do fundo. Proibido perguntar de qual obra se trata. |
| "o cliente pediu alguma mudança?" | Casa Condomínio | busca | Só o E10 (25/09). Proibido citar o E17. |
| "o cliente pediu alguma mudança?" | Reforma Loja Shopping | busca | Só o E17 (05/08). Proibido citar o E10. |
| "quanto já foi de cimento na casa?" | Casa Condomínio | SQL | Soma dos gastos com o item Cimento (dentro de Material de Construção), calculada por SQL sobre os dados gerados. Não depende do E08. Proibido somar a categoria inteira. |

## Decisões registradas

- **E05:** o texto não cita clima. O gerador força tempestade na véspera (17/06), e o validador confere essa véspera. A regra de palavras de clima não foi afrouxada.
- **Obra 2:** o diário de 29/08 existe. As datas das etapas não mudam. A obra começa numa sexta (10/07) e termina num sábado (29/08).
- **Sábados:** sempre têm diário, com jornada normal. Não há exceção de meio período.
- **Jornada:** jornada reduzida só acontece com clima ruim no Exterior ou com um evento plantado que a explique (E05, E16). E todo dia de clima ruim no Exterior tem jornada reduzida.
- **E08:** o modelo `Gasto` não guarda quantidade nem valor unitário (só `item`, `categoria` e `valor`), então o evento não tem preço acima do normal, e a pergunta "quanto pagamos a mais no cimento de emergência?" fica fora. O `Gasto` não será alterado agora; a opção está registrada no roadmap do `docs/experimentos.md`. Em troca, entrou uma pergunta de soma por item ("quanto já foi de cimento na casa?"), que não depende do evento.
- **E15:** sem gasto de EPI, porque o catálogo não tem esse item e ficou decidido não alterar o catálogo.
- **Forma dos textos:** a rotina segue a faixa de 55 a 110 caracteres, com mediana até 15 caracteres distante da dos eventos. O pytest também compara número de frases, presença de dígitos e presença de vírgulas, para que os eventos não sejam identificáveis pela forma.
