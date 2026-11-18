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
function demoNote(c){try{const d=c.ultimo.split("-").reverse().join("/"),n=document.createElement("div");n.className="note";n.style.cssText="margin:4px 0 0";n.textContent=window.__DEMO?"Versão de demonstração · dados gravados até "+d+" (a versão ao vivo consulta o BigQuery).":"Dados atualizados diariamente · último dia da base: "+d;const t=document.querySelector("header h1");if(t)t.insertAdjacentElement("afterend",n);else{const x=document.querySelector(".tabs");x.parentNode.insertBefore(n,x)}}catch(_){}}
'''
LOAD_A='window.__DEMO=true;const ENC=%s;window.__cuboLoader=async()=>{const c=await dec(ENC,%s);demoNote(c);return c};'
import os
LOAD_B=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'login_ui.js'),encoding='utf-8').read()+r'''
const EQ=[["equipe-1","Equipe 1"],["equipe-bope","Equipe Bope"],["equipe-champions","Equipe Champions"],["equipe-elite","Equipe Elite"],["equipe-evolucao","Equipe Evolução"],["equipe-exupery","Equipe Exupéry"],["equipe-iron","Equipe Iron"],["equipe-magnitude","Equipe Magnitude"],["equipe-meta","Equipe Meta"],["equipe-nexo","Equipe Nexo"],["equipe-sky","Equipe Sky"],["equipe-supreme","Equipe Supreme"],["equipe-synergia","Equipe Synergia"],["equipe-vertice","Equipe Vértice"],["equipe-aguias","Equipe Águias"]];
const nrm=s=>(s||"").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g,"").replace(/[^a-z0-9]/g,"");
const findEq=u=>{const n=nrm(u);return n?EQ.find(([s])=>nrm(s)===n||nrm(s).replace(/^equipe/,"")===n):null};
function teamMode(nome){const hide=e=>e&&e.style.setProperty("display","none","important");
 document.querySelectorAll(".tabs button").forEach(b=>{if(b.dataset.tab!=="overview"&&b.dataset.tab!=="cmp")hide(b)});
 ["f-loja","f-equipe","f-veiculo","c1-loja","c1-equipe","c2-loja","c2-equipe"].forEach(i=>{const e=document.getElementById(i);hide(e&&e.closest("div"))});
 const h=document.querySelector("h1");if(h)h.insertAdjacentHTML("beforeend",' <span style="color:var(--br);font-weight:600">· '+nome+'</span>');document.title="Dashboard "+nome}
