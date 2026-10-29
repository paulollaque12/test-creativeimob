---
name: "gralha-dashboard-migracao"
description: "Contexto completo e método do projeto de migração do dashboard da Gralha Imóveis do Power BI para um HTML alimentado pelo BigQuery, feito pela equipe de Data & BI da CreativeImob. Use SEMPRE que o assunto envolver Gralha, Vista CRM, vw_consolidado_dados_gralha, nitro_dados, funil de vendas imobiliário (Captação, Oportunidade, Visita, Proposta, Fechamento, Vendas), agenciamentos, placas, imóveis vendidos, aba Produto, aba Insights, mapa por bairro, equipes comerciais da Gralha, migração Power BI para HTML, medidas DAX, dashboards imobiliários da CreativeImob, o espelho público no GitHub Pages ou a rotina diária de atualização, ou quando o usuário pedir para criar, ajustar, validar ou explicar qualquer indicador ou gráfico desse painel, mesmo sem citar a skill."
---

# Migração do dashboard da Gralha (Power BI para HTML + BigQuery)

## Quem é quem
- **CreativeImob** (grafia correta, sem "Mob" separado): assessoria de growth marketing para o mercado imobiliário, sede na Vila Leopoldina (SP). Seis unidades: Performance, Social & Branding, Design, Audiovisual, **Data & BI**, Tech. O usuário desta skill é da **equipe de dados** (Data & BI) (Paulo, paulo@creativeimob.com).
- **Gralha Imóveis**: cliente. Imobiliária de alto padrão em Florianópolis (venda e locação). Detalhes em `references/negocio-gralha.md`.
- **Vista CRM** (Vista Software): CRM onde os corretores cadastram leads, veem a etapa do funil e registram atividades. É a origem dos dados.
- **Projeto**: dashboard HTML que consulta o BigQuery da Gralha, com os indicadores do Power BI e mais clareza executiva.

