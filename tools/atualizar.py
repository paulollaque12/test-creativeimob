#!/usr/bin/env python3
"""Atualizacao INCREMENTAL do cubo do dashboard (rodada diaria).

Fluxo (feito pelo Claude agendado, com o conector do BigQuery):
  1) python tools/atualizar.py sql [--desde AAAA-MM-DD] [--dir /tmp/atu]
        -> grava q_m0..q_m11.sql, q_k.sql, q_ultimo.sql (desde padrao = dia 1 do mes anterior)
  2) rodar cada .sql com mcp execute_sql_readonly (projectId vistaprocessos); resultados grandes o
     conector salva em arquivo (caminho aparece na resposta). Anotar o caminho de cada resultado.
  3) DASH_SENHA=... python tools/atualizar.py montar --desde D --ultimo U --k ARQ_K ARQ_M0 ARQ_M1 ... ARQ_M9
        -> decifra docs/data.enc.json, troca as linhas com dia >= desde pelas novas, mescla K, recifra.
  4) python tools/build_estatico.py fonte/dashboard-gralha-funil.html --site docs/index.html --enc docs/data.enc.json
"""
import argparse, datetime, json, os, sys, zlib, base64, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gerar_dados as g

D0 = datetime.date(2020, 1, 1)
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENC = os.path.join(RAIZ, "docs", "data.enc.json")

# linha de enchimento (m=-1) para o conector SEMPRE salvar o resultado em arquivo (resultados pequenos voltam inline e gastam contexto)
PAD_M = "UNION ALL SELECT -1 m, 'pad' mes, REPEAT('x', 400000) s"
PAD_K = "UNION ALL SELECT 'pad' cli, [REPEAT('x', 400000)] cors"

def desde_padrao(hoje=None):
    h = hoje or datetime.date.today()
    p = h.replace(day=1) - datetime.timedelta(days=1)
    return p.replace(day=1).isoformat()

def sql_m(desde, m):
    v = {c: (v, w, e) for c, v, w, e in g.METR}[m]
    sel = g.sel(m, v[0], v[1], v[2], desde)
    f = lambda c: f"IFNULL({c},'')"
    row = " , '\\x1f', ".join(["CAST(dt AS STRING)", f("cl")] + g.DIMS + [f("cc"), f("kc"), "IFNULL(CAST(v AS STRING),'')", "CAST(n AS STRING)"])
    return (f"SELECT * FROM (WITH c AS ({sel}) SELECT m, FORMAT_DATE('%Y-%m', dt) mes, "
            f"STRING_AGG(CONCAT({row}), '\\x1e') s FROM c GROUP BY m, mes) " + PAD_M)

def sql_k(desde):
    return "SELECT * FROM (" + g.sql_k(desde) + ") " + PAD_K

