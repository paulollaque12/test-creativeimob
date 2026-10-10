# Mapa de consultas do dashboard (função no HTML → fonte → regra → rota no shim)
Todas as consultas rodam via `mcp.watchTool("Google Cloud BigQuery","execute_sql_readonly",{projectId:"vistaprocessos",query})`, cache de 1 h. No espelho, `tools/shim.js` roteia o TEXTO do SQL para uma função JS sobre o cubo. Views: c=`vw_consolidado_clientes_capturados_gralha` (`DATE(Data)`), d=`vw_consolidado_dados_gralha`, h=`vw_consolidado_historico_gralha`, imóveis=`vista_imoveis`+`vista_agencias`+`vista_usuarios` (`IMV` no HTML). Filtros globais (loja/equipe/corretor/veículo) entram por `fw()` como `AND coluna = '...'`.

| Bloco | Função | Regra / fonte | Rota no shim |
|---|---|---|---|
| Overview: big numbers e funil | `sql(r)` | atual vs anterior (CTE `p`); leads c; oportunidade d `EtapaAcaoId IN ('9','5','1')`; fechamento d `('8','4','12')` (ambos `Assunto NOT IN ('Negócio ganho','Negócio perdido')`); visitas h `LOWER(Assunto)='visita'`; proposta h `Assunto='Proposta'`; vendas d `Assunto IN ('Negócio ganho','Negocio Ganho via API')` DISTINCT CodigoNegocio; VGV = soma do MAX(valornegocio_dn) por negócio; agenciamentos/placas = IMV | `qFunil` |
| Overview: Evolução | `sqlE` | por dia/semana (segunda)/mês, 8 métricas | `qEvo` |
| Overview: Veículos·Vendas | `sqlV`, `sqlC` | negócios ganhos por veículo/bairro/tipologia/dorm.; % corretores com venda; corretores por cliente | `qVeic`, `qCorV` |
| Overview: Desempenho por dimensão | `sqlD` | funil por dimensão (DENSE_RANK) | `qDim` |
| Comparativo | `sqlCmp` (reusa `sql`) | dois períodos, filtros por funil | `qFunil` |
| Ranking | `sqlR`, `sqlQ` | % corretores com venda por equipe/mês (GROUPING SETS); conversão por corretor | `qRank`, `qConv` |
| Lojas | `sqlLJ`, `sqlT` | funil por loja; resultados (equipe/loja/corretor) | `qLojas`, `qRes` |
| Produto | `sqlPd1`, `sqlPd2` | cadastrados (`DATE(data_cadastro)`), placa (`LOWER(tem_placa)='sim'`), vendidos (CodigoEmImovel dos negócios ganhos, data da venda), por loja/equipe/corretor do captador, bairro e célula 0,004° | `qProd1` (`'vend_pl'`), `qProd2` (`'bai' k,bairro a`) |
| Daily | `sqlL`, `sqlY` | último dia da base L; d1=L, d2=L-1, mês atual 1..L, mês anterior mesmo nº de dias; GROUPING SETS (equipe,corretor) | `qUlt`, `qDaily` |
| Insights | `sqlIn(w)` | prefixo `/*ins*/`; 3 consultas (dia, semana, mês), período × métrica × dimensão via UNNEST; vendas com MAX por negócio (VGV em `v`) | `qIns` |
| Filtros | `loadOpts` | opções de loja/equipe/corretor/veículo | `qOpts` |

Janelas do Insights (`inWin(L)`): dia L vs L-1; semana segunda..L vs mesmos dias da semana anterior; mês dia 1..L vs mesmo nº de dias do mês anterior. Motor de regras: `inGen`/`inPick` (pesos `INM`, limiares `mt/md/mz/md2/pp`); Wins = candidatos `up`, Lows = `dn`, até 3 de cada.
Armadilhas SQL: `Data` TIMESTAMP na view c; GROUPING SETS com COALESCE só em subconsulta; `latitude/longitude` BIGNUMERIC → SAFE_CAST FLOAT64; `get_query_results` precisa de `location`; resultados grandes são salvos em arquivo.
