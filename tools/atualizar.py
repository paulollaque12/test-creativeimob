#!/usr/bin/env python3
"""Atualizacao INCREMENTAL do cubo do dashboard (rodada diaria).

Fluxo (feito pelo Claude agendado, com o conector do BigQuery):
  1) python tools/atualizar.py sql [--desde AAAA-MM-DD] [--dir /tmp/atu]
        -> grava q_m0..q_m9.sql, q_k.sql, q_ultimo.sql (desde padrao = dia 1 do mes anterior)
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

def cmd_sql(a):
    os.makedirs(a.dir, exist_ok=True)
    for m in range(10):
        open(os.path.join(a.dir, f"q_m{m}.sql"), "w").write(sql_m(a.desde, m))
    open(os.path.join(a.dir, "q_k.sql"), "w").write(sql_k(a.desde))
    open(os.path.join(a.dir, "q_ultimo.sql"), "w").write(g.SQL_L)
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
    mets = set(int(x) for x in a.metricas.split(",")) if a.metricas else set(range(10))
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
    a = ap.parse_args()
    cmd_sql(a) if a.c == "sql" else cmd_montar(a)