# PipeImob (contratos de compra e venda): mesma consulta da aba ao vivo, gravada em d["pipe"]
SQL_PIPE = ("SELECT * FROM ("
    "SELECT CAST(p.data_contrato AS STRING) ccv,CAST(p.data_inicio_venda AS STRING) env,CAST(p.valor_contrato AS FLOAT64) vgv,CAST(p.total_comissao AS FLOAT64) vgc,IF(EXISTS(SELECT 1 FROM `nitro_dados.pipeimob_negocio_comissionados` m WHERE m.imobiliaria_id=1 AND m.transacao_unique_id_pipeimob=p.transacao_unique_id_pipeimob AND m.comissionado_tipo_participacao LIKE '%Gestor de Produto%') OR EXISTS(SELECT 1 FROM `nitro_dados.pipeimob_negocio_forma_pagamento` f WHERE f.imobiliaria_id=1 AND f.transacao_unique_id_pipeimob=p.transacao_unique_id_pipeimob AND f.forma_pagamento_nome IN ('Mensal','Anual','Chaves')),1,0) lanc,IFNULL(p.etapa_atual,'') etapa,IFNULL(p.agente_gestor,'') gestor,IFNULL(p.codigo_imovel,'') imovel,IFNULL(CAST(p.data_titulo_definitivo AS STRING),'') tit,IFNULL(CAST(p.data_entrega_chaves_posse AS STRING),'') cha,IFNULL(CAST(p.data_pagamento_comissao AS STRING),'') cpg,IFNULL(CAST(p.data_pagamento_comissao_prevista AS STRING),'') cpv,IFNULL(CAST(p.data_registro_publico AS STRING),'') reg,IFNULL(p.comissao_quem_paga,'') quem,IFNULL(p.comissao_momento_pagamento,'') mom,IFNULL(p.midia_origem_compradores,'') mc,IFNULL(p.midia_origem_vendedores,'') mv,IF(p.financiamento,1,0) fin,IFNULL(p.financiamento_banco,'') banco,IFNULL(p.categoria_crm,'') cat,IFNULL(p.endereco_bairro,'') bai,IFNULL(p.endereco_cidade,'') cid,IFNULL(p.diasemestoque,-1) est,IFNULL(CAST(DATE(p.ingested_at) AS STRING),'') ing,IFNULL((SELECT STRING_AGG(CONCAT(IFNULL(x.comissionado_tipo_participacao,'?'),'~',CAST(ROUND(IFNULL(CAST(x.comissionado_valor AS FLOAT64),0)) AS STRING)),'|') FROM `nitro_dados.pipeimob_negocio_comissionados` x WHERE x.imobiliaria_id=1 AND x.transacao_unique_id_pipeimob=p.transacao_unique_id_pipeimob),'') pap,IFNULL((SELECT MIN(gg.grupo_id) FROM `nitro_dados.pipeimob_negocio_gestor_grupos` gg WHERE gg.imobiliaria_id=1 AND gg.transacao_unique_id_pipeimob=p.transacao_unique_id_pipeimob AND gg.grupo_id LIKE 'EQUIPE%'),'') eq FROM `nitro_dados.pipeimob_negocios` p WHERE p.imobiliaria_id=1 AND p.data_contrato IS NOT NULL"
    ") UNION ALL SELECT 'pad',NULL,NULL,NULL,NULL,REPEAT('x',400000),NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL")

def cmd_pipe(a):
    senha = os.environ.get("DASH_SENHA")
    assert senha, "defina DASH_SENHA"
    d = decifrar(senha)
    rows = []
    for r in json.load(open(a.arquivo, encoding="utf-8"))["rows"]:
        v = [c["v"] for c in r["f"]]
        if v[0] == "pad": continue
        # 26 colunas: ccv,env,vgv,vgc,lanc,etapa,gestor,imovel,tit,cha,cpg,cpv,reg,quem,mom,mc,mv,fin,banco,cat,bai,cid,est,ing,pap,eq
        t = lambda x: x or ""
        rows.append([v[0], t(v[1]), float(v[2] or 0), float(v[3] or 0), int(v[4] or 0), t(v[5]), t(v[6]), t(v[7]),
                     t(v[8]), t(v[9]), t(v[10]), t(v[11]), t(v[12]), t(v[13]), t(v[14]), t(v[15]), t(v[16]),
                     int(v[17] or 0), t(v[18]), t(v[19]), t(v[20]), t(v[21]), int(v[22] or -1), t(v[23]), t(v[24]), t(v[25])])
    assert len(rows) > 50, f"poucos contratos da PipeImob ({len(rows)}): nao publicar"
    antes = len(d.get("pipe", []))
    assert len(rows) >= antes * 0.9, f"contratos caíram de {antes} para {len(rows)}: conferir antes de publicar"
    rows.sort(key=lambda x: x[0]); d["pipe"] = rows
    print("pipe: contratos", len(rows), "(antes", antes, ") ultimo CCV", rows[-1][0])
    g.cifrar(d, senha, ENC)

