#!/usr/bin/env python3
"""Gera site/data.json (cubo de eventos) a partir do BigQuery. Uso: python gerar_dados.py [--desde 2025-01-01] [--sql]"""
import argparse, json, datetime, os, sys

PROJ = "vistaprocessos"
V = {"c": "nitro_dados.vw_consolidado_clientes_capturados_gralha",
     "d": "nitro_dados.vw_consolidado_dados_gralha",
     "h": "nitro_dados.vw_consolidado_historico_gralha"}
# ordem fixa dos campos de dimensão (indices 3..14 da linha)
DIMS = ["loja", "equipe", "corretor", "veiculo", "bairro", "tipo", "cond", "lanc", "cod", "dorm", "area", "nome"]
COL = {  # coluna de cada dimensão em cada view
 "c": ["nome_agencia_usuario","nome_equipe_usuario","nome_usuario","veiculocaptacao_dn","bairro_imovel","categoria_imovel","Empreendimento","Lancamento","CodigoEmImovel","Dormitorios","AreaPrivativa","nomecliente_dn"],
 "d": ["nome_agencia_usuario","nome_equipe_usuario","nome_usuario","veiculocaptacao_dn","bairro_imovel","categoria_imovel","condominio_imovel","lancamento_imovel","CodigoEmImovel","dormitorios_imovel","areaprivativa_imovel","nomecliente_dn"],
 "h": ["nome_agencia_usuario","nome_equipe_usuario","nome_usuario","veiculocaptacao_dn","Bairro","Categoria","Empreendimento","Lancamento","CodigoEmImovel","Dormitorios","AreaPrivativa","nomecliente_dn"]}
X = "COALESCE(Assunto,'') NOT IN ('Negócio ganho','Negócio perdido')"
G = "Assunto IN ('Negócio ganho','Negocio Ganho via API')"
# (codigo, view, filtro, coluna da entidade distinta)
METR = [(0,"c","TRUE","CodigoCliente"),
        (1,"d",f"EtapaAcaoId IN ('9','5','1') AND {X}","CodigoCliente"),
        (2,"h","LOWER(Assunto)='visita'","CodigoCliente"),
        (3,"h","LOWER(Assunto)='proposta'","CodigoCliente"),
        (4,"d",f"EtapaAcaoId IN ('8','4','12') AND {X}","CodigoCliente"),
        (5,"d",G,"CodigoNegocio"),
        (6,"d","TRUE",None),   # 6 = corretores ativos (qualquer evento em dados)
        (7,"h","TRUE",None)]   # 7 = corretores com qualquer evento no historico (Ranking/Lojas)

def sel(code, v, cond, ent, desde):
    dims = []
    for i, n in enumerate(DIMS):
        if (code == 6 and i > 3) or (code == 7 and i > 2):
            dims.append(f"'' {n}")
        else:
            dims.append(f"COALESCE(NULLIF(CAST({COL[v][i]} AS STRING),''),'') {n}")
    ent_s = f"CAST({ent} AS STRING)" if ent else "CAST(NULL AS STRING)"
    kc = "CAST(CodigoCliente AS STRING)" if code == 5 else "CAST(NULL AS STRING)"
    val = "CAST(valornegocio_dn AS FLOAT64)" if code == 5 else "CAST(NULL AS FLOAT64)"
    return (f"SELECT {code} m, dt, cl, {', '.join(DIMS)}, cc, kc, MAX(v) v, COUNT(*) n FROM ("
            f"SELECT DATE(Data) dt, {ent_s} cl, {', '.join(dims)}, CAST(CodigoCorretor AS STRING) cc, {kc} kc, {val} v "
            f"FROM `{V[v]}` WHERE DATE(Data) BETWEEN DATE '{desde}' AND CURRENT_DATE('America/Sao_Paulo') AND {cond}) "
            f"GROUP BY m, dt, cl, {', '.join(DIMS)}, cc, kc")

def sql_cubo(desde):
    return " UNION ALL ".join(sel(c, v, w, e, desde) for c, v, w, e in METR)