## Estado atual (out/2026) — ler primeiro
- **Versão final ao vivo** (artefato Claude, consulta o BigQuery a cada abertura via `claude.use("mcp")` + `watchTool`): https://claude.ai/artifact/8bfHMow3YsAM91dieAhULi (v50 em 15/10/2026; republicar sempre copiando `fonte/` para `/mnt/user-data/outputs/dashboard-gralha-funil.html` ANTES de publicar e mudando o `label`). Fonte de verdade do código: `fonte/dashboard-gralha-funil.html` do repositório (e o artefato). O `assets/dashboard-funil-final.html` desta skill está DEFASADO (só funil + Evolução); não usar como base.
- **8 abas** (ordem final de 15/10/2026): **Insights (BETA)**, **Overview (SEMPRE a página inicial)**, Comparativo (dois períodos, filtros próprios por funil), Daily (dia fechado d-1 vs dia anterior, mês atual vs mês anterior, por equipe com expansão por corretor, 8 métricas), Ranking (% corretores com vendas por equipe/mês com datas padrão 01/01/2026 a D-1; evolução; conversão por corretor), **Produto** (imóveis), Lojas (funil por loja e Resultados Equipes/Loja/Corretor), **Equipes** (nova: UMA aba com filtro de Loja que substitui as 5 abas por loja do Power BI; ver abaixo). Filtros globais: Loja, Equipe, Corretor, Veículo de captação (veículo oculto na aba Produto). Na aba Insights o seletor de datas e os filtros globais ficam ocultos (janelas fixas).
- **Aba Equipes** (`#panel-eq`): seletor Loja ("Todas as lojas" + `OPTS.loja`, nomes "Gralha X") + datas (padrão mês até D-1); ao trocar a loja a aba inteira recarrega: funil por equipe (cards, `sqlLJ(a,b,"nome_equipe_usuario",loja)`, `renderEQ`/`loadEQ`) e UMA tabela "Resultados · Equipes e corretores" com botão **+/−** que abre os corretores de cada equipe com as mesmas métricas (`sqlT(...,loja)` com dim `eqco` = equipe¦corretor; `LRC.eqe`/`LRC.eqc`, `renderT` expansível, `EQX`). No shim: `qEquipes` e filtro de loja em `qRes` (incl. composto `eqco`). A aba Lojas mantém Resultados Equipes/Loja/Corretor. Filtros globais ocultos nas abas cmp/rk/lj/eq.
- **Tema claro/escuro**: botão lua/sol (`#thm`) no canto do cabeçalho; padrão SEMPRE claro (ignora o tema do navegador); escolha guardada em localStorage `gralha-tema` (try/catch); escuro só via `:root[data-theme="dark"]`. Aplicado no gerencial, nos 15 dashboards de equipe (repo gralha-equipes) e no lab.
- **Celular**: bloco CSS "celular: nada pode passar da largura da tela" no fim do `<style>` (inputs date `min-width:0;width:100%`); auditar com Playwright `is_mobile` em 360/390 px.
- **Padrões de UI finais**: cada bloco tem uma frase introdutória curta e cinza (`.bi`) sobre o que é/representa (sem repetir datas); o Overview NÃO mostra a linha "período · anterior · atualizado em" nem texto de resumo; todas as tabelas ordenam ao clicar no nome da coluna (1º clique maior→menor nas numéricas, A–Z nas de texto; 2º inverte; seta ↓/↑). Tabelas com ordenação própria: Desempenho por dimensão, Ranking, Conversão por corretor, Resultados; Desempenho por dimensão tem colunas de métricas de largura igual (fixa, 112 px; `table.dt`, variável `--n`) com cabeçalho, valores e total centralizados (nomes à esquerda). As demais usam o ordenador genérico de DOM (`SEL`, no fim do script; no Daily ordena equipes e corretores dentro de cada equipe).
- **vs. anterior (regra)**: Overview/Produto comparam com os N dias imediatamente antes do período selecionado (variação = (atual−anterior)/anterior; anterior 0 ou antes de 01/01/2026 = "sem base"). Daily e Insights: dia vs dia anterior; semana (segunda..L) vs mesmos dias da semana anterior; mês (dia 1..L) vs mesmo nº de dias do mês anterior. Inconsistência conhecida e ACEITA pelo usuário ("deixa como tá"): com as datas padrão o Overview compara 01–08/10 com 23–30/09, enquanto Insights/Daily comparam com 01–08/09. Não mudar sem pedido.
- **Espelho público estático** (GitHub Pages, protegido por senha): https://gralha.creativeimob.app (domínio próprio; o link antigo github.io redireciona) — repo `paulollaque12/test-creativeimob`, branch main, Pages em `/docs`. É o MESMO HTML do ao vivo + `tools/shim.js` que responde às consultas SQL a partir de um cubo criptografado (`docs/data.enc.json`, AES-GCM, PBKDF2-SHA256 250k, zlib). A senha NUNCA vai para o repositório nem para arquivos; o usuário a conhece.
- **Repositório completo** (versão final em 09/10/2026; inclui `QUERIES.md` = mapa de consultas e `skill/SKILL.md` = cópia desta skill): `CONTEXTO.md` (resumo do projeto, regras, cubo, armadilhas), `ATUALIZAR.md` (passo a passo da rotina), `fonte/`, `docs/`, `tools/` (`gerar_dados.py`, `atualizar.py`, `build_estatico.py`, `shim.js`, `build_geo.py`, `geo_osm.sql`, `pdgeo.json`, `requirements.txt`).
- **Rotina diária**: tarefa agendada (06:52 America/Sao_Paulo, trigger `trig_011wxEjYY2FU3mknn3ky8mxK`) que clona o repo, segue `ATUALIZAR.md`, atualiza o cubo de forma incremental (reconsulta desde o dia 1 do mês anterior, métricas 0 a 11), recifra, reconstrói `docs/index.html`, commita só `docs/` e dá push. Em qualquer falha, para sem publicar. Os Insights se recalculam sozinhos a cada abertura a partir do último dia da base: a rotina não gera nada para eles. Teste manual da rotina (com as métricas 8 a 11) ainda pendente: disparar após o usuário confirmar que o link do Pages abre.
- A demonstração estática antiga (Netlify/zip) NÃO é mais mantida (decisão do usuário: "o dashboard vf é o que sim"). O sandbox só alcança GitHub e o dataset público do BigQuery (Netlify, Cloudflare, Vercel, CDNs e tiles de mapa não); push exige o app GitHub do Claude instalado na conta do usuário.