# C2S (leads da Gralha, imobiliaria_id=1): mesma consulta da aba ao vivo, gravada em d["c2s"] (19 colunas, 1 linha por lead)
SQL_C2S_CORPO = ("SELECT CAST(DATE(a.created_at,'America/Sao_Paulo') AS STRING) dt,EXTRACT(HOUR FROM DATETIME(a.created_at,'America/Sao_Paulo')) hr,IFNULL(a.lead_source_name,'') fonte,IFNULL(a.channel_name,'') canal,IFNULL(d.negotiation_name,'') tipo,IFNULL(REGEXP_REPLACE(a.company_name,r'^Gralha Imóveis( \\| (Equipe )?)?',''),'') equipe,IFNULL(s.name,'') corretor,a.lead_status_id st,CASE a.funnel_status WHEN 'New lead' THEN 0 WHEN 'In attendance' THEN 1 WHEN 'Scheduled visit' THEN 2 WHEN 'Done visit' THEN 3 WHEN 'Created offer' THEN 4 ELSE 1 END fun,IFNULL(a.lost_reasons_name,'') mot,IFNULL(TIMESTAMP_DIFF(a.read_at,a.created_at,MINUTE),-1) rd,IF(a.created_by_id IS NOT NULL,1,0) man,IFNULL(p.neighbourhood,'') bai,IFNULL(p.city,'') cid,CAST(ROUND(IFNULL(CAST(p.price_float AS FLOAT64),0)) AS INT64) pre,IFNULL(IF(REGEXP_CONTAINS(TRIM(IFNULL(p.prop_ref,'')),r'^[0-]*$') OR TRIM(p.prop_ref)='1',REGEXP_EXTRACT(a.description,r'^\\[([^\\]]+)\\]'),TRIM(p.prop_ref)),'') cod,IF(ROW_NUMBER() OVER(PARTITION BY c.phone_global ORDER BY a.created_at)=1 OR c.phone_global IS NULL,1,0) uni,IF(a.done_details_done,1,0) ven,IFNULL((SELECT CASE MIN(CASE t.tag_name WHEN 'Quente - pronto para comprar' THEN 1 WHEN 'Morno - Em atendimento' THEN 2 WHEN 'Frio - cliente a trabalhar' THEN 3 WHEN 'Curioso - não compra' THEN 4 WHEN 'Telefone Inexistente' THEN 5 WHEN 'corretor de imoveis' THEN 6 END) WHEN 1 THEN 'Quente' WHEN 2 THEN 'Morno' WHEN 3 THEN 'Frio' WHEN 4 THEN 'Curioso' WHEN 5 THEN 'Telefone inexistente' WHEN 6 THEN 'Corretor' END FROM `nitro_dados.c2s_tags` t WHERE t.imobiliaria_id=1 AND t.lead_id=a.lead_id),'') tg FROM `nitro_dados.c2s_lead_attributes` a LEFT JOIN `nitro_dados.c2s_customer` c ON c.imobiliaria_id=1 AND c.lead_id=a.lead_id LEFT JOIN `nitro_dados.c2s_product` p ON p.imobiliaria_id=1 AND p.product_id=a.product_id LEFT JOIN `nitro_dados.c2s_real_estate_detail` d ON d.imobiliaria_id=1 AND d.product_id=a.product_id LEFT JOIN `nitro_dados.c2s_seller` s ON s.imobiliaria_id=1 AND s.seller_id=a.seller_id WHERE a.imobiliaria_id=1")
# O conector devolve no maximo 3000 linhas por chamada: empacota 25 leads por linha (JSON) -> ~630 linhas; a linha pad forca o resultado a ir para arquivo
SQL_C2S = ("WITH b AS (" + SQL_C2S_CORPO + "), n AS (SELECT *,DIV(ROW_NUMBER() OVER(ORDER BY dt,hr)-1,25) g FROM b) "
           "SELECT CAST(g AS STRING) g,STRING_AGG(TO_JSON_STRING((SELECT AS STRUCT n.* EXCEPT(g))),',') js FROM n GROUP BY g "
           "UNION ALL SELECT 'pad',REPEAT('x',400000)")