def sql_pack(desde):
    f = lambda c: f"IFNULL({c},'')"
    row = " , '\\x1f', ".join([ "CAST(dt AS STRING)", f("cl")] + DIMS + [f("cc"), f("kc"), "IFNULL(CAST(v AS STRING),'')", "CAST(n AS STRING)"])
    return (f"WITH c AS ({sql_cubo(desde)}) SELECT m, FORMAT_DATE('%Y-%m', dt) mes, STRING_AGG(CONCAT({row}), '\\x1e') s FROM c GROUP BY m, mes ORDER BY m, mes")

def sql_k(desde):
    t = " UNION ALL ".join(f"SELECT CAST(CodigoCliente AS STRING) cli, CAST(CodigoCorretor AS STRING) cor FROM `{V[k]}`" for k in "dch")
    return (f"WITH vend AS (SELECT DISTINCT CAST(CodigoCliente AS STRING) cli FROM `{V['d']}` WHERE DATE(Data)>=DATE '{desde}' AND {G} AND CodigoCliente IS NOT NULL), "
            f"todos AS ({t}) SELECT cli, ARRAY_AGG(DISTINCT cor) cors FROM todos JOIN vend USING (cli) WHERE cor IS NOT NULL GROUP BY cli")

SQL_L = ("SELECT CAST(MAX(dt) AS STRING) l FROM (SELECT DATE(Data) dt FROM `%s` UNION ALL SELECT Data FROM `%s` UNION ALL SELECT Data FROM `%s`) "
         "WHERE dt < CURRENT_DATE('America/Sao_Paulo')" % (V["c"], V["d"], V["h"]))

def montar(linhas, kmap, ultimo, desde):
    """linhas: iteravel de (m,dt:date,cl,dims[12],cc,kc,v,n) ; kmap: {cli:[cc,...]}"""
    D0 = datetime.date(2020, 1, 1)
    dic = {k: {} for k in DIMS + ["cl", "cc"]}
    def ix(k, v):
        d = dic[k]
        if v not in d: d[v] = len(d)
        return d[v]
    rows, hoje = [], datetime.date.today()
    d_min = datetime.date.fromisoformat(desde)
    for m, dt, cl, dims, cc, kc, v, n in linhas:
        if dt > hoje or dt < d_min: continue
        row = [m, (dt - D0).days, ix("cl", cl) if cl else -1]
        row += [ix(k, x or "") for k, x in zip(DIMS, dims)]
        row += [ix("cc", cc) if cc else -1, ix("cl", kc) if kc else -1, v or 0, 1 if m == 7 else n]
        rows.append(row)
    rows.sort(key=lambda x: (x[0], x[1]))
    K = {}
    for cli, cors in kmap.items():
        if cli in dic["cl"]:
            K[str(dic["cl"][cli])] = sorted(ix("cc", c) for c in cors)
    return {"v": 1, "gerado": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "ultimo": ultimo, "d0": D0.isoformat(), "desde": desde,
            "dict": {k: list(d.keys()) for k, d in dic.items()}, "rows": rows, "K": K}

def ler_arquivos_mcp(arqs, karq):
    """Le resultados salvos das consultas empacotadas (sql_pack) e da consulta K feitas pelo conector do Claude."""
    def linhas():
        for a in arqs:
            for r in json.load(open(a, encoding="utf-8"))["rows"]:
                m = int(r["f"][0]["v"])
                for ln in (r["f"][2]["v"] or "").split("\x1e"):
                    if not ln: continue
                    p = ln.split("\x1f")
                    yield (m, datetime.date.fromisoformat(p[0]), p[1], p[2:14], p[14], p[15], float(p[16]) if p[16] else 0, int(p[17]))
    kmap = {r["f"][0]["v"]: r["f"][1]["v"].split(",") for r in json.load(open(karq, encoding="utf-8"))["rows"]}
    return linhas(), kmap