## Princípio central
O Power BI atual é a **fonte da verdade**. Nenhum número do HTML vale até bater com o do Power BI para o mesmo filtro e período. Nunca apresente um número como "oficial" sem essa validação, e diga isso ao usuário. Regras já validadas em `references/powerbi-referencia.md` (usar SOMENTE elas; as regras antigas baseadas em `nomeetapa_dn` são obsoletas e nunca devem ser usadas).

## Regras de contagem em vigor (validadas)
Views: `nitro_dados.vw_consolidado_clientes_capturados_gralha` (c), `vw_consolidado_dados_gralha` (d, cards/negócios) e `vw_consolidado_historico_gralha` (h, atividades). Projeto `vistaprocessos`, dataset `nitro_dados`, location `us-east1`. Dados desde 2026-01-01.
- **Leads**: view c, `DATE(Data)` (Data é TIMESTAMP aí), `COUNT(DISTINCT CodigoCliente)`; o total ao lado é `COUNT(*)`.
- **Oportunidade**: view d, `EtapaAcaoId IN ('9','5','1')` e `Assunto NOT IN ('Negócio ganho','Negócio perdido')`, clientes únicos.
- **Fechamento**: view d, `EtapaAcaoId IN ('8','4','12')` com o mesmo filtro de Assunto.
- **Visita**: view h, `LOWER(Assunto)='visita'`. **Proposta**: view h, `LOWER(Assunto)='proposta'` (algumas abas ao vivo ainda usam 'Proposta' estrito; o cubo usa LOWER).
- **Vendas**: view d, `Assunto IN ('Negócio ganho','Negocio Ganho via API')`, `COUNT(DISTINCT CodigoNegocio)`. **VGV** = soma do `MAX(valornegocio_dn)` por negócio.
- **Agenciamentos**: imóveis cadastrados = `COUNT(DISTINCT codigo)` de `nitro_dados.vista_imoveis` com `imobiliaria_id=1`, data = `DATE(data_cadastro)` (NÃO usar `created_at`/`updated_at`: são timestamps de carga). Há 3 datas com erro de digitação (anos 2108/2206): limitar ao período/`<= CURRENT_DATE`. **Placas** = o mesmo, com `LOWER(tem_placa)='sim'` (valores 'Sim'/'Nao').
- **Imóvel vendido** = `CodigoEmImovel` dos negócios ganhos (view d) no período, pela data da venda. A `vista_imoveis` NÃO tem data de venda (o `status` 'Vendido Gralha'/'Vendido Terceiros' não tem data). Todas as 354 vendas de 2026 trazem o código do imóvel e casam com a `vista_imoveis` (338 com status Vendido Gralha, 336 com coordenadas).
- Loja = `vista_agencias.nome` via `codigo_agencia`; equipe = `vista_usuarios.equipe_nome` e corretor = `vista_usuarios.nome` via `codigo_corretor` (joins sempre com `imobiliaria_id=1`). Os nomes batem com os das views do funil. ~11 imóveis ficam sem usuário.
- Imóvel não tem veículo de captação: com o filtro de veículo ativo, Agenciamentos e Placas dariam 0 (na aba Produto o filtro é ignorado e aparece um aviso curto).
- A `vista_imoveis` é carregada com atraso (última carga 06/10/2026, dados até 05/10): o Daily mostra o aviso "sem registros no último dia" e o mês corrente fica parcial.
- Conferência (agenciamentos/placas por mês): jan 370/126, fev 366/119, mar 466/155, abr 413/141, mai 379/143, jun 480/183, jul 427/107, ago 398/98, set 384/97, out (até 05/10) 69/12. Setembro/2026 na aba Produto: cadastrados 384, com placa 97, vendidos 27 (8 com placa); período anterior (02/08 a 31/08): 397 / 98 / 42 / 13.
- Nunca usar `nomeetapa_dn`. Corretores ativos = qualquer evento em d (para %corretores com venda).