# Overview Multi-platform: cadeia C2S (pessoa, telefone) -> Vista (cliente, visita, proposta, ganho) -> PipeImob (imovel + data do CCV), gravada em d["mp"]={"p":[pessoas],"v":[vendas]}
# Empacotada em 25 por linha (limite de 3000 linhas do conector); a linha pad forca o resultado a ir para arquivo.
SQL_MP_CORPO = "WITH L AS (\n SELECT a.lead_id, a.created_at, DATE(a.created_at,'America/Sao_Paulo') d0, IFNULL(a.lead_source_name,'') fonte, IFNULL(a.company_name,'') eq, IFNULL(TIMESTAMP_DIFF(a.read_at,a.created_at,MINUTE),-1) rd,\n  RIGHT(REGEXP_REPLACE(IFNULL(c.phone_global,c.phone),r'\\D',''),11) ph\n FROM `nitro_dados.c2s_lead_attributes` a JOIN `nitro_dados.c2s_customer` c ON c.imobiliaria_id=1 AND c.lead_id=a.lead_id WHERE a.imobiliaria_id=1),\nPn AS (SELECT ph, COUNT(*) nl FROM L WHERE LENGTH(ph)>=10 GROUP BY ph),\nF AS (SELECT l.* FROM L l JOIN Pn USING(ph) WHERE nl<=12 QUALIFY ROW_NUMBER() OVER(PARTITION BY ph ORDER BY created_at)=1),\nVC AS (SELECT DISTINCT CAST(codigo AS STRING) cli, RIGHT(REGEXP_REPLACE(p,r'\\D',''),11) ph FROM `nitro_dados.vista_clientes`, UNNEST([celular,fone_principal,fone_comercial]) p WHERE imobiliaria_id=1 AND p IS NOT NULL),\nFC AS (SELECT * FROM F WHERE d0>='2026-01-01'),\nM AS (SELECT DISTINCT f.ph, f.d0, vc.cli FROM FC f JOIN VC vc ON vc.ph=f.ph),\nVIS AS (SELECT m.ph, MIN(DATE_DIFF(DATE(h.Data),m.d0,DAY)) dias FROM M m JOIN `nitro_dados.vw_consolidado_historico_gralha` h ON CAST(h.CodigoCliente AS STRING)=m.cli AND DATE(h.Data)>=m.d0 AND DATE(h.Data)<=DATE_ADD(m.d0,INTERVAL 180 DAY) WHERE LOWER(h.Assunto)='visita' AND h.Statusvisita='Finalizado' GROUP BY 1),\nPRO AS (SELECT m.ph, MIN(DATE_DIFF(DATE(h.Data),m.d0,DAY)) dias FROM M m JOIN `nitro_dados.vw_consolidado_historico_gralha` h ON CAST(h.CodigoCliente AS STRING)=m.cli AND DATE(h.Data)>=m.d0 AND DATE(h.Data)<=DATE_ADD(m.d0,INTERVAL 180 DAY) WHERE h.Assunto='Proposta' GROUP BY 1),\nGAN AS (SELECT m.ph, DATE_DIFF(DATE(d.Data),m.d0,DAY) dias, DATE(d.Data) dg, CAST(d.CodigoEmImovel AS STRING) imv FROM M m JOIN `nitro_dados.vw_consolidado_dados_gralha` d ON CAST(d.CodigoCliente AS STRING)=m.cli AND DATE(d.Data)>=m.d0 AND DATE(d.Data)<=DATE_ADD(m.d0,INTERVAL 180 DAY) WHERE d.Assunto IN ('Negócio ganho','Negocio Ganho via API') QUALIFY ROW_NUMBER() OVER(PARTITION BY m.ph ORDER BY DATE(d.Data))=1),\nGC AS (SELECT g.ph, IF(EXISTS(SELECT 1 FROM `nitro_dados.pipeimob_negocios` p WHERE p.imobiliaria_id=1 AND CAST(p.codigo_imovel AS STRING)=g.imv AND p.data_contrato BETWEEN DATE_SUB(g.dg,INTERVAL 30 DAY) AND DATE_ADD(g.dg,INTERVAL 90 DAY)),1,0) ccv FROM GAN g),\nPS AS (SELECT 'p' k, CAST(CAST(UNIX_DATE(f.d0) AS INT64) AS STRING) o, TO_JSON_STRING(STRUCT(CAST(f.d0 AS STRING) AS d, f.fonte AS f, f.rd AS r, IF(f.ph IN (SELECT ph FROM M),1,0) AS m, IFNULL(v.dias,-1) AS v, IFNULL(p.dias,-1) AS p, IFNULL(g.dias,-1) AS g, IFNULL(gc.ccv,0) AS c, f.eq AS e)) js\n  FROM FC f LEFT JOIN VIS v USING(ph) LEFT JOIN PRO p USING(ph) LEFT JOIN GAN g USING(ph) LEFT JOIN GC gc USING(ph)),\ncov AS (SELECT d.CodigoNegocio neg, MIN(DATE(d.Data)) dg, ANY_VALUE(CAST(d.CodigoCliente AS STRING)) cli, ANY_VALUE(IFNULL(d.veiculocaptacao_dn,'')) veic, ANY_VALUE(IFNULL(d.nome_equipe_usuario,'')) eqv, MAX(IFNULL(CAST(d.valornegocio_dn AS FLOAT64),0)) vgv, ANY_VALUE(CAST(d.CodigoEmImovel AS STRING)) imv\n  FROM `nitro_dados.vw_consolidado_dados_gralha` d WHERE d.Assunto IN ('Negócio ganho','Negocio Ganho via API') AND DATE(d.Data)>='2026-01-01' GROUP BY 1),\ncm AS (SELECT cov.neg, ARRAY_AGG(STRUCT(f.fonte AS fonte, DATE_DIFF(cov.dg,f.d0,DAY) AS dias) ORDER BY f.d0 DESC LIMIT 1)[OFFSET(0)] a FROM cov JOIN VC ON VC.cli=cov.cli JOIN F f ON f.ph=VC.ph AND f.d0<=cov.dg AND DATE_DIFF(cov.dg,f.d0,DAY)<=180 GROUP BY 1),\nVS AS (SELECT 'v' k, CAST(UNIX_DATE(cov.dg) AS STRING) o, TO_JSON_STRING(STRUCT(CAST(cov.dg AS STRING) AS d, cov.veic AS o, CAST(ROUND(cov.vgv) AS INT64) AS m, IF(cm.neg IS NOT NULL,1,0) AS c, IFNULL(cm.a.fonte,'') AS f, IFNULL(cm.a.dias,-1) AS a,\n  IF(EXISTS(SELECT 1 FROM `nitro_dados.pipeimob_negocios` p WHERE p.imobiliaria_id=1 AND CAST(p.codigo_imovel AS STRING)=cov.imv AND p.data_contrato BETWEEN DATE_SUB(cov.dg,INTERVAL 30 DAY) AND DATE_ADD(cov.dg,INTERVAL 90 DAY)),1,0) AS x, cov.eqv AS e)) js\n  FROM cov LEFT JOIN cm USING(neg)),\nU AS (SELECT * FROM PS UNION ALL SELECT * FROM VS),\nN AS (SELECT k, js, DIV(ROW_NUMBER() OVER(PARTITION BY k ORDER BY o)-1,25) g FROM U)\nSELECT k, CAST(g AS STRING) g, STRING_AGG(js,',') js FROM N GROUP BY k, g"
SQL_MP = SQL_MP_CORPO + "\nUNION ALL SELECT 'pad','pad',REPEAT('x',400000)"