def cifrar(obj, senha, saida):
    """Gera data.enc.json: zlib + AES-GCM (chave PBKDF2-SHA256). O navegador decifra com a senha."""
    import zlib, base64, hashlib
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    raw = zlib.compress(json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), 9)
    salt, iv, it = os.urandom(16), os.urandom(12), 250000
    key = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, it, 32)
    ct = AESGCM(key).encrypt(iv, raw, None)
    b = lambda x: base64.b64encode(x).decode()
    with open(saida, "w") as f:
        json.dump({"v": 1, "it": it, "salt": b(salt), "iv": b(iv), "ct": b(ct)}, f, separators=(",", ":"))
    print(f"cifrado: {os.path.getsize(saida)/1e6:.1f} MB -> {saida}")

def gravar(out, a):
    d = os.path.dirname(a.saida); os.makedirs(d, exist_ok=True)
    enc, pla = os.path.join(d, "data.enc.json"), os.path.join(d, "data.json")
    if a.senha:
        cifrar(out, a.senha, enc)
        if os.path.exists(pla): os.remove(pla)
    else:
        json.dump(out, open(pla, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        if os.path.exists(enc): os.remove(enc)
        print(f"{len(out['rows'])} linhas -> {pla}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", default="2026-01-01")
    ap.add_argument("--saida", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "site", "data.json"))
    ap.add_argument("--sql", action="store_true")
    ap.add_argument("--sql-pack", action="store_true", help="imprime a consulta empacotada (cubo) para rodar no conector")
    ap.add_argument("--sql-k", action="store_true")
    ap.add_argument("--sql-ultimo", action="store_true")
    ap.add_argument("--senha", default=os.environ.get("DASH_SENHA"), help="se informada, grava data.enc.json (criptografado) em vez de data.json")
    ap.add_argument("--mcp", nargs="+", help="arquivos de resultado do sql_pack (conector do Claude)")
    ap.add_argument("--k", help="arquivo de resultado da consulta K")
    ap.add_argument("--ultimo", help="ultimo dia da base (AAAA-MM-DD)")
    a = ap.parse_args()
    if a.sql:
        print(sql_cubo(a.desde)); return
    if a.sql_pack:
        print(sql_pack(a.desde)); return
    if a.sql_k:
        print(sql_k(a.desde)); return
    if a.sql_ultimo:
        print(SQL_L); return
    if a.mcp:
        L, km = ler_arquivos_mcp(a.mcp, a.k)
        out = montar(L, km, a.ultimo, a.desde)
        gravar(out, a); return
    from google.cloud import bigquery
    cli = bigquery.Client(project=PROJ)
    ultimo = list(cli.query(SQL_L).result())[0]["l"]
    D0 = datetime.date(2020, 1, 1)
    dic = {k: {} for k in DIMS + ["cl", "cc"]}
    def ix(k, v):
        d = dic[k]
        if v not in d: d[v] = len(d)
        return d[v]
    rows = []
    for r in cli.query(sql_cubo(a.desde)).result():
        if r["dt"] > datetime.date.today(): continue
        row = [r["m"], (r["dt"] - D0).days, ix("cl", r["cl"]) if r["cl"] is not None else -1]
        row += [ix(n, r[n] or "") for n in DIMS]
        row += [ix("cc", r["cc"]) if r["cc"] is not None else -1,
                ix("cl", r["kc"]) if r["kc"] is not None else -1,
                round(r["v"], 2) if r["v"] is not None else 0, r["n"]]
        rows.append(row)
    rows.sort(key=lambda x: (x[0], x[1]))
    K = {}
    for r in cli.query(sql_k(a.desde)).result():
        if r["cli"] in dic["cl"]:
            K[str(dic["cl"][r["cli"]])] = sorted(ix("cc", c) for c in r["cors"])
    out = {"v": 1, "gerado": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
           "ultimo": ultimo, "d0": D0.isoformat(), "desde": a.desde,
           "dict": {k: list(d.keys()) for k, d in dic.items()}, "rows": rows, "K": K}
    gravar(out, a)

if __name__ == "__main__":
    main()
