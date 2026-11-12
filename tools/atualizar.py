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
    "SELECT CAST(p.data_contrato AS STRING) ccv,CAST(p.data_inicio_venda AS STRING) env,CAST(p.valor_contrato AS FLOAT64) vgv,CAST(p.total_comissao AS FLOAT64) vgc,IF(EXISTS(SELECT 1 FROM `nitro_dados.pipeimob_negocio_comissionados` m WHERE m.imobiliaria_id=1 AND m.transacao_unique_id_pipeimob=p.transacao_unique_id_pipeimob AND m.comissionado_tipo_participacao LIKE '%Gestor de Produto%') OR EXISTS(SELECT 1 FROM `nitro_dados.pipeimob_negocio_forma_pagamento` f WHERE f.imobiliaria_id=1 AND f.transacao_unique_id_pipeimob=p.transacao_unique_id_pipeimob AND f.forma_pagamento_nome IN ('Mensal','Anual','Chaves')),1,0) lanc,IFNULL(p.etapa_atual,'') etapa,IFNULL(p.agente_gestor,'') gestor,IFNULL(p.codigo_imovel,'') imovel,IFNULL(CAST(p.data_titulo_definitivo AS STRING),'') tit,IFNULL(CAST(p.data_entrega_chaves_posse AS STRING),'') cha,IFNULL(CAST(p.data_pagamento_comissao AS STRING),'') cpg,IFNULL(CAST(p.data_pagamento_comissao_prevista AS STRING),'') cpv,IFNULL(CAST(p.data_registro_publico AS STRING),'') reg,IFNULL(p.comissao_quem_paga,'') quem,IFNULL(p.comissao_momento_pagamento,'') mom,IFNULL(p.midia_origem_compradores,'') mc,IFNULL(p.midia_origem_vendedores,'') mv,IF(p.financiamento,1,0) fin,IFNULL(p.financiamento_banco,'') banco,IFNULL(p.categoria_crm,'') cat,IFNULL(p.endereco_bairro,'') bai,IFNULL(p.endereco_cidade,'') cid,IFNULL(p.diasemestoque,-1) est,IFNULL(CAST(DATE(p.ingested_at) AS STRING),'') ing,IFNULL((SELECT STRING_AGG(CONCAT(IFNULL(x.comissionado_tipo_participacao,'?'),'~',CAST(ROUND(IFNULL(CAST(x.comissionado_valor AS FLOAT64),0)) AS STRING)),'|') FROM `nitro_dados.pipeimob_negocio_comissionados` x WHERE x.imobiliaria_id=1 AND x.transacao_unique_id_pipeimob=p.transacao_unique_id_pipeimob),'') pap FROM `nitro_dados.pipeimob_negocios` p WHERE p.imobiliaria_id=1 AND p.data_contrato IS NOT NULL"
    ") UNION ALL SELECT 'pad',NULL,NULL,NULL,NULL,REPEAT('x',400000),NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL")

def cmd_pipe(a):
    senha = os.environ.get("DASH_SENHA")
    assert senha, "defina DASH_SENHA"
    d = decifrar(senha)
    rows = []
    for r in json.load(open(a.arquivo, encoding="utf-8"))["rows"]:
        v = [c["v"] for c in r["f"]]
        if v[0] == "pad": continue
        # 25 colunas: ccv,env,vgv,vgc,lanc,etapa,gestor,imovel,tit,cha,cpg,cpv,reg,quem,mom,mc,mv,fin,banco,cat,bai,cid,est,ing,pap
        t = lambda x: x or ""
        rows.append([v[0], t(v[1]), float(v[2] or 0), float(v[3] or 0), int(v[4] or 0), t(v[5]), t(v[6]), t(v[7]),
                     t(v[8]), t(v[9]), t(v[10]), t(v[11]), t(v[12]), t(v[13]), t(v[14]), t(v[15]), t(v[16]),
                     int(v[17] or 0), t(v[18]), t(v[19]), t(v[20]), t(v[21]), int(v[22] or -1), t(v[23]), t(v[24])])
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

def cmd_sql(a):
    os.makedirs(a.dir, exist_ok=True)
    for m in range(12):
        open(os.path.join(a.dir, f"q_m{m}.sql"), "w").write(sql_m(a.desde, m))
    open(os.path.join(a.dir, "q_k.sql"), "w").write(sql_k(a.desde))
    open(os.path.join(a.dir, "q_ultimo.sql"), "w").write(g.SQL_L)
    open(os.path.join(a.dir, "q_pipe.sql"), "w").write(SQL_PIPE)
    open(os.path.join(a.dir, "q_c2s.sql"), "w").write(SQL_C2S)
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
    a = ap.parse_args()
    {"sql": cmd_sql, "montar": cmd_montar, "pipe": cmd_pipe, "c2s": cmd_c2s}[a.c](a)