## Aba Insights (BETA)
- Primeira aba na barra (ícone ✦ + "Insights" + "BETA" pequeno), mas o Overview é a página inicial; Insights carrega ao clicar. Três colunas (Diário, Semanal, Mensal); em cada uma, dois blocos empilhados: **Wins** (até 3 destaques positivos, ícone verde) e **Lows** (até 3 negativos, ícone vermelho). Foco: visão high level para gerentes (etapas do funil, lojas/equipes/corretores, VGV, agenciamentos, placas).
- Insights **por regras em JS, recalculados a cada abertura** (não é texto escrito à mão). Referência = último dia fechado da base (L, mesma `sqlL` do Daily). `inWin(L)`: dia L vs L-1; semana segunda..L vs mesmos dias da semana anterior; mês dia 1..L vs mesmo nº de dias do mês anterior.
- Consulta `sqlIn(w)` (começa com `/*ins*/`), uma por quadrante: período (atual/anterior) × métrica (leads, oportunidade, visitas, proposta, fechamento, vendas+VGV, agenciamentos, placas) × dimensão (loja/equipe/corretor/tot) via UNNEST de STRUCT; vendas usa MAX por negócio (VGV em `v`). Espelho: `qIns` em `shim.js` (rota `startsWith("/*ins*/")`). Validado no BigQuery (1–5/10 vs 1–5/9: leads 147/193, visitas 68/135, vendas 4/6, VGV 3,22/5,705 Mi).
- Motor: `inGen(k,X,lo)` gera candidatos (variação do total |Δ|≥2/3/5 por quadrante ou ≥40%, VGV, equipe/loja que mais moveu cada métrica, corretor líder em vendas/proposta/visita, conversão entre etapas só semanal/mensal com Δ≥2 p.p., equipe/loja que zerou); score = peso da métrica (`INM`: vendas 5 … placas 1,6) × magnitude; `inPick(k,X,'up'|'dn')` escolhe 3 por bloco (máx. 2 por métrica e 2 por tipo; se faltar, relaxa os limites e usa `inGen(...,true)`). Limiares em `mt`, `md`, `mz`, `md2`, `pp`.
- Evolução possível (não feita): narrativa por LLM gerada na rotina diária e gravada em arquivo.