window.__cuboLoader=async()=>{const get=k=>{try{return sessionStorage.getItem(k)}catch(_){return null}},set=(k,v)=>{try{sessionStorage.setItem(k,v)}catch(_){}},del=k=>{try{sessionStorage.removeItem(k)}catch(_){}},
 fj=async u=>{const r=await fetch(u,{cache:"default"});if(!r.ok)throw new Error("Dados indisponíveis (HTTP "+r.status+")");return r.json()};
 const sq=get("gpw-eq");if(sq){try{const o=JSON.parse(sq),q=EQ.find(x=>x[0]===o.s),c=await dec(await fj("equipes/"+o.s+"/data.enc.json"),o.pw);teamMode(q[1]);demoNote(c);return c}catch(_){del("gpw-eq")}}
 const sg=get("gpw");if(sg){try{const c=await dec(await fj("data.enc.json"),sg);demoNote(c);return c}catch(_){del("gpw")}}
 let msg="";
 for(;;){const {u,pw}=await askPw(msg),q=findEq(u),adm=nrm(u)==="gralhaimoveis";msg="Usuário ou senha incorretos.";
  if(!adm&&!q)continue;
  let e;try{e=await fj(adm?"data.enc.json":"equipes/"+q[0]+"/data.enc.json")}catch(_){msg="Não foi possível carregar os dados. Tente de novo.";continue}
  try{const c=await dec(e,pw);if(adm)set("gpw",pw);else{set("gpw-eq",JSON.stringify({s:q[0],pw}));teamMode(q[1])}demoNote(c);return c}catch(_){}}};'''
marker='<script>\nconst DESDE='
assert marker in live, 'marcador do script principal nao encontrado'
ICONES='<link rel="icon" href="favicon.ico?v=2" sizes="any">\n<link rel="icon" type="image/png" sizes="32x32" href="favicon-32.png?v=2">\n<link rel="apple-touch-icon" href="apple-touch-icon.png?v=2">\n'

def injeta_assistente(h):
    """Assistente de dados (crIAtive): so no site estatico. Botao no menu lateral (escondido; so aparece se o cubo tiver askToken, ou seja, so no login gerencial),
    painel e tools/ask.js. Sem tools/ask.js, nao muda nada."""
    d=os.path.dirname(os.path.abspath(__file__));pj=os.path.join(d,'ask.js')
    if not os.path.exists(pj): return h
    rd=lambda n,pad: (open(os.path.join(d,n),encoding='utf-8').read().strip() if os.path.exists(os.path.join(d,n)) else pad)
    nome=rd('nome.txt','Assistente');ep=rd('endpoint.txt','')
    svg='<svg viewBox="0 0 24 24" fill="#fff" aria-hidden="true"><path d="M12 2l1.9 5.6L19.5 9.5l-5.6 1.9L12 17l-1.9-5.6L4.5 9.5l5.6-1.9L12 2z"/><path d="M19 15l.9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9L19 15z" opacity=".75"/></svg>'
    btn='<button class="mpb mpa" id="tab-ask" type="button" role="tab" data-tab="ask" aria-selected="false" aria-controls="panel-ask" hidden>'+svg+'<span>'+nome.replace('IA','<span class="iaw">IA</span>')+'<small>Pergunte aos dados</small></span></button>'
    css='<style>#tab-ask[hidden]{display:none}.mpa{margin-top:8px;background:linear-gradient(135deg,#232e66,#2f3f80 70%,#3a4c9a)}.mpa .iaw{color:#fff;font-weight:800}.mpa[aria-selected=true]{box-shadow:0 0 0 2px var(--sf),0 0 0 4px #2f3f80}</style>'
    assert h.count('</button></nav><div class="sbcap">')==1,'menu lateral nao encontrado'
    h=h.replace('</button></nav><div class="sbcap">','</button>'+btn+'</nav><div class="sbcap">',1)
    assert h.count('<section id="panel-ins"')==1
    h=h.replace('<section id="panel-ins"','<section id="panel-ask" role="tabpanel" aria-labelledby="tab-ask" hidden><div id="askroot"></div></section>\n<section id="panel-ins"',1)
    js=open(pj,encoding='utf-8').read().replace('__ASK_ENDPOINT__',ep).replace('__ASK_NAME__',nome)
    assert h.count('</body>')==1
    return h.replace('</head>',css+'</head>',1).replace('</body>','<script>\n'+js+'\n</script>\n</body>')
def build(loader,out,titulo,demo=False,icones=False,assistente=False):
    base=live0.replace(OLD,"function applyDflt(){const r={a:\"2026-09-01\",b:\"2026-09-30\",a1:\"2026-08-01\",b1:\"2026-08-31\"};") if demo else live0
    h=base.replace(marker,'<script>'+COMMON+loader+'</script>\n<script>'+shim+'</script>\n'+marker,1)
    h=re.sub(r'<!-- v[^>]*-->','<!-- '+titulo+' -->',h,count=1)
    if icones and 'rel="icon"' not in h: h=h.replace('</head>',ICONES+'</head>',1)
    if assistente: h=injeta_assistente(h)
    open(out,'w',encoding='utf-8').write(h);print(out,len(h))
if a.artefato:
    assert a.senha,'--senha obrigatoria para o artefato'
    enc=open(a.enc).read().strip();build(LOAD_A%(enc,json.dumps(a.senha)),a.artefato,'ESTATICO demonstracao (mesmo codigo da versao ao vivo)',True)
if a.site:
    build(LOAD_B,a.site,'ESTATICO site Netlify (mesmo codigo da versao ao vivo)',icones=True,assistente=True)
