# Rotina diária do dashboard Gralha (espelho público)

Site publicado: GitHub Pages, pasta `docs/` da branch `main`.
Dados: `docs/data.enc.json` (cubo criptografado AES-GCM; a senha NUNCA fica no repositório, vem da variável `DASH_SENHA`).
Página: `docs/index.html` = `fonte/dashboard-gralha-funil.html` (o dashboard ao vivo) + `tools/shim.js` (responde as consultas a partir do cubo). Ela e a versão ao vivo são o mesmo código.

## Passo a passo (feito pelo Claude agendado, 07:00 America/Sao_Paulo)
1. `git pull` e instalar dependência: `pip install --break-system-packages cryptography`.
2. `python tools/atualizar.py sql` -> grava `/tmp/atu/q_m0..q_m11.sql`, `q_k.sql`, `q_ultimo.sql`.
   (janela padrão = dia 1 do mês anterior até hoje; reprocessa o período recente para pegar correções do CRM.)
3. Rodar CADA arquivo com `execute_sql_readonly` (projectId `vistaprocessos`, `timeoutMs` 120000), colando o texto da consulta sem alterar.
   Todas as consultas têm uma linha de enchimento, então o conector SEMPRE salva o resultado num arquivo e devolve o caminho (erro "exceeds maximum allowed tokens ... saved to <caminho>" é o esperado). Anotar o caminho de cada uma.
   Rodar `q_ultimo.sql` também (resultado pequeno, inline): é a data do último dia da base (`ULTIMO`).
4. `DASH_SENHA=<senha> python tools/atualizar.py montar --desde <DESDE> --ultimo <ULTIMO> --k <arquivo q_k> <arq q_m0> ... <arq q_m11>`
   (DESDE = a data impressa no passo 2). Deve imprimir contagens para as 8 métricas (0..7); se faltar alguma, parar sem publicar.
5. `python tools/build_estatico.py fonte/dashboard-gralha-funil.html --site docs/index.html --enc docs/data.enc.json`
6. Conferir: `ultimo` do cubo = `ULTIMO`, número de linhas próximo ao anterior (não pode cair mais que ~2%).
7. `git add docs && git commit -m "dados ate <ULTIMO>" && git push origin main`.
   Se o push falhar, não insistir em loop: relatar o erro.

## Quando mudar o dashboard
Edite `fonte/dashboard-gralha-funil.html` (cópia do HTML ao vivo) e rode o passo 5. Se mudar alguma consulta SQL do HTML, atualize também `tools/shim.js` (roteador das consultas) e `tools/gerar_dados.py` (definição das métricas do cubo).

## Métricas do cubo (m)
0 leads (capturados, DATE(Data)); 1 oportunidade (EtapaAcaoId 9/5/1, Assunto fora de Negócio ganho/perdido); 2 visita (histórico, LOWER(Assunto)='visita' E Statusvisita='Finalizado'); 3 proposta (histórico, LOWER(Assunto)='proposta'; n=1 por cliente+dia); 4 fechamento (EtapaAcaoId 8/4/12 + mesmo filtro); 5 vendas (Assunto Negócio ganho / Negocio Ganho via API, entidade = CodigoNegocio, v = valornegocio_dn); 6 qualquer evento em dados (corretores ativos); 7 qualquer evento no histórico.
