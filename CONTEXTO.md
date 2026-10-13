# Dashboard Performance CRM · Gralha Imóveis (CreativeImob · Data & BI)

Migração do dashboard do Power BI para HTML sobre o BigQuery (projeto `vistaprocessos`, dataset `nitro_dados`, location `us-east1`). Dados desde 2026-01-01.
O Power BI é a fonte da verdade; nenhum número vale como oficial sem bater com ele. Idioma: português do Brasil.

## Onde está cada coisa
- **Ao vivo** (artefato Claude; consulta o BigQuery a cada abertura): https://claude.ai/artifact/8bfHMow3YsAM91dieAhULi
- **Espelho público** (GitHub Pages, senha): https://paulollaque12.github.io/test-creativeimob/ (branch main, pasta `/docs`).
  É o MESMO HTML do ao vivo + `tools/shim.js` + cubo criptografado `docs/data.enc.json` (AES-GCM, PBKDF2-SHA256 250k, zlib). **A senha nunca fica no repositório.**
- `fonte/dashboard-gralha-funil.html`: cópia do HTML ao vivo (fonte do espelho). Sempre copiar do artefato publicado antes de reconstruir.
- `tools/`: `gerar_dados.py` (métricas `METR` e SQL do cubo), `atualizar.py` (`sql`, `montar`), `build_estatico.py`, `shim.js`, `build_geo.py` + `geo_osm.sql` + `pdgeo.json` (limites OSM), `requirements.txt`.
- `ATUALIZAR.md`: passo a passo da rotina diária (tarefa agendada 06:52 America/Sao_Paulo, trigger `trig_011wxEjYY2FU3mknn3ky8mxK`).

## Abas (versão final v43, 09/10/2026)
Ordem: **Insights (BETA)**, **Overview (página inicial, sempre)**, Comparativo, Ranking, Lojas, Produto, Daily. Cada bloco tem uma frase introdutória curta e cinza (classe `.bi`) dizendo o que é e o que representa (sem repetir datas). Overview: 6 big numbers (VGV, Vendas, Leads captados, Conv. lead para venda, Agenciamentos, Placas; todos centralizados e em uma fila), jornada do funil, Evolução (gráfico com a mesma altura da coluna de métricas; 8 métricas; eixo Dia/Semana/Mês), Veículos·Vendas, Desempenho por dimensão. A linha de status "período · anterior · atualizado em" foi removida do Overview. Comparativo: dois períodos com filtros por funil. Ranking: % de corretores com vendas (datas padrão 01/01/2026 a D-1), evolução e conversão por corretor. Lojas: funil por loja e Resultados (Equipes/Loja/Corretor). Produto: ver seção. Daily: dia fechado vs dia anterior e mês atual vs mês anterior por equipe/corretor, 8 métricas. Todas as tabelas ordenam ao clicar no nome da coluna (maior para menor primeiro).
**vs. anterior (Overview/Produto)**: período anterior = os N dias imediatamente antes do selecionado (N = nº de dias do período); variação = (atual−anterior)/anterior; anterior 0 ou antes de 01/01/2026 = "sem base". Daily e Insights usam outro recorte (dia vs dia anterior; mês atual vs o mesmo nº de dias do mês anterior). Pendente: o usuário decide se o Overview também passa a comparar com o mesmo recorte do mês anterior.
Datas padrão: dia 1 do mês até D-1 (no dia 1, o mês anterior inteiro). O seletor de datas do topo vale para Overview e Produto.

## Regras de contagem validadas
Views: c=`vw_consolidado_clientes_capturados_gralha` (Data é TIMESTAMP: usar `DATE(Data)`), d=`vw_consolidado_dados_gralha`, h=`vw_consolidado_historico_gralha`. Nunca usar `nomeetapa_dn`.
- Leads: c, clientes únicos (total = COUNT(*)). Oportunidade: d, `EtapaAcaoId IN ('9','5','1')` e `Assunto NOT IN ('Negócio ganho','Negócio perdido')`. Fechamento: d, `('8','4','12')` mesmo filtro. Visita: h, `LOWER(Assunto)='visita'`. Proposta: h, `LOWER(Assunto)='proposta'`.
- Vendas: d, `Assunto IN ('Negócio ganho','Negocio Ganho via API')`, `COUNT(DISTINCT CodigoNegocio)`. VGV = soma do `MAX(valornegocio_dn)` por negócio.
- **Agenciamentos** = imóveis distintos de `vista_imoveis` (`imobiliaria_id=1`) por `DATE(data_cadastro)` (não usar created_at/updated_at; há 3 datas digitadas errado em 2108/2206). **Placas** = o mesmo com `LOWER(tem_placa)='sim'`.
- **Imóvel vendido** = `CodigoEmImovel` dos negócios ganhos (view d) no período, pela data da venda (a `vista_imoveis` não tem data de venda; `status` "Vendido Gralha" não tem data). Todas as 354 vendas de 2026 casam com um imóvel.
- Loja = `vista_agencias.nome` (via `codigo_agencia`); equipe = `vista_usuarios.equipe_nome` e corretor = `vista_usuarios.nome` (via `codigo_corretor`); sempre com `imobiliaria_id=1`. Na aba Produto, loja/equipe/corretor são os do CAPTADOR do imóvel (cadastrados e vendidos). Imóvel não tem veículo de captação (filtro de veículo não vale na aba Produto).
- A `vista_imoveis` é carregada com atraso (última carga 06/10/2026; dados até 05/10).
- Conferência (setembro/2026): cadastrados 384, com placa 97, vendidos 27 (8 com placa); anterior (02/08–31/08): 397 / 98 / 42 / 13. Por mês (cad/placa): jan 370/126, fev 366/119, mar 466/155, abr 413/141, mai 379/143, jun 480/183, jul 427/107, ago 398/98, set 384/97, out até 05/10 69/12.