## Aba Produto (imóveis)
- Topo: usa o seletor de datas do cabeçalho (o mesmo do Overview; mudar a data ou clicar Atualizar recarrega a aba) e os filtros globais Loja/Equipe/Corretor (do CAPTADOR do imóvel, tanto nos cadastrados quanto nos vendidos).
- 6 tiles em fila: Agenciamentos, Com placa, Imóveis vendidos (com "vs. anterior"), Cadastrados / Vendidos, Com placa / Vendidos, Sem placa / Vendidos (razões numéricas, ex.: set/2026 14,22 / 3,59 / 10,63).
- Painel "Placa: cadastrados e vendidos": duas barras 100% (com placa x sem placa). A placa é a situação ATUAL do imóvel, não a da data da venda (dizer isso).
- "Análise por captador": seletor Loja/Equipe/Corretor; colunas cadastrados (com barrinha), com placa, % com placa, vendidos, cad./vend., total no rodapé.
- "Onde estão os imóveis": mapa por bairro com camadas Cadastrados, Com placa, Sem placa, Vendidos; zoom (+/−) e arrastar; hover com nome do bairro, cidade e quantidade; top 10 bairros ao lado (segue os polígonos do mapa).
- **Mapa (decisão importante)**: tiles externos de rua (OSM/CARTO) não carregam no ambiente do artefato; o usuário pediu "pelo menos regiões, bairros, formato da cidade". Solução: SVG próprio com polígonos de municípios (OSM admin_level 8) e bairros (admin_level 10) da Grande Florianópolis, embutidos em `const PDG` (≈54 KB, deltas inteiros em 1e-4 grau; 12 municípios e 201 bairros; Florianópolis 50, Palhoça 33, São José 27 etc.), gerados por `tools/geo_osm.sql` (dataset público `bigquery-public-data.geo_openstreetmap.planet_features`, location US) + `tools/build_geo.py`. O SQL do dashboard devolve células de 0,004° (~400 m) `FLOOR(lat/0.004)|FLOOR(lon/0.004)` dentro da caixa lat -28.3..-27.2 e lon -49.3..-48.2; o JS atribui cada célula ao bairro por ponto-em-polígono (polígonos ordenados por área crescente) e pinta o bairro pela soma. Enquadramento por quantis 0,4%/99,6% das células de fundo (`bg` = todos os cadastrados desde 01/01/2026). Atribuição "Limites: © OpenStreetMap" no canto (ODbL). Em set/2026, 305 dos 384 cadastrados caem em bairros mapeados (OSM cobre só parte dos bairros; alternativa: malha de bairros do IBGE, se o usuário quiser mais cobertura).
- Consultas da aba: `sqlPd1` (KPIs atual/anterior: cad, pl, vend, vend_pl) e `sqlPd2` (análise por loja/equipe/corretor, tot, bai, cell, bg numa só consulta, colunas k,a,b,n1..n6). No shim: `qProd1` (route por `'vend_pl'`) e `qProd2` (route por `'bai' k,bairro a`).

## Como trabalhar (fluxo por indicador)
1. Identifique o indicador e a pergunta de negócio (se o usuário não disse, pergunte; não invente).
2. Recupere a regra original (DAX ou descrição). Sem ela, marque "regra não confirmada".
3. Escreva o SQL (ver `references/bigquery.md`) e rode com `execute_sql_readonly` (sempre `projectId: vistaprocessos`; `get_query_results` precisa de `location: us-east1`, ou `US` para o dataset público do OSM).
4. Compare com o Power BI (mesmo período e filtros). Registre a diferença.
5. Só então construa/ajuste o visual (ver `references/dashboard-html.md`).
6. Ao mexer em métrica nova ou visual, atualizar TAMBÉM o espelho (ver abaixo), publicar o artefato e dar push.

### Ficha de indicador
```
Indicador:            (nome como aparece no Power BI)
Pergunta de negócio:  (o que o gestor decide com isso)
Regra original/DAX:   (colar; "não confirmada" se faltar)
SQL equivalente:      (query)
Validação:            Power BI = X | HTML = Y | status
Gráfico e por quê:    (tipo de visual e motivo da escolha)
```

## Regras-chave do GuideLine (detalhe em `references/etapas-funil.md`)
- Dois funis: Pipeline (movimentação dos cards) e Atividades (Visita e Proposta contam atividades dentro do card).
- **Clientes únicos** contam o cliente uma vez; **movimentações** contam cada card, na data em que aconteceu.
- O dashboard **não bate com a tela do Vista, por desenho** (o Vista mostra só a última etapa). Validar contra o Power BI.
- **Captação** = leads cadastrados. **Vendas** = "Negócio Ganho" datado pela atividade de ganho; VGV = valor do negócio.
- Prints do guia em `assets/guia-gralha/`. Metas fora do dashboard (decisão do usuário). VGV por negócio, com aviso da diferença para o Power BI.
- Três processos de origem: A Captação, B Oportunidade/Visita/Proposta/Fechamento (cards), C Vendas (status, não etapa).

