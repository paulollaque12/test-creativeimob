#!/usr/bin/env python3
"""Monta a versao estatica = HTML ao vivo (identico) + shim.js (responde as consultas a partir do cubo).
Uso: python build_estatico.py <html_ao_vivo> [--saida-artefato X.html] [--saida-site site/index.html] [--senha-artefato SENHA]"""
import sys,re,json,argparse
ap=argparse.ArgumentParser();ap.add_argument('live');ap.add_argument('--artefato');ap.add_argument('--site');ap.add_argument('--enc',default='docs/data.enc.json');ap.add_argument('--senha',default=None)
a=ap.parse_args()
live=open(a.live,encoding='utf-8').read();shim=open(__import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)),'shim.js'),encoding='utf-8').read()
OLD="function applyDflt(){const r=dfltRange();"
assert OLD in live
live0=live
COMMON=r'''
const b64=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
async function dec(e,pw){const k=await crypto.subtle.deriveKey({name:"PBKDF2",salt:b64(e.salt),iterations:e.it,hash:"SHA-256"},await crypto.subtle.importKey("raw",new TextEncoder().encode(pw),"PBKDF2",false,["deriveKey"]),{name:"AES-GCM",length:256},false,["decrypt"]),
 buf=await crypto.subtle.decrypt({name:"AES-GCM",iv:b64(e.iv)},k,b64(e.ct));return JSON.parse(await new Response(new Blob([buf]).stream().pipeThrough(new DecompressionStream("deflate"))).text())}
function demoNote(c){try{const d=c.ultimo.split("-").reverse().join("/"),n=document.createElement("div");n.className="note";n.style.cssText="margin:-14px 0 14px";n.textContent=window.__DEMO?"Versão de demonstração · dados gravados até "+d+" (a versão ao vivo consulta o BigQuery).":"Dados atualizados diariamente · último dia da base: "+d;const t=document.querySelector(".tabs");t.parentNode.insertBefore(n,t)}catch(_){}}
'''
LOAD_A='window.__DEMO=true;const ENC=%s;window.__cuboLoader=async()=>{const c=await dec(ENC,%s);demoNote(c);return c};'
import os
LOAD_B=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'login_ui.js'),encoding='utf-8').read()+r'''
window.__cuboLoader=async()=>{const r=await fetch("data.enc.json",{cache:"default"});if(!r.ok)throw new Error("Dados indisponíveis (HTTP "+r.status+")");const e=await r.json();let pw=null,msg="";try{pw=sessionStorage.getItem("gpw")}catch(_){}
 for(;;){if(!pw)pw=await askPw(msg);try{const c=await dec(e,pw);try{sessionStorage.setItem("gpw",pw)}catch(_){}demoNote(c);return c}catch(_){pw=null;msg="Senha incorreta. Tente de novo.";try{sessionStorage.removeItem("gpw")}catch(_){}}}};'''
marker='<script>\nconst DESDE='
assert marker in live, 'marcador do script principal nao encontrado'
ICONES='<link rel="icon" href="favicon.ico?v=2" sizes="any">\n<link rel="icon" type="image/png" sizes="32x32" href="favicon-32.png?v=2">\n<link rel="apple-touch-icon" href="apple-touch-icon.png?v=2">\n'
def build(loader,out,titulo,demo=False,icones=False):
    base=live0.replace(OLD,"function applyDflt(){const r={a:\"2026-09-01\",b:\"2026-09-30\",a1:\"2026-08-01\",b1:\"2026-08-31\"};") if demo else live0
    h=base.replace(marker,'<script>'+COMMON+loader+'</script>\n<script>'+shim+'</script>\n'+marker,1)
    h=re.sub(r'<!-- v[^>]*-->','<!-- '+titulo+' -->',h,count=1)
    if icones and 'rel="icon"' not in h: h=h.replace('</head>',ICONES+'</head>',1)
    open(out,'w',encoding='utf-8').write(h);print(out,len(h))
if a.artefato:
    assert a.senha,'--senha obrigatoria para o artefato'
    enc=open(a.enc).read().strip();build(LOAD_A%(enc,json.dumps(a.senha)),a.artefato,'ESTATICO demonstracao (mesmo codigo da versao ao vivo)',True)
if a.site:
    build(LOAD_B,a.site,'ESTATICO site Netlify (mesmo codigo da versao ao vivo)',icones=True)
