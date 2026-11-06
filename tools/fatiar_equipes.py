"""Fatia o cubo gerencial em 15 arquivos cifrados, um por equipe: docs/equipes/<slug>/data.enc.json.
Usado pelo login unico (usuario+senha) do dashboard: a equipe abre a MESMA pagina do gerencial em "modo equipe"
(tools/build_estatico.py) e le so o seu arquivo. Nao gera HTML.
Senha da equipe = <slug>-<token>; token = 8 letras/digitos de HMAC-SHA256(slug, EQUIPES_MESTRE) em base32 minusculo.
Senhas e segredos NUNCA sao gravados em arquivo/commit.
Uso: DASH_SENHA=... EQUIPES_MESTRE=... python3 -I tools/fatiar_equipes.py [--cubo docs/data.enc.json] [--saida docs/equipes] [--so "EQUIPE 1"]
"""
import argparse, base64, hashlib, hmac, json, os, re, sys, unicodedata, zlib

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EQUIPES = ["EQUIPE 1", "EQUIPE BOPE", "EQUIPE CHAMPIONS", "EQUIPE ELITE", "EQUIPE EVOLUÇÃO", "EQUIPE EXUPÉRY",
           "EQUIPE IRON", "EQUIPE MAGNITUDE", "EQUIPE META", "EQUIPE NEXO", "EQUIPE SKY", "EQUIPE SUPREME",
           "EQUIPE SYNERGIA", "EQUIPE VÉRTICE", "EQUIPE ÁGUIAS"]

def slug(nome):
    s = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")

def senha_equipe(nome, mestre):
    sl = slug(nome)
    tok = base64.b32encode(hmac.new(mestre.encode(), sl.encode(), hashlib.sha256).digest()).decode().lower()[:8]
    return f"{sl}-{tok}"

def bonito(nome):
    return " ".join(w.capitalize() if not w.isdigit() else w for w in nome.lower().split())

def decifrar(arq, senha):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    j = json.load(open(arq)); b = base64.b64decode
    k = hashlib.pbkdf2_hmac("sha256", senha.encode(), b(j["salt"]), j["it"], 32)
    return json.loads(zlib.decompress(AESGCM(k).decrypt(b(j["iv"]), b(j["ct"]), None)))

def cifrar(obj, senha, saida):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    raw = zlib.compress(json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), 9)
    salt, iv, it = os.urandom(16), os.urandom(12), 250000
    key = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, it, 32)
    ct = AESGCM(key).encrypt(iv, raw, None)
    b = lambda x: base64.b64encode(x).decode()
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    json.dump({"v": 1, "it": it, "salt": b(salt), "iv": b(iv), "ct": b(ct)}, open(saida, "w"), separators=(",", ":"))

# colunas de linha: 0 m,1 dia,2 cl,3 loja,4 equipe,5 corretor,6 veiculo,7 bairro,8 tipo,9 cond,10 lanc,11 cod,12 dorm,13 area,14 nome,15 cc,16 kc,17 valor,18 n
DIMCOL = {"loja": 3, "equipe": 4, "corretor": 5, "veiculo": 6, "bairro": 7, "tipo": 8, "cond": 9, "lanc": 10,
          "cod": 11, "dorm": 12, "area": 13, "nome": 14}

def fatiar(c, nome):
    """Cubo so com as linhas da equipe; dicionarios recompactados (nada de outras equipes) e K restrito."""
    eq = c["dict"]["equipe"]; assert nome in eq, f"equipe {nome!r} nao existe no cubo"
    ie = eq.index(nome)
    rows = [r for r in c["rows"] if r[4] == ie]
    mp = {k: {} for k in list(DIMCOL) + ["cl", "cc"]}
    nd = {k: [] for k in mp}
    def m(k, i):
        if i < 0: return i
        d = mp[k]
        if i not in d:
            d[i] = len(nd[k]); nd[k].append(c["dict"][k][i])
        return d[i]
    out = []
    for r in rows:
        r = list(r)
        for k, col in DIMCOL.items(): r[col] = m(k, r[col])
        r[2] = m("cl", r[2]); r[16] = m("cl", r[16]); r[15] = m("cc", r[15])
        out.append(r)
    # K: so clientes presentes nas vendas da equipe; corretores de outras equipes viram placeholders anonimos (so contam)
    K, anon = {}, {}
    def mk(x):
        if x in mp["cc"]: return mp["cc"][x]
        if x not in anon:
            nd["cc"].append(""); anon[x] = len(nd["cc"]) - 1
        return anon[x]
    for old, new in mp["cl"].items():
        v = c["K"].get(str(old))
        if v is not None: K[str(new)] = [mk(x) for x in v]
    return {**{k: c[k] for k in ("v", "gerado", "ultimo", "d0", "desde") if k in c},
            "dict": nd, "rows": out, "K": K}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cubo", default=os.path.join(RAIZ, "docs", "data.enc.json"))
    ap.add_argument("--saida", default=os.path.join(RAIZ, "docs", "equipes"))
    ap.add_argument("--so")
    a = ap.parse_args()
    sen, mestre = os.environ.get("DASH_SENHA"), os.environ.get("EQUIPES_MESTRE")
    assert sen and mestre and len(mestre) >= 16, "defina DASH_SENHA e EQUIPES_MESTRE (>=16 chars)"
    c = decifrar(a.cubo, sen)
    for nome in ([a.so] if a.so else EQUIPES):
        f = fatiar(c, nome); sl = slug(nome); arq = os.path.join(a.saida, sl, "data.enc.json")
        assert f["rows"] and f["ultimo"] == c["ultimo"], f"{nome}: sem linhas ou ultimo diferente"
        cifrar(f, senha_equipe(nome, mestre), arq)
        assert decifrar(arq, senha_equipe(nome, mestre))["ultimo"] == c["ultimo"], f"{nome}: conferencia falhou"
        print(f"{sl}: linhas {len(f['rows'])} ate {f['ultimo']} | {os.path.getsize(arq)/1e6:.2f} MB")

if __name__ == "__main__":
    main()