## Aba Produto
Tiles: Agenciamentos, Com placa, Imóveis vendidos (com vs. anterior), Cadastrados/Vendidos, Com placa/Vendidos, Sem placa/Vendidos. Barras 100% da placa (cadastrados x vendidos; placa é a situação atual do imóvel). Tabela por Loja/Equipe/Corretor (cadastrados, com placa, % placa, vendidos, cad./vend.). Mapa por bairro (camadas: Cadastrados, Com placa, Sem placa, Vendidos) + top bairros.
Mapa: células de 0,004° (~400 m) `FLOOR(lat/0.004)|FLOOR(lon/0.004)` na caixa lat -28.3..-27.2 e lon -49.3..-48.2; polígonos de bairros (OSM admin_level 10) e municípios (nível 8) embutidos em `const PDG` (≈54 KB; gerados por `tools/geo_osm.sql` + `tools/build_geo.py`); cada célula é atribuída ao bairro pela coordenada do centro (point-in-polygon). Tiles externos NÃO funcionam no artefato/sandbox: por isso o mapa é desenhado em SVG. Em setembro 305 dos 384 cadastrados caem em bairros mapeados (OSM cobre só parte dos bairros).

## Cubo do espelho
Linhas `[m,dia,cl,loja,equipe,corretor,veiculo,bairro,tipo,cond,lanc,cod,dorm,area,nome,cc,kc,valor,n]`, dia = dias desde 2020-01-01. m0 leads, m1 oportunidade, m2 visita, m3 proposta, m4 fechamento, m5 vendas, m6 qualquer evento de d (corretores ativos), m7 qualquer evento de h, m8 agenciamentos, m9 placas, m10 imóveis vendidos, m11 vendidos com placa. Para m8–m11: cl = código do imóvel; só loja/equipe/corretor; `bairro` (idx 7); `area` (idx 13) = célula do mapa "i|j"; cc=-1. `K`: cliente → corretores (clientes com venda).
Backfill de métricas novas: `DASH_SENHA=... python tools/atualizar.py montar --desde 2026-01-01 --ultimo AAAA-MM-DD --metricas 8,9,10,11 <arquivos q_m8..q_m11>`.
Ao criar métrica nova: METR → SQL do dashboard → roteamento no `shim.js` → `atualizar.py` (range e assert) → backfill → rebuild → testar no navegador servindo `docs/` por http.server (file:// bloqueia o fetch) comparando com o BigQuery → commit/push.

## Armadilhas
GROUPING SETS não aceita COALESCE direto; nomes JS/CSS únicos (já existem unL, sqlL, nz, dv, pc1, esc2, rt, PDW...); republicar o artefato exige ler a versão antes e mudar o comentário de versão; `get_query_results` precisa de `location`; resultados pequenos do MCP voltam inline (usar linha de enchimento `REPEAT('x',400000)` para salvar em arquivo); resultado grande demais fecha a conexão (uma consulta por métrica); o sandbox só alcança GitHub (e o dataset público do BigQuery); push exige o app GitHub do Claude instalado.

## Decisões e pendências
Metas fora do dashboard; VGV por negócio; demonstração antiga (Netlify) descontinuada. LGPD: a lista "Corretores por cliente com venda" mostra nomes de clientes (decisão pendente, espelho é público com senha). Pendências: print 34 agenciamentos / 9 placas (não reproduzido), teste da rotina diária com as métricas 8–11, DAX de corretores ativos (Ranking), caixa de linguagem natural.

## Aba Insights (BETA) — v39
Primeira aba na ordem (ícone ✦ + "Insights" + BETA pequeno), mas a página inicial é SEMPRE o Overview (pedido do usuário); Insights carrega ao clicar. Cada quadrante tem 2 blocos empilhados: Wins (3 destaques positivos) e Lows (3 negativos) via `inPick(k,X,'up'|'dn')`, com preenchimento frouxo (`inGen(k,X,true)`) se faltar. 3 quadrantes (Diário, Semanal, Mensal) com 3 insights cada, **gerados por regras em JS** a cada abertura (sem texto escrito à mão; nada a atualizar na rotina diária — o cubo/BigQuery já alimentam). Referência = último dia fechado da base (L, mesma `sqlL` do Daily).
- Janelas: dia = L vs L-1; semana = segunda..L vs mesmos dias da semana anterior; mês = dia 1..L vs mesmo nº de dias do mês anterior (`inWin`).
- Consulta `sqlIn(w)` (prefixo `/*ins*/`, 1 por quadrante): por período (atual/anterior) × métrica (leads, oportunidade, visitas, proposta, fechamento, vendas+VGV, agenciamentos, placas) × dimensão (loja/equipe/corretor/tot). Espelho: `qIns` em `tools/shim.js` (rota `startsWith("/*ins*/")`). Validado contra BigQuery (1–5/10 vs 1–5/9: leads 147/193, visitas 68/135, vendas 4/6, VGV 3,22/5,705 Mi).
- Motor `inGen(k,X)`: candidatos = variação do total (|Δ|≥2/3/5 por quadrante ou ≥40%), VGV, equipe/loja que mais moveu cada métrica, corretor líder (vendas/proposta/visita), conversão entre etapas (só semanal/mensal, Δ≥2 p.p., denominadores mínimos), equipe/loja que zerou. Score = peso da métrica (vendas 5 … placas 1,6) × magnitude; seleção top 3 com máx. 2 por métrica e 2 por tipo; preenche com fatos neutros se faltar.
- Ajustes: limiares em `inGen` (`mt`,`md`,`mz`,`md2`,`pp`); pesos em `INM`. Evolução futura: narrativa por LLM na rotina diária (guardar em arquivo) — não implementada.

## Ordenação e Ranking (v43)
- Clique no nome da coluna ordena (1º clique: maior para menor nas colunas numéricas, A–Z nas de texto; 2º clique inverte; seta ↓/↑ no cabeçalho). Tabelas com ordenação própria já existente: Desempenho por dimensão, Ranking, Conversão por corretor, Resultados (Lojas). As demais (Veículos·Vendas, Corretores por cliente, Detalhamento, Produto, Daily) usam o ordenador genérico de DOM no fim do script (`SEL`); no Daily ordena as equipes e, dentro de cada equipe, os corretores.
- Ranking · Equipes: datas padrão = 01/01/2026 (`DESDE`) até D-1 (dinâmico, `dfltRange().b`); as demais abas seguem do dia 1 do mês até D-1.

## Decisões finais do usuário (10/10/2026)
- Overview "vs. anterior": manter como está (N dias imediatamente antes). Print 34/9: deixar. LGPD: a lista "Corretores por cliente com venda" mostra só o código do cliente (nome removido da consulta e do shim; a dimensão "Nome Cliente" do Desempenho por dimensão ainda existe).
- Desempenho por dimensão: colunas de métricas com largura igual (112 px, `table.dt`, `--n`), cabeçalho/valores/total centralizados.

## Layout mobile (10/10/2026) e incidente do conector (13/10/2026)
- Mobile: bloco CSS "celular" no fim do `<style>` (fonte). Corrige página forçada a ~856 px (`.ev` com `1fr`, `.tabs` sem rolagem, `.cmh` em 3 colunas). Abas rolam de lado; Comparativo empilha os dois períodos; tabelas largas rolam dentro do cartão. Auditado a 360 e 390 px (Playwright `is_mobile`), todas as abas sem rolagem lateral. As páginas por equipe e o lab ainda NÃO têm esse CSS.
- Incidente: em 10–13/10 as rotinas (06:52 gerencial, 07:21 equipes) terminaram em ~30 s sem publicar porque o conector do Google Cloud BigQuery caiu. Dados ficaram em 09/10 até a reconexão. Reconectado em 13/10 com outra conta Google (precisa de `bigquery.jobUser`, `bigquery.dataViewer` e `mcp.toolUser` no projeto `vistaprocessos`). Rotinas disparadas manualmente; base em 12/10.
- Sintoma de falha: ausência de commit "dados ate AAAA-MM-DD" no dia. Rotina "concluída" não garante publicação. Ideia pendente: alerta quando a rotina parar.