def cmd_c2s(a):
    senha = os.environ.get("DASH_SENHA")
    assert senha, "defina DASH_SENHA"
    d = decifrar(senha)
    rows = []
    t = lambda x: x or ""
    K = ["dt","hr","fonte","canal","tipo","equipe","corretor","st","fun","mot","rd","man","bai","cid","pre","cod","uni","ven","tg"]
    for r in json.load(open(a.arquivo, encoding="utf-8"))["rows"]:
        v = [c["v"] for c in r["f"]]
        if v[0] == "pad": continue
        for o in json.loads("[" + v[1] + "]"):
            x = [o.get(k) for k in K]
            rows.append([x[0], int(x[1] or 0), t(x[2]), t(x[3]), t(x[4]), t(x[5]), t(x[6]), int(x[7] or 0), int(x[8] or 0), t(x[9]),
                         int(x[10] if x[10] not in (None, "") else -1), int(x[11] or 0), t(x[12]), t(x[13]), int(float(x[14] or 0)), t(x[15]),
                         int(x[16] or 0), int(x[17] or 0), t(x[18])])
    assert len(rows) > 1000, f"poucos leads do C2S ({len(rows)}): nao publicar"
    antes = len(d.get("c2s", []))
    assert len(rows) >= antes * 0.9, f"leads do C2S cairam de {antes} para {len(rows)}: conferir antes de publicar"
    rows.sort(key=lambda x: (x[0], x[1])); d["c2s"] = rows
    print("c2s: leads", len(rows), "(antes", antes, ") ultimo lead", rows[-1][0])
    g.cifrar(d, senha, ENC)