## Preferências de design e produto (do usuário)
- Paleta vinho (#6e1428/#8a1f33) e navy (#2f3f80), logo da Gralha, UI elegante, limpa, objetiva e analítica ("não tão cansativa"), modo claro/escuro (padrão claro, botão lua/sol).
- Big numbers: 6 em uma única fila no desktop (VGV, Vendas, Leads captados, Conv. lead para venda, Agenciamentos, Placas), textos centralizados, chip de variação "vs. anterior" (3 colunas até 1000px, 2 no celular). O nome do card de conversão é "Conv. lead para venda". A aba Produto usa o mesmo padrão de 6 tiles.
- Evolução: gráfico com a mesma altura da coluna de métricas (flex), métricas = Captação, Oportunidade, Visita, Proposta, Fechamento, Vendas, Agenciamentos, Placas; eixo Dia/Semana/Mês (legenda "imóveis" nas duas últimas).
- Daily: seletores das mesmas 8 métricas; ícone de variação no mesmo nível do número de %.
- Comparativo: filtros por funil (cada período com os seus).
- **Datas padrão**: do dia 1 do mês até ontem (D-1); no dia 1, o mês anterior inteiro. Comparativo: período 1 = mês anterior no mesmo número de dias. Datas ficam no cabeçalho; abas não devem repetir explicações longas sobre datas.
- Otimização de tokens/refresh: cache de 1h nas consultas, uma consulta por bloco.

## Arquitetura do espelho estático (repo test-creativeimob)
- `fonte/dashboard-gralha-funil.html` (cópia do ao vivo; copiar do arquivo publicado antes de reconstruir), `tools/build_estatico.py` (`--site docs/index.html --enc docs/data.enc.json`: injeta loader de senha + `shim.js`), `tools/shim.js` (roteia o texto SQL de cada consulta do dashboard para uma função JS sobre o cubo), `tools/gerar_dados.py` (definição das métricas `METR` e SQL do cubo), `tools/atualizar.py` (`sql`, `montar`), `ATUALIZAR.md`, `docs/` (publicado: index.html, data.enc.json, robots.txt, .nojekyll).
- **Cubo**: linhas `[m,dia,cl,loja,equipe,corretor,veiculo,bairro,tipo,cond,lanc,cod,dorm,area,nome,cc,kc,valor,n]`, dia = dias desde 2020-01-01. Métricas: m0 leads, m1 oportunidade, m2 visita, m3 proposta, m4 fechamento, m5 vendas (cl=CodigoNegocio, kc=CodigoCliente, valor=valornegocio_dn), m6 qualquer evento de d (corretores ativos; só loja/equipe/corretor/veículo), m7 qualquer evento de h (só loja/equipe/corretor; n=1), **m8 agenciamentos**, **m9 placas**, **m10 imóveis vendidos** (um registro por imóvel e dia da venda) e **m11 vendidos com placa**. Para m8 a m11: cl = código do imóvel; dims só loja/equipe/corretor do captador, `bairro` (índice 7) e `area` (índice 13) = célula do mapa "i|j"; cc=-1 (não conta como corretor ativo). `K` mapeia cliente → corretores (clientes com venda). O cubo tem ~92 mil linhas (1,1 MB cifrado).
- **Shim**: qFunil (KPIs do Overview, incluindo agenciamentos/placas), qEvo, qDaily (usa `MK` com as 8 métricas), qRes ignora m>7, qProd1/qProd2 para a aba Produto, **qIns** para a aba Insights.
- **Ao criar métrica nova**: (1) definir em `METR` e no SQL do dashboard; (2) rotear/agregar no `shim.js` (cuidar para não vazar nas consultas que somam por corretor); (3) `atualizar.py` (`range(N)` e assert de métricas); (4) backfill: `DASH_SENHA=... python tools/atualizar.py montar --desde 2026-01-01 --ultimo AAAA-MM-DD --metricas 8,9,10,11 <arquivos q_m8..q_m11>` (a opção `--metricas` reconstrói só essas); (5) rebuild do site e teste no navegador (servir `docs/` por `python3 -m http.server`; `file://` bloqueia o fetch; bloquear fontes do Google nos testes) comparando com o BigQuery; (6) commit/push só com `docs/`+código, mensagem com os Co-Authored-By exigidos.
- **Atualização incremental**: uma consulta por métrica (`q_m0..q_m11.sql`, gerados por `atualizar.py sql`) com linha de enchimento (`m=-1`, `REPEAT('x',400000)`) para o conector SEMPRE salvar o resultado em arquivo (resultado pequeno volta inline e gasta contexto); resultados grandes demais para uma mensagem fecham a conexão MCP, por isso uma consulta por métrica.

## Armadilhas conhecidas
- `Data` é TIMESTAMP na view c: usar `DATE(Data)`. Nas views d/h, `Data` é DATE.
- GROUPING SETS não aceita COALESCE direto: fazer em subconsulta.
- Nomes de CSS/JS únicos no HTML (já existem `unL`, `sqlL`, `nz`, `dv`, `pc1`, `esc2`, `rt`, `PDW`, `PDK`, `INK`, `INM`, `inGen`, `inPick`...): prefixar novos nomes (ex.: `IM`/`im`, `pd`, `in`).
- Publicar o artefato exige ler a versão atual antes; re-publicar idêntico é recusado (mudar o comentário de versão `<!-- vAAAA-MM-DDx ... -->`).
- `get_query_results` do BigQuery precisa de `location` (us-east1 para `nitro_dados`; US para datasets públicos). `ST_ASGEOJSON` não aceita o argumento de precisão. `ST_SIMPLIFY` pode devolver GeometryCollection (com linhas): extrair só Polygon/MultiPolygon.
- **Rotinas e conector**: as rotinas diárias (06:52 gerencial `trig_011wxEjYY2FU3mknn3ky8mxK`; 07:21 equipes `trig_012HghkenQotDzXkrNv5SooB`) aparecem como SUCCEEDED mesmo quando o conector do BigQuery caiu (incidente 10–13/10/2026: nada publicado). Sintoma: falta commit "dados ate AAAA-MM-DD" do dia; conferir a mensagem do último commit. O conector usa conta Google própria com bigquery.jobUser, bigquery.dataViewer e mcp.toolUser em `vistaprocessos`; se reconectar, disparar as duas rotinas com fire_trigger (gerencial primeiro). A rotina gerencial reconstrói `docs/index.html` a partir de `fonte/` do repo: toda mudança do dashboard precisa estar commitada em `fonte/` + `tools/shim.js` para sobreviver.
- **Publicar o artefato**: o `cp` de `fonte/` para `/mnt/user-data/outputs/` deve rodar em comando separado do `pkill`/servidor (um exit 144 mata o resto do comando e publica a versão antiga sem aviso). Conferir com `grep -c` de um id novo no arquivo copiado.
- A CLI `bq` quebra neste sandbox (bug interno): usar o conector `execute_sql_readonly`. Para testar o espelho no navegador: servir `docs/` com `python3 -m http.server` em `setsid nohup` (o servidor cai entre chamadas), bloquear fontes do Google e, sem a senha, trocar `window.__cuboLoader` para ler o cubo em claro. `pkill -f "http.server"` no mesmo Bash do git derruba o shell (exit 144): rodar separado.
- Tabelas de imóveis: `vista_imoveis` (`codigo` único, `status`, `tem_placa`, `latitude`/`longitude` BIGNUMERIC (usar SAFE_CAST para FLOAT64), `bairro`, `cidade`, `codigo_agencia` 1=Pedra Branca, 3=Trindade, 5=Centro, 11=Campeche, 12=Jurerê, `codigo_corretor`, `data_cadastro`), `vista_agencias`, `vista_usuarios`, `vista_equipes`, `vista_corretores`, `vista_imovel_corretores`. 43,7 mil dos 43,9 mil imóveis da Gralha têm coordenada.
- Resultados do MCP muito grandes são salvos em arquivo (caminho no erro); processá-los com Python/jq, nunca colar no contexto.

## Regras que valem sempre
- **Idioma**: português do Brasil; se o usuário escrever em espanhol ou misturar, responder no idioma predominante.
- **Dados pessoais (LGPD)**: as views têm nome e telefone de clientes. Em resumos e dashboards públicos usar só agregados; nunca repetir telefones. Decisão LGPD do usuário (10/10/2026): a lista "Corretores por cliente com venda" mostra SÓ o código do cliente (cabeçalho "Código do cliente"); o nome saiu da consulta (`sqlC`) e do shim. Ainda existe a dimensão "Nome Cliente" em Desempenho por dimensão (nomes vêm de `nomecliente_dn` e estão no cubo cifrado): só mexer se o usuário pedir.
- **Honestidade sobre incertezas**: separar o verificado no BigQuery do suposto (ex.: o mapa de rua não pôde ser testado com tiles reais no sandbox).
- **Agendamento**: existe tarefa agendada do Claude (ver Rotina diária); usar as ferramentas de tarefas agendadas, nunca cron local.
- **Acesso**: o conector do BigQuery exige `mcp.tools.call` no projeto. Ver erros em `references/bigquery.md`.
- Nunca escrever a senha do espelho em arquivo, commit, mensagem ou prompt salvo além do que o usuário já configurou na tarefa agendada.

## Pendências
- Antes de enviar ao cliente (Gralha): conferir divergência de VGV de setembro (novo 31,22 Mi x PDF antigo 29,72 Mi); PDF de venda da evolução em `/mnt/user-data/outputs/Gralha_Evolucao_Dashboard.pdf` (6 páginas, tom executivo, termina em "Obrigado").
- Lab (repo gralha-lab, crIAtive com Worker Cloudflare `gralha-ask`): o Secret `ACESSO` precisa ser igual ao `askToken` do cubo do lab, senão a IA cai nas regras ("acesso negado"). NÃO levar a IA ao gerencial sem confirmação dos sócios.
- Print "34 Agenciamentos / 9 Placas": o usuário disse "deixa" (não reproduzido; outubro até 05/10 = 69/12). Não insistir.
- Disparar teste da rotina diária (métricas 0 a 11) após o usuário confirmar que o link do Pages abre; confirmar que o conector do BigQuery está disponível em execuções agendadas.
- Insights: ajustar limiares/pesos conforme feedback dos gerentes; avaliar narrativa por LLM na rotina diária.
- Mapa: cobertura de bairros do OSM é parcial (~20% dos cadastrados ficam fora); avaliar malha de bairros do IBGE se o usuário quiser mais cobertura.
- Ranking: DAX de "corretores ativos"; dimensão "Nome Cliente" (LGPD, ver regras); caixa de linguagem natural para colegas (limites de uso por dia ainda por definir).
- Reconciliar o `assets/dashboard-funil-final.html` com a versão atual (ou removê-lo) e atualizar `references/dashboard-html.md` e `references/pendencias.md` com este estado.

## Mapa dos arquivos
- Repo: `CONTEXTO.md` (contexto completo), `QUERIES.md` (mapa de consultas por bloco), `ATUALIZAR.md` (rotina), `skill/SKILL.md` (cópia desta skill).
- `references/negocio-gralha.md`: negócio, estrutura comercial, Vista CRM, glossário.
- `references/bigquery.md`: projeto, tabelas, colunas, queries prontas, armadilhas (sem as queries de imóveis: ver esta SKILL.md e o `CONTEXTO.md` do repo).
- `references/etapas-funil.md`: definição das 6 etapas, com os números do print.
- `references/powerbi-referencia.md`: dashboard Power BI atual, valores do print e DAX; regras validadas.
- `references/dashboard-html.md`: regras técnicas das páginas, histórico de versões e decisões de design (defasado, ver "Estado atual").
- `references/pendencias.md`: pendências antigas.
- `assets/dashboard-funil-final.html`: versão ANTIGA (funil + Evolução). Para a atual, ver o repo/artefato.
- `assets/logo-gralha.png`, `assets/guia-gralha/`: logo e prints do guia.