def cmd_mp(a):
    senha = os.environ.get("DASH_SENHA")
    assert senha, "defina DASH_SENHA"
    d = decifrar(senha)
    P, V = [], []
    for r in json.load(open(a.arquivo, encoding="utf-8"))["rows"]:
        v = [c["v"] for c in r["f"]]
        if v[0] == "pad": continue
        for o in json.loads("[" + v[2] + "]"):
            if v[0] == "p":
                P.append([o["d"], o.get("f") or "", int(o["r"]), int(o["m"]), int(o["v"]), int(o["p"]), int(o["g"]), int(o["c"]), o.get("e") or ""])
            elif v[0] == "v":
                V.append([o["d"], o.get("o") or "", int(o["m"]), int(o["c"]), o.get("f") or "", int(o["a"]), int(o["x"]), o.get("e") or ""])
    assert len(P) > 5000 and len(V) > 200, f"poucas linhas do Overview Multi-platform (pessoas {len(P)}, vendas {len(V)}): nao publicar"
    antes = d.get("mp", {})
    assert len(P) >= len(antes.get("p", [])) * 0.9 and len(V) >= len(antes.get("v", [])) * 0.9, "Overview Multi-platform caiu mais de 10%: conferir antes de publicar"
    P.sort(key=lambda x: x[0]); V.sort(key=lambda x: x[0]); d["mp"] = {"p": P, "v": V}
    print("mp: pessoas", len(P), "vendas", len(V), "ultimo contato", P[-1][0])
    g.cifrar(d, senha, ENC)

def cmd_sql(a):
    os.makedirs(a.dir, exist_ok=True)
    for m in range(12):
        open(os.path.join(a.dir, f"q_m{m}.sql"), "w").write(sql_m(a.desde, m))
    open(os.path.join(a.dir, "q_k.sql"), "w").write(sql_k(a.desde))
    open(os.path.join(a.dir, "q_ultimo.sql"), "w").write(g.SQL_L)
    open(os.path.join(a.dir, "q_pipe.sql"), "w").write(SQL_PIPE)
    open(os.path.join(a.dir, "q_c2s.sql"), "w").write(SQL_C2S)
    open(os.path.join(a.dir, "q_mp.sql"), "w").write(SQL_MP)
    print("desde", a.desde, "->", a.dir, sorted(os.listdir(a.dir)))

def decifrar(senha):
    j = json.load(open(ENC)); b = base64.b64decode
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    k = hashlib.pbkdf2_hmac("sha256", senha.encode(), b(j["salt"]), j["it"], 32)
    return json.loads(zlib.decompress(AESGCM(k).decrypt(b(j["iv"]), b(j["ct"]), None)))

def cmd_montar(a):
    senha = os.environ.get("DASH_SENHA")
    assert senha, "defina DASH_SENHA"
    d = decifrar(senha)
    dic = {k: {v: i for i, v in enumerate(l)} for k, l in d["dict"].items()}
    def ix(k, v):
        t = dic[k]
        if v not in t: t[v] = len(t)
        return t[v]
    dmin = (datetime.date.fromisoformat(a.desde) - D0).days
    hoje = datetime.date.today()
    mets = set(int(x) for x in a.metricas.split(",")) if a.metricas else set(range(12))
    # com --metricas, so essas metricas sao substituidas; as demais ficam como estao
    antigas = [r for r in d["rows"] if r[1] < dmin or r[0] not in mets]
    novas, cont = [], {}
    for arq in a.arquivos:
        for r in json.load(open(arq, encoding="utf-8"))["rows"]:
            m = int(r["f"][0]["v"])
            if m < 0: continue
            for ln in (r["f"][2]["v"] or "").split("\x1e"):
                if not ln: continue
                p = ln.split("\x1f"); dt = datetime.date.fromisoformat(p[0])
                if dt > hoje or dt < datetime.date.fromisoformat(a.desde): continue
                row = [m, (dt - D0).days, ix("cl", p[1]) if p[1] else -1]
                row += [ix(k, x or "") for k, x in zip(g.DIMS, p[2:14])]
                row += [ix("cc", p[14]) if p[14] else -1, ix("cl", p[15]) if p[15] else -1,
                        float(p[16]) if p[16] else 0, 1 if m == 7 else int(p[17])]
                novas.append(row); cont[m] = cont.get(m, 0) + 1
    assert set(cont) == mets, f"faltam metricas no resultado: {sorted(cont)} (esperado {sorted(mets)})"
    rows = antigas + novas
    rows.sort(key=lambda x: (x[0], x[1]))
    K = d.get("K", {})
    if a.k:
        for r in json.load(open(a.k, encoding="utf-8"))["rows"]:
            cli = r["f"][0]["v"]; cv = r["f"][1]["v"]
            if cli == "pad": continue
            cors = [x["v"] for x in cv] if isinstance(cv, list) else str(cv).split(",")
            if cli in dic["cl"]:
                K[str(dic["cl"][cli])] = sorted(ix("cc", c) for c in cors if c)
    d["rows"] = rows; d["K"] = K
    d["dict"] = {k: list(t.keys()) for k, t in dic.items()}
    d["ultimo"] = a.ultimo
    d["gerado"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    print("linhas antigas mantidas", len(antigas), "novas", len(novas), cont, "total", len(rows))
    g.cifrar(d, senha, ENC)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="c", required=True)
    s = sp.add_parser("sql"); s.add_argument("--desde", default=desde_padrao()); s.add_argument("--dir", default="/tmp/atu")
    m = sp.add_parser("montar"); m.add_argument("--desde", required=True); m.add_argument("--ultimo", required=True)
    m.add_argument("--k"); m.add_argument("--metricas", help="ex.: 8,9 (reconstroi so essas metricas)"); m.add_argument("arquivos", nargs="+")
    pp = sp.add_parser("pipe"); pp.add_argument("arquivo")
    pc = sp.add_parser("c2s"); pc.add_argument("arquivo")
    pm = sp.add_parser("mp"); pm.add_argument("arquivo")
    a = ap.parse_args()
    {"sql": cmd_sql, "montar": cmd_montar, "pipe": cmd_pipe, "c2s": cmd_c2s, "mp": cmd_mp}[a.c](a)
