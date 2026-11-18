/* ===== LABORATÓRIO · "Pergunte aos dados" (BETA) =====
   Assistente de dados (IA traduz a pergunta no Worker; plano B por regras) -> consulta estruturada -> calcula no cubo local (window.__cuboInfo).
   Nada sai do navegador. A função interpretar() devolve um "spec"; para trocar por IA depois, basta gerar o mesmo spec. */
(function(){
const D0=Date.UTC(2020,0,1),U=Date.UTC;
const norm=s=>(s==null?"":String(s)).normalize("NFD").replace(/[̀-ͯ]/g,"").toLowerCase().replace(/[^a-z0-9/\s.%-]/g," ").replace(/\s+/g," ").trim();
const dIdx=(y,m,d)=>Math.round((U(y,m,d)-D0)/864e5),ymd=n=>{const d=new Date(D0+n*864e5);return[d.getUTCFullYear(),d.getUTCMonth(),d.getUTCDate()]};
const iso=n=>new Date(D0+n*864e5).toISOString().slice(0,10),br=n=>iso(n).slice(8)+"/"+iso(n).slice(5,7),brY=n=>br(n)+"/"+iso(n).slice(0,4);
const monthStart=(y,m)=>dIdx(y,m,1),monthEnd=(y,m)=>dIdx(y,m+1,1)-1;
const wkStart=n=>n-((new Date(D0+n*864e5).getUTCDay()+6)%7);
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const fmt=v=>Math.round(v).toLocaleString("pt-BR");
const fmtV=v=>{const a=Math.abs(v);return a>=1e6?"R$ "+(v/1e6).toLocaleString("pt-BR",{maximumFractionDigits:2})+" Mi":a>=1e3?"R$ "+Math.round(v/1e3).toLocaleString("pt-BR")+" mil":"R$ "+Math.round(v).toLocaleString("pt-BR")};
const METN={0:"Captação (leads)",1:"Oportunidades",2:"Visitas",3:"Propostas",4:"Fechamentos",5:"Vendas",8:"Agenciamentos",9:"Placas",vgv:"VGV"};
const METL={0:"leads",1:"oportunidades",2:"visitas",3:"propostas",4:"fechamentos",5:"vendas",8:"agenciamentos",9:"placas",vgv:"VGV"};
const ENT={corretor:{col:5,s:"corretor",p:"corretores",g:"o"},equipe:{col:4,s:"equipe",p:"equipes",g:"a"},loja:{col:3,s:"loja",p:"lojas",g:"a"},veiculo:{col:6,s:"veículo",p:"veículos",g:"o"},bairro:{col:7,s:"bairro",p:"bairros",g:"o"},tipo:{col:8,s:"tipologia",p:"tipologias",g:"a",im:1},cond:{col:9,s:"condomínio",p:"condomínios",g:"o",im:1},lanc:{col:10,s:"lançamento",p:"lançamentos",g:"o",im:1},dorm:{col:12,s:"nº de dormitórios",p:"nºs de dormitórios",g:"o",im:1},cod:{col:11,s:"imóvel",p:"imóveis",g:"o",im:1}};
const IMMET={0:"parcial",2:1,3:1,5:1,vgv:1}; /* dimensões do imóvel só existem em visitas, propostas, vendas/VGV e em parte dos leads */
const MESES=["janeiro","fevereiro","marco","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"],MESN=["janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"];
let C=null,ULT=0,NAMES=null;
const ENDPOINT=(v=>v.startsWith("__")?"":v)("__ASK_ENDPOINT__");
const NAME=(v=>v.startsWith("__")?"Assistente":v)("__ASK_NAME__");

/* ---------- interpretação ---------- */
function metrica(q){
 if(/\b(vgv|volume de vendas|valor vendido|valor das vendas|faturamento)\b/.test(q))return"vgv";
 if(/agenciament|imoveis captados|captaram imove/.test(q))return 8;
 if(/\bplaca/.test(q))return 9;
 if(/oportunidade/.test(q))return 1;
 if(/\bvisita/.test(q))return 2;
 if(/\bproposta/.test(q))return 3;
 if(/fechament/.test(q))return 4;
 if(/\bvend(a|as|eu|eram|er|emos|ido|idos)\b|\bvendi/.test(q))return 5;
 if(/\blead|captac|\bcadastr/.test(q))return 0;
 return null}
const ENTW="corretor(?:es)?|equipes?|lojas?|agencias?|veiculos?|bairros?|tipologias?|tipos? d[eoa]s? imove(?:l|is)|tipos? de imovel|condominios?|empreendimentos?|lancamentos?|dormitorios?|quartos?|imove(?:l|is)(?! captad)";
const entKey=w=>w.startsWith("corretor")?"corretor":w.startsWith("equipe")?"equipe":w.startsWith("loja")||w.startsWith("agencia")?"loja":w.startsWith("veiculo")?"veiculo":w.startsWith("bairro")?"bairro":w.startsWith("tipologia")||w.startsWith("tipo")?"tipo":w.startsWith("condominio")||w.startsWith("empreendimento")?"cond":w.startsWith("lancamento")?"lanc":w.startsWith("dormitorio")||w.startsWith("quarto")?"dorm":"cod";
function entidade(q){
 let m=new RegExp("\\b(?:quantos|quantas|quais|quem|qual|ranking de|ranking dos|ranking das|top\\s*\\d*(?: de| dos| das)?|melhores|maiores|piores|menores|melhor|maior|pior|menor)\\s+(?:os |as |o |a )?("+ENTW+")\\b").exec(q)||new RegExp("\\bpor\\s+("+ENTW+")\\b").exec(q);
 if(!m)m=/\b(corretores|equipes|lojas|veiculos|bairros|tipologias?|condominios?|empreendimentos?|lancamentos?|dormitorios?|imoveis)\b/.exec(q);
 if(!m)return null;return entKey(m[1])}
function nomes(){
 if(NAMES)return NAMES;NAMES={};
 for(const k of Object.keys(ENT)){const L=C.dict[k]||[];NAMES[k]=L.map((n,i)=>({i,n,q:norm(n)})).filter(o=>o.q.length>=2)}
 return NAMES}
function filtros(q){
 const N=nomes(),F={},txt=" "+q+" ",found=[];
 const add=(dim,o)=>{(F[dim]=F[dim]||new Set()).add(o.i);found.push([dim,o.n])};
 N.equipe.forEach(o=>{if(txt.includes(" "+o.q+" ")||txt.includes(" equipe "+o.q.replace(/^equipe /,"")+" "))add("equipe",o)});
 N.loja.forEach(o=>{const b=o.q.replace(/^agencia /,"");if(txt.includes(" "+o.q+" ")||new RegExp("\\b(?:loja|agencia)(?: d[eoa]s?| n[oa])? "+b.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")+"\\b").test(q))add("loja",o)});
 N.corretor.forEach(o=>{if(/^(equipe|agencia) /.test(o.q))return;const t=o.q.split(" ");const two=t.slice(0,2).join(" ");if(txt.includes(" "+o.q+" ")||(t.length>=2&&two.length>=7&&txt.includes(" "+two+" ")))add("corretor",o)});
 [["veiculo","(?:veiculo|canal|origem)(?: de captacao)?"],["bairro","bairro"],["tipo","(?:tipo|tipologia)(?: d[eoa]s?)?(?: imovel)?"],["cond","(?:condominio|empreendimento)"]].forEach(([dim,pre])=>N[dim].forEach(o=>{if(new RegExp("\\b"+pre+"(?: (?:d[eoa]s?|n[oa]s?|em|pel[oa]))? "+o.q.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")+"\\b").test(q))add(dim,o)}));
 N.tipo.forEach(o=>{if(o.q==="loja"||found.some(f=>f[0]==="tipo"&&f[1]===o.n))return;const e=o.q.replace(/[.*+?^${}()|[\]\\]/g,"\\$&"),w=o.q.split(" ")[0];
  if(new RegExp("\\b(?:d[eoa]s?|em|n[oa]s?|so|apenas)\\s+"+e+"(?:s|es)?\\b").test(q)||(o.q.includes(" ")&&new RegExp("\\b(?:d[eoa]s?|em|n[oa]s?|so|apenas)\\s+"+w+"(?:s|es)?\\b").test(q)&&!/\b(?:tipologia|tipo)\\b/.test(q.replace(w,""))))add("tipo",o)});
 {const mm=/\b(\d{1,2})\s*(?:dormitorios?|quartos?|dorms?)\b/.exec(q);if(mm){const i=(C.dict.dorm||[]).indexOf(mm[1]);if(i>=0)add("dorm",{i,n:mm[1]+" dormitório"+(mm[1]==="1"?"":"s")})}
  if(/\b(?:so |apenas )?lancamentos?\b/.test(q)&&!/\bpor lancamento/.test(q)){const i=(C.dict.lanc||[]).indexOf("Sim");if(i>=0)add("lanc",{i,n:"lançamentos"})}}
 return{F,found}}
function ant(per){ // período anterior padrão
 const len=per.b-per.a+1;
 if(per.tipo==="ano")return null;
 if(per.tipo==="mtd"||per.tipo==="mes"){const[y,m]=ymd(per.a),pm=m?m-1:11,py=m?y:y-1,pa=monthStart(py,pm),cheio=per.b===monthEnd(y,m);return{a:pa,b:cheio?monthEnd(py,pm):Math.min(pa+len-1,monthEnd(py,pm)),rot:"mês anterior"}}
 if(per.tipo==="wtd"||per.tipo==="sem")return{a:per.a-7,b:per.b-7,rot:"semana anterior"};
 return{a:per.a-len,b:per.a-1,rot:len===1?"dia anterior":len+" dias anteriores"}}
function periodo(q){
 let m;
 if((m=/(\d{1,2})\/(\d{1,2})(?:\/(\d{2,4}))?\s*(?:a|ate|ao|-)\s*(\d{1,2})\/(\d{1,2})(?:\/(\d{2,4}))?/.exec(q))){
  const y0=+(ymd(ULT)[0]),Y=s=>s?(s.length===2?2000+ +s:+s):y0;const a=dIdx(Y(m[3]),+m[2]-1,+m[1]),b=dIdx(Y(m[6]),+m[5]-1,+m[4]);if(b>=a)return{a,b,tipo:"x",rot:br(a)+" a "+br(b)}}
 if((m=/\bdia (\d{1,2})\/(\d{1,2})(?:\/(\d{2,4}))?\b/.exec(q))){const y=m[3]?(m[3].length===2?2000+ +m[3]:+m[3]):ymd(ULT)[0],a=dIdx(y,+m[2]-1,+m[1]);return{a,b:a,tipo:"x",rot:brY(a)}}
 if((m=/\bultim[oa]s? (\d{1,2}|dois|duas|tres|quatro|cinco|seis|sete|oito|nove|dez|onze|doze) mes(?:es)?\b/.exec(q))){const W={dois:2,duas:2,tres:3,quatro:4,cinco:5,seis:6,sete:7,oito:8,nove:9,dez:10,onze:11,doze:12},n=Math.min(12,Math.max(1,+m[1]||W[m[1]])),[y,mo]=ymd(ULT);let yy=y,mm=mo-(n-1);while(mm<0){mm+=12;yy--}const a=Math.max(monthStart(yy,mm),dIdx(2026,0,1));return{a,b:ULT,tipo:"x",rot:"últimos "+n+" meses ("+br(a)+" a "+br(ULT)+")",nota:n>1?"últimos "+n+" meses = mês atual + "+(n-1)+" anteriores":""}}
 if((m=/ultim[oa]s? (\d+) (dias?|semanas?)/.exec(q))){const n=+m[1]*(m[2][0]==="s"?7:1);return{a:ULT-n+1,b:ULT,tipo:"x",rot:"últimos "+n+" dias ("+br(ULT-n+1)+" a "+br(ULT)+")"}}
 if(/\bultima semana\b|\bultimos 7 dias\b/.test(q))return{a:ULT-6,b:ULT,tipo:"x",rot:"últimos 7 dias ("+br(ULT-6)+" a "+br(ULT)+")"};
 if(/\bsemana (passada|anterior)\b|\bsemana pasada\b/.test(q)){const s=wkStart(ULT)-7;return{a:s,b:s+6,tipo:"sem",rot:"semana passada ("+br(s)+" a "+br(s+6)+")"}}
 if(/\b(esta|nesta|essa|nessa|na) semana\b|\bsemana atual\b/.test(q)){const s=wkStart(ULT);return{a:s,b:ULT,tipo:"wtd",rot:"esta semana ("+br(s)+" a "+br(ULT)+")"}}
 if(/\bmes (passado|anterior)\b|\bultimo mes\b/.test(q)){const[y,mo]=ymd(ULT),pm=mo?mo-1:11,py=mo?y:y-1;return{a:monthStart(py,pm),b:monthEnd(py,pm),tipo:"mes",rot:"mês passado ("+MESN[pm]+")"}}
 for(let i=0;i<12;i++){if(new RegExp("\\b"+MESES[i]+"\\b").test(q)){let y=ymd(ULT)[0];const a=monthStart(y,i),b=Math.min(monthEnd(y,i),ULT);return{a,b:Math.max(a,b),tipo:"mes",rot:MESN[i]+" de "+y}}}
 if(/\bontem\b|\bultimo dia\b|\bdia anterior\b|\bhoje\b/.test(q))return{a:ULT,b:ULT,tipo:"x",rot:(/\bhoje\b/.test(q)?"último dia com dados: ":"")+brY(ULT)};
 if(/\b(este|neste|esse|nesse|no) ano\b|\bem 20\d\d\b|\bano todo\b/.test(q)){const y=ymd(ULT)[0];return{a:monthStart(y,0),b:ULT,tipo:"ano",rot:"ano "+y+" até "+br(ULT)}}
 if(/\b(este|neste|esse|nesse|no) mes\b|\bmes atual\b/.test(q)){const[y,mo]=ymd(ULT);return{a:monthStart(y,mo),b:ULT,tipo:"mtd",rot:"este mês ("+br(monthStart(y,mo))+" a "+br(ULT)+")"}}
 return null}
function interpretar(raw){
 let q=norm(raw);if(q.length<3)return null;
 [[/\bcuantos\b/g,"quantos"],[/\bcuantas\b/g,"quantas"],[/\bcuales\b/g,"quais"],[/\bcorredor(es)?\b/g,"corretor$1"],[/\bventas\b/g,"vendas"],[/\bventa\b/g,"venda"],[/\bpropuestas\b/g,"propostas"],[/\bpropuesta\b/g,"proposta"],[/\bmes pasado\b/g,"mes passado"],[/\bsemana pasada\b/g,"semana passada"],[/\baumentaron\b/g,"aumentaram"],[/\bdisminuyeron\b/g,"diminuiram"],[/\bultimo (\d+) dias\b/g,"ultimos $1 dias"],[/\ben el ano\b/g,"este ano"]].forEach(([a,b])=>{q=q.replace(a,b)});
 const hasUp=/\b(aument|cresc|subir|subiram|subiu|melhor(?:ar|aram|ou)|evolu|avanc|aceler)/.test(q),hasDown=/\b(diminu|cair|cairam|caiu|reduz|pior(?:ar|aram|ou)|recu|desacel|queda)/.test(q);
 const dir=hasUp&&!hasDown?"up":hasDown&&!hasUp?"down":null;
 let met=metrica(q),ent=entidade(q),assum=[];
 if(met===null){met=5;assum.push("métrica: vendas")}
 const rankMais=/\b(mais|maior(?:es)?|melhor(?:es)?|lider|top\s*\d*|ranking)\b/.test(q),rankMenos=/\b(menos|menor(?:es)?|pior(?:es)?)\b/.test(q);
 if(!ent&&(dir||rankMais||rankMenos)){ent="corretor";assum.push("por corretor")}
 const ng=/\b(nao|sem|nenhum|nenhuma|zero|nunca)\b/.exec(q);
 if(ng){ // "teve em A e nao teve em B" (ou o inverso)
  const L=q.slice(0,ng.index),Rr=q.slice(ng.index+ng[0].length);let had=null,none=null;
  if(ent&&met!==null||ent){had=periodo(L);none=periodo(Rr);
   if(!had&&none){const parts=Rr.split(/\b(?:mas|e|porem|que)\b/);const n1=periodo(parts[0]),h1=parts.length>1?periodo(parts.slice(1).join(" ")):null;if(n1&&h1){none=n1;had=h1}else{had=null}}}
  const{F:F2,found:f2}=filtros(q);
  if(ent&&had&&none)return{modo:"lost",met,ent,per:had,prev:none,F:F2,found:f2,assum,raw,dir:null};
  return{modo:"nao_entendi",motivo:"negacao",raw}}
 const cmp=q.split(/\b(?:vs\.?|versus|contra|comparad[oa]s? (?:com|ao|a)|em relacao (?:a|ao)|comparando com)\b/);
 let per=periodo(cmp[0]),prev=null,pAssum=false;
 if(!per){per=periodo(q);}
 if(cmp.length>1){const p2=periodo(cmp[1]);if(p2)prev={a:p2.a,b:p2.b,rot:p2.rot}}
 if(!per){const[y,mo]=ymd(ULT);per={a:monthStart(y,mo),b:ULT,tipo:"mtd",rot:"este mês ("+br(monthStart(y,mo))+" a "+br(ULT)+")"};pAssum=true;assum.push("período: este mês")}
 if(per.nota)assum.push(per.nota);
 if(!prev)prev=ant(per);
 if(!prev&&dir)prev={a:per.a-(per.b-per.a+1),b:per.a-1,rot:"período anterior"};
 const{F,found}=filtros(q);
 const quant=/\b(quantos|quantas)\b/.test(q),quais=/\b(quais|quem)\b/.test(q);
 let modo;
 if(ent&&dir)modo="movers";else if(ent&&(rankMais||rankMenos))modo="rank";else if(ent&&quant)modo="count";else if(ent&&quais)modo="list";else if(ent)modo="break";else modo="total";
 const tn=/\btop\s*(\d+)/.exec(q)||/\bos (\d+) (?:maiores|melhores|piores|menores)/.exec(q);
 return{modo,met,ent,dir,asc:rankMenos&&!rankMais,top:tn?+tn[1]:(/\b(qual|quem)\b/.test(q)&&modo==="rank"?1:10),per,prev,F,found,assum,raw}}

/* ---------- cálculo ---------- */
function agg(sp,a,b){
 const col=sp.ent?ENT[sp.ent].col:null,m=sp.met,vgv=m==="vgv",mk=vgv?5:m,per=new Map(),all=vgv?new Map():new Set(),FK=Object.keys(sp.F);
 const fc=FK.map(k=>[ENT[k].col,sp.F[k]]);
 for(const r of C.rows){if(r[0]!==mk||r[1]<a||r[1]>b||r[2]<0)continue;
  let ok=true;for(let i=0;i<fc.length;i++)if(!fc[i][1].has(r[fc[i][0]])){ok=false;break}if(!ok)continue;
  const k=col==null?0:r[col];let s=per.get(k);
  if(vgv){if(!s){s=new Map();per.set(k,s)}const o=s.get(r[2]);if(o===undefined||r[17]>o)s.set(r[2],r[17]);const o2=all.get(r[2]);if(o2===undefined||r[17]>o2)all.set(r[2],r[17])}
  else{if(!s){s=new Set();per.set(k,s)}s.add(r[2]);all.add(r[2])}}
 const val=s=>{if(!vgv)return s.size;let t=0;s.forEach(v=>t+=v);return t};
 const out=new Map();per.forEach((s,k)=>out.set(k,val(s)));return{map:out,total:val(all)}}
const nm=(sp,k)=>{const n=C.dict[sp.ent][k];if(sp.ent==="dorm"&&n!==""&&n!=null)return n+(n==="1"?" dormitório":" dormitórios");if(sp.ent==="lanc"&&n)return n==="Sim"?"Lançamento":"Pronto/usado";return n||"(sem "+ENT[sp.ent].s+")"};
const V=(sp,v)=>sp.met==="vgv"?fmtV(v):fmt(v);

function calcular(sp){
 if(sp.modo==="lost"||sp.modo==="both"){const A=agg(sp,sp.per.a,sp.per.b),B=agg(sp,sp.prev.a,sp.prev.b),rows=[];A.map.forEach((v,k)=>{const pb=B.map.get(k)||0;if(v>=(sp.min||1)&&(sp.modo==="both"?pb>0:!(pb>0)))rows.push({k,n:nm(sp,k),c:v,p:pb,d:v-pb})});return{A,B,rows}}
 const A=agg(sp,sp.per.a,sp.per.b),B=sp.prev?agg(sp,sp.prev.a,sp.prev.b):{map:new Map(),total:0};
 const rows=[];if(sp.ent){const ks=new Set([...A.map.keys(),...B.map.keys()]);ks.forEach(k=>{const c=A.map.get(k)||0,p=B.map.get(k)||0;rows.push({k,n:nm(sp,k),c,p,d:c-p})})}
 return{A,B,rows}}

/* ---------- apresentação ---------- */
const pct=(c,p)=>p>0?((c-p)/p*100>0?"+":"")+Math.round((c-p)/p*100)+"%":c>0?"novo":"—";
const cls=d=>d>0?"pos":d<0?"neg":"";
function tabela(sp,rs,hide){
 const lim=15,show=rs.slice(0,lim),np=!sp.prev||hide;
 let h='<div class="atw"><table class="at"><thead><tr><th>'+esc(ENT[sp.ent].s[0].toUpperCase()+ENT[sp.ent].s.slice(1))+'</th><th>'+hd(sp.per)+'</th>'+(np?"":"<th>"+hd(sp.prev)+"</th><th>Variação</th>")+'</tr></thead><tbody>';
 show.forEach(r=>{h+="<tr><td>"+esc(r.n)+"</td><td>"+V(sp,r.c)+"</td>"+(np?"":"<td>"+V(sp,r.p)+'</td><td class="'+cls(r.d)+'">'+(r.d>0?"+":"")+V(sp,r.d)+" · "+pct(r.c,r.p)+"</td>")+"</tr>"});
 h+="</tbody></table></div>";if(rs.length>lim)h+='<div class="amut">e mais '+(rs.length-lim)+' na lista.</div>';return h}
function chips(sp){
 const c=[];if(sp.ia)c.push("IA");c.push(METN[sp.met]+(sp.met==="vgv"?"":" (clientes únicos)"));
 if(sp.ent)c.push("por "+ENT[sp.ent].s);c.push(sp.per.rot);if(sp.prev)c.push("vs. "+sp.prev.rot+" ("+br(sp.prev.a)+" a "+br(sp.prev.b)+")");
 sp.found.forEach(([d,n])=>c.push("filtro: "+n));
 if(sp.dir)c.push(sp.dir==="up"?"só quem aumentou":"só quem diminuiu");
 if(sp.ent&&ENT[sp.ent].im&&IMMET[sp.met]!==1)sp.assum=sp.assum.concat([IMMET[sp.met]==="parcial"?"a dimensão do imóvel só existe para parte dos leads":"a dimensão do imóvel (tipologia, condomínio, dormitórios) só existe para visitas, propostas, vendas e VGV; para esta métrica o resultado fica sem classificação"]);
 return '<div class="achips">Entendi assim: '+c.map(x=>"<span>"+esc(x)+"</span>").join("")+"</div>"+(sp.ia&&sp.entendi?'<div class="amut">'+esc(sp.entendi)+"</div>":"")+(sp.assum.length?'<div class="amut">Assumi: '+esc(sp.assum.join(" · "))+".</div>":"")}
function tab2(sp,rs,h1,h2){const lim=15;let h='<div class="atw"><table class="at"><thead><tr><th>'+esc(ENT[sp.ent].s[0].toUpperCase()+ENT[sp.ent].s.slice(1))+"</th><th>"+hd(sp.per)+"</th><th>"+hd(sp.prev)+"</th></tr></thead><tbody>";rs.slice(0,lim).forEach(r=>{h+="<tr><td>"+esc(r.n)+"</td><td>"+V(sp,r.c)+"</td><td>"+V(sp,r.p)+"</td></tr>"});h+="</tbody></table></div>";if(rs.length>lim)h+='<div class="amut">e mais '+(rs.length-lim)+" na lista.</div>";return h}
const cap=x=>x.charAt(0).toUpperCase()+x.slice(1);
const emp=r=>{r=String(r).replace(/\s*\(.*\)\s*$/,"");
 if(/^últimos/i.test(r))return"nos "+r;if(/^esta semana/i.test(r))return"nesta semana";if(/^este mês/i.test(r))return"neste mês";
 if(/^(mês|ano)\b/i.test(r))return"no "+r;if(/^semana\b/i.test(r))return"na "+r;if(/^dia\b/i.test(r))return"no "+r;if(/^[0-9]/.test(r))return"em "+r;return"em "+r};
const curto=r=>String(r).replace(/\s*\(.*\)\s*$/,"");
const filt=sp=>sp.found.length?" (filtro: "+[...new Set(sp.found.map(f=>f[1]))].join(", ")+")":"";
const quem=(sp,rs,n)=>rs.slice(0,n).map(r=>r.n+" ("+V(sp,r.c)+")").join(", ")+(rs.length>n?" e mais "+(rs.length-n):"");
const hd=p=>esc(cap(curto(p.rot)))+'<span class="ad">'+br(p.a)+(p.a===p.b?"":" a "+br(p.b))+"</span>";
const art=(E,n)=>n===1?E.s:E.p;
function responder(sp){
 if(sp.modo==="lost"||sp.modo==="both"){const R=calcular(sp),E=ENT[sp.ent],ml=METL[sp.met],rs=R.rows.sort((x,y)=>y.c-x.c||(x.n<y.n?-1:1)),tA=[...R.A.map.values()].filter(v=>v>0).length,bo=sp.modo==="both",n=rs.length;
  const chp=[METN[sp.met]+(sp.met==="vgv"?"":" (clientes únicos)"),"por "+E.s,"com "+ml+" em: "+sp.per.rot,(bo?"e com ":"sem ")+ml+" em: "+sp.prev.rot];if(sp.ia)chp.unshift("IA");sp.found.forEach(([d,nn])=>chp.push("filtro: "+nn));
  const meio=" "+emp(sp.per.rot)+(bo?" e também ":" e nenhuma ")+emp(sp.prev.rot)+filt(sp);
  const fr=n?fmt(n)+" "+art(E,n)+(n===1?" teve ":" tiveram ")+ml+meio+": "+esc(quem(sp,rs,6))+".":"Nenhum"+(E.g==="a"?"a ":" ")+E.s+" teve "+ml+meio+".";
  return'<div class="abig">'+fmt(n)+'</div><div class="asub">'+fr+'</div><div class="amut" style="margin:-6px 0 12px">De '+tA+" "+E.p+" com "+ml+" "+esc(emp(sp.per.rot))+".</div>"+(sp.ia&&sp.entendi?'<div class="amut" style="margin:-6px 0 12px">'+esc(sp.entendi)+"</div>":"")+'<div class="achips">Entendi assim: '+chp.map(x=>"<span>"+esc(x)+"</span>").join("")+"</div>"+(n?tab2(sp,rs,curto(sp.per.rot),curto(sp.prev.rot)):"")}
 const R=calcular(sp);let h="",big="",sub="";const ml=METL[sp.met],E=sp.ent?ENT[sp.ent]:null;
 if(sp.modo==="total"){const c=R.A.total,p=R.B.total,d=c-p;big=V(sp,c);sub="Foram "+V(sp,c)+" "+ml+" "+esc(emp(sp.per.rot))+esc(filt(sp))+(sp.prev?(p||c?", "+(d>0?"+":"")+V(sp,d)+" ("+pct(c,p)+") em relação a "+V(sp,p)+" "+esc(emp(sp.prev.rot)):", sem movimento nos dois períodos"):"")+".";
  if(sp.prev){const lb=METN[sp.met]+(sp.found.length?" · "+[...new Set(sp.found.map(f=>f[1]))].join(", "):"");h='<div class="atw"><table class="at"><thead><tr><th>Indicador</th><th>'+hd(sp.per)+"</th><th>"+hd(sp.prev)+"</th><th>Variação</th></tr></thead><tbody><tr><td>"+esc(lb)+"</td><td>"+V(sp,c)+"</td><td>"+V(sp,p)+'</td><td class="'+cls(d)+'">'+(d>0?"+":"")+V(sp,d)+" · "+pct(c,p)+"</td></tr></tbody></table></div>"}}
 else if(sp.modo==="movers"){
  const pop=R.rows.filter(r=>r.c>0||r.p>0),mv=pop.filter(r=>sp.dir==="up"?r.c>r.p:r.c<r.p).sort((x,y)=>sp.dir==="up"?y.d-x.d||y.c-x.c:x.d-y.d||y.p-x.p),ig=pop.filter(r=>r.c===r.p).length,op=pop.filter(r=>sp.dir==="up"?r.c<r.p:r.c>r.p).length;
  big=fmt(mv.length);sub=(mv.length?fmt(mv.length)+" "+art(E,mv.length)+" "+(sp.dir==="up"?(mv.length===1?"aumentou":"aumentaram"):(mv.length===1?"diminuiu":"diminuíram"))+" "+ml+" "+esc(emp(sp.per.rot))+" em relação a "+esc(curto(sp.prev.rot))+esc(filt(sp))+": "+esc(mv.slice(0,6).map(r=>r.n+" ("+(r.d>0?"+":"")+V(sp,r.d)+")").join(", "))+(mv.length>6?" e mais "+(mv.length-6):"")+".":"Nenhum"+(E.g==="a"?"a ":" ")+E.s+" "+(sp.dir==="up"?"aumentou":"diminuiu")+" "+ml+" "+esc(emp(sp.per.rot))+" em relação a "+esc(curto(sp.prev.rot))+esc(filt(sp))+".")+'<div class="amut" style="margin-top:6px">De '+pop.length+" "+E.p+" com "+ml+" em algum dos dois períodos: "+ig+" ficaram iguais e "+op+" "+(sp.dir==="up"?"caíram":"subiram")+".</div>";
  h=mv.length?tabela(sp,mv):"";if(!R.A.total)h+='<div class="amut">Não há nenhum registro de '+ml+" no período atual ("+sp.per.rot+"), por isso ninguém aparece como aumento.</div>"}
 else if(sp.modo==="count"||sp.modo==="list"){
  const pos=R.rows.filter(r=>r.c>=(sp.min||1)).sort((x,y)=>y.c-x.c);big=fmt(pos.length);sub=(pos.length?fmt(pos.length)+" "+art(E,pos.length)+(pos.length===1?" teve ":" tiveram ")+ml+" "+esc(emp(sp.per.rot))+esc(filt(sp))+(sp.min>1?" (pelo menos "+sp.min+")":"")+": "+esc(quem(sp,pos,6))+".":"Nenhum"+(E.g==="a"?"a ":" ")+E.s+" teve "+ml+" "+esc(emp(sp.per.rot))+esc(filt(sp))+".");h=tabela(sp,pos,true)}
 else if(sp.modo==="rank"){
  const pos=R.rows.filter(r=>sp.asc?(r.c>0||r.p>0):r.c>=(sp.min||1)).sort((x,y)=>sp.asc?x.c-y.c:y.c-x.c).slice(0,sp.top);
  if(pos.length){big=esc(pos[0].n);sub=cap(esc(emp(sp.per.rot)))+esc(filt(sp))+", "+esc(pos[0].n)+(sp.asc?" tem o menor resultado":" lidera")+" em "+ml+" com "+V(sp,pos[0].c)+(pos.length>1?"; depois "+esc(pos.slice(1,3).map(r=>r.n+" ("+V(sp,r.c)+")").join(" e "))+(pos.length>3?" e outros":""):"")+"."}
  else{big="—";sub="Não houve "+ml+" "+esc(emp(sp.per.rot))+esc(filt(sp))+"."}h=pos.length?tabela(sp,pos):""}
 else{const rs=R.rows.filter(r=>r.c>0||r.p>0).sort((x,y)=>y.c-x.c);big=V(sp,R.A.total);sub="Foram "+V(sp,R.A.total)+" "+ml+" "+esc(emp(sp.per.rot))+esc(filt(sp))+", distribuídas por "+E.s+" na tabela.";h=tabela(sp,rs,!sp.prev)}
 if(!R.rows.length&&sp.ent&&!h)h='<div class="amut">Nenhum registro encontrado para esse recorte.</div>';
 return'<div class="abig">'+big+'</div><div class="asub">'+sub+"</div>"+chips(sp)+h}

/* ---------- interpretação por IA (opcional: precisa do ENDPOINT) ---------- */
const MET2={leads:0,oportunidades:1,visitas:2,propostas:3,fechamentos:4,vendas:5,agenciamentos:8,placas:9,vgv:"vgv"};
function ancoras(){
 const[y,mo]=ymd(ULT),ws=wkStart(ULT),pm=mo?mo-1:11,py=mo?y:y-1,meses={};
 for(let i=0;i<=mo;i++)meses[MESN[i]+" de "+y]={a:iso(monthStart(y,i)),b:iso(Math.min(monthEnd(y,i),ULT))};
 return{ultimo_dia:iso(ULT),dia_da_semana:["domingo","segunda","terça","quarta","quinta","sexta","sábado"][new Date(D0+ULT*864e5).getUTCDay()],inicio_dos_dados:iso(dIdx(2026,0,1)),
  semana_atual:{a:iso(ws),b:iso(ULT)},semana_passada:{a:iso(ws-7),b:iso(ws-1)},mes_atual:{a:iso(monthStart(y,mo)),b:iso(ULT)},mes_passado:{a:iso(monthStart(py,pm)),b:iso(monthEnd(py,pm))},ano_ate_agora:{a:iso(monthStart(y,0)),b:iso(ULT)},meses}}
function listas(){const u=k=>(C.dict[k]||[]).filter(Boolean);return{equipes:u("equipe"),lojas:u("loja"),veiculos:u("veiculo"),tipologias:u("tipo")}}
let RESTAM=null;
const uid=()=>{try{let u=localStorage.getItem("ask_uid");if(!u||!/^[A-Za-z0-9_-]{8,40}$/.test(u)){u=Array.from(crypto.getRandomValues(new Uint8Array(16)),b=>b.toString(36).padStart(2,"0")).join("").slice(0,24);localStorage.setItem("ask_uid",u)}return u}catch(_){return""}};
function restamNota(r){const n=RESTAM&&(RESTAM.usuario!=null?RESTAM.usuario:RESTAM.ip);if(n!=null&&n<=30)r.insertAdjacentHTML("beforeend",'<div class="amut">Restam '+n+(n===1?" pergunta":" perguntas")+" hoje.</div>")}
async function viaIA(t){
 const c=new AbortController(),to=setTimeout(()=>c.abort(),15000);
 try{const r=await fetch(ENDPOINT,{method:"POST",signal:c.signal,headers:{"content-type":"application/json","x-acesso":C.askToken||""},body:JSON.stringify({pergunta:t,uid:uid(),contexto:{ancoras:ancoras(),listas:listas()}})});
  const j=await r.json().catch(()=>({}));if(!r.ok||!j.spec)throw new Error(j.erro||("HTTP "+r.status));RESTAM=j.restam||null;return j.spec}
 finally{clearTimeout(to)}}
function resolver(dim,nomesPedidos){
 const L=nomes()[dim],ach=[],falt=[];
 nomesPedidos.forEach(n=>{const q=norm(n);if(!q)return;
  let m=L.filter(o=>o.q===q);if(!m.length)m=L.filter(o=>o.q.replace(/^(equipe|agencia) /,"")===q.replace(/^(equipe|agencia) /,""));
  if(!m.length){const t=q.split(" ");m=L.filter(o=>t.every(w=>(" "+o.q+" ").includes(" "+w+" ")))}
  if(!m.length)m=L.filter(o=>o.q.includes(q));
  if(m.length&&m.length<=5)m.forEach(o=>ach.push(o));else falt.push(n)});
 return{ach,falt}}
function v2ToSp(v){
 if(v.nao_suportado)return{recusa:v.nao_suportado};
 const met=MET2[v.metrica];if(met===undefined)throw new Error("métrica inválida");
 const ent=v.entidade&&ENT[v.entidade]?v.entidade:null;
 const dt=(x,nmz)=>{if(!x||!/^\d{4}-\d\d-\d\d$/.test(x.a||"")||!/^\d{4}-\d\d-\d\d$/.test(x.b||""))throw new Error("período inválido ("+nmz+")");
  let a=dIdx(+x.a.slice(0,4),+x.a.slice(5,7)-1,+x.a.slice(8,10)),b=dIdx(+x.b.slice(0,4),+x.b.slice(5,7)-1,+x.b.slice(8,10));if(b<a)[a,b]=[b,a];
  return{a,b,tipo:"x",rot:x.rotulo||br(a)+" a "+br(b)}};
 let per=dt(v.periodo,"principal"),prev=v.comparar?dt(v.comparar,"comparação"):null;
 const F={},found=[],falt=[];
 Object.keys(v.filtros||{}).forEach(d=>{if(!ENT[d]||!(v.filtros[d]||[]).length)return;const r=resolver(d,v.filtros[d]);r.ach.forEach(o=>{(F[d]=F[d]||new Set()).add(o.i);found.push([d,o.n])});falt.push(...r.falt.map(n=>d+" "+n))});
 if(falt.length)return{recusa:"Não encontrei nos dados: "+falt.join(", ")+"."};
 const sp={met,ent,F,found,assum:[],per,prev,dir:null,asc:v.ordem==="asc",top:v.top||(v.modo==="ranking"?10:10),min:v.minimo||0,ia:true,entendi:v.entendi||"",raw:""};
 const modo=(v.modo==="variacao"&&!ent)?"total":v.modo; /* comparar dois períodos sem agrupar = total com variação */
 if(modo==="total"&&v.modo==="variacao"&&!prev)throw new Error("faltou o período de comparação");
 const needEnt=["ranking","contagem","lista","variacao","conjunto"].includes(modo);
 if(needEnt&&!ent)return{recusa:"Essa pergunta precisa de uma dimensão (corretor, equipe, loja...). Diga por qual quer ver."};
 switch(modo){
  case"total":sp.modo="total";break;
  case"ranking":sp.modo="rank";break;
  case"contagem":sp.modo="count";break;
  case"lista":sp.modo="list";break;
  case"variacao":if(!prev)throw new Error("faltou o período de comparação");sp.dir=v.direcao==="aumentou"?"up":v.direcao==="diminuiu"?"down":null;sp.modo=sp.dir?"movers":"break";break;
  case"conjunto":if(!prev)throw new Error("faltou o segundo período");
   if(v.conjunto==="so_na_comparacao"){sp.per=prev;sp.prev=per;sp.modo="lost"}else if(v.conjunto==="em_ambos")sp.modo="both";else sp.modo="lost";break;
  default:throw new Error("modo inválido")}
 return sp}

/* ---------- interface ---------- */
const EX=["Quantos corretores aumentaram vendas nos últimos 7 dias?","Quais equipes mais venderam este mês?","Quantos agenciamentos tivemos em setembro?","Quais corretores diminuíram visitas esta semana?","Qual veículo trouxe mais vendas este ano?","Vendas da equipe Meta este mês vs. mês passado"];
function css(){const s=document.createElement("style");s.textContent=`
.iaw{color:var(--br);font-weight:800}
#ask{margin:0;padding:16px 20px 18px}
#ask h2{margin:0 0 4px;font-size:15px;color:var(--ink)}#ask .beta{font-size:8px}
#ask .asb{margin:0 0 12px;color:var(--mut);font-size:13px;line-height:1.5}
#ask form{display:flex;gap:10px}#ask input[type=text]{flex:1;min-width:0;padding:12px 14px;border:1px solid var(--line);border-radius:12px;font:inherit;font-size:14px;background:var(--sf);color:var(--ink)}
#ask input[type=text]:focus{outline:2px solid var(--nv);outline-offset:1px}
#ask .ex{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}#ask .ex button{font:inherit;font-size:12px;border:1px solid var(--line);background:var(--tr);color:var(--nv);border-radius:999px;padding:6px 11px;cursor:pointer}
#ask .ex button:hover{background:var(--hv)}
#ask .res{margin-top:16px;padding-top:14px;border-top:1px solid var(--line)}
#ask .abig{font-size:32px;font-weight:700;color:var(--br);line-height:1.15}#ask .asub{color:var(--ink);font-size:13.5px;margin:2px 0 12px;line-height:1.5}
#ask .atw{overflow-x:auto}#ask table.at{border-collapse:collapse;width:100%;max-width:760px;font-size:13px}
#ask .at th{text-align:left;color:var(--mut);font-weight:600;font-size:12px;padding:6px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
#ask .at td{padding:7px 10px;border-bottom:1px solid var(--line);color:var(--ink)}#ask .at td.pos,#ask .at td.neg{background:none}#ask .at td.pos{color:var(--pos);font-weight:600}#ask .at td.neg{color:var(--neg);font-weight:600}
#ask .at th:not(:first-child),#ask .at td:not(:first-child){text-align:right;white-space:nowrap}
#ask .achips{margin:0 0 14px;color:var(--mut);font-size:12px;line-height:2}#ask .achips span{display:inline-block;margin:0 6px 0 0;padding:1px 9px;border-radius:999px;background:var(--tr);color:var(--nv)}
#ask .at th .ad{display:block;font-weight:400;font-size:11px;opacity:.85;margin-top:1px}
#ask .amut{color:var(--mut);font-size:12px;margin-top:8px}
@media(max-width:600px){#ask{padding:14px}#ask form{flex-direction:column}}`;document.head.appendChild(s)}
function ui(){
 const root=document.getElementById("askroot"),nav=document.querySelector(".tabs");if(document.getElementById("ask")||(!root&&!nav))return;css();
 const d=document.createElement("div");d.id="ask";d.className="panel";
 d.innerHTML='<h2>'+esc(NAME).replace("IA",'<span class="iaw">IA</span>')+'<span class="beta">BETA</span></h2><p class="asb">O assistente de dados da CreativeImob. Pergunte em português sobre o funil, vendas, agenciamentos ou placas. A resposta é calculada nos dados do próprio dashboard e mostra como a pergunta foi entendida.</p><form id="askf" autocomplete="off"><input type="text" id="askq" aria-label="Pergunta" placeholder="Carregando dados..." disabled><button class="gh" type="submit" id="askb" disabled>Perguntar</button></form><div class="ex" id="askex"></div><div class="res" id="askr" hidden aria-live="polite"></div>';
 if(root)root.appendChild(d);else nav.parentNode.insertBefore(d,nav);
 const tb=document.getElementById("tab-ask"),pn=document.getElementById("panel-ask"),G=i=>document.getElementById(i);
 if(tb&&pn){tb.addEventListener("click",()=>{document.querySelectorAll(".sbx .tabs button").forEach(x=>x.setAttribute("aria-selected","false"));const mp=G("tab-mp");if(mp)mp.setAttribute("aria-selected","false");
   document.querySelectorAll("[role=tabpanel]").forEach(p=>p.hidden=p!==pn);document.querySelectorAll(".sbg").forEach(g=>{g.classList.remove("op");const b=g.querySelector(".sbh");if(b)b.setAttribute("aria-expanded","false")});
   tb.setAttribute("aria-selected","true");const cr=G("crb");if(cr)cr.innerHTML=esc(NAME)+' <span>›</span> <b>Pergunte aos dados</b>';
   if(G("hctl"))G("hctl").hidden=true;if(G("gfb"))G("gfb").hidden=true;G("sbx").classList.remove("open");G("sbov").classList.remove("open");window.scrollTo({top:0})});
  document.querySelectorAll(".sbx .tabs button,#tab-mp").forEach(b=>b.addEventListener("click",()=>tb.setAttribute("aria-selected","false")))}
 const ex=document.getElementById("askex");EX.forEach(t=>{const b=document.createElement("button");b.type="button";b.textContent=t;b.onclick=()=>{document.getElementById("askq").value=t;run(t)};ex.appendChild(b)});
 document.getElementById("askf").onsubmit=e=>{e.preventDefault();run(document.getElementById("askq").value)}}
let seq=0;
function mostrar(sp,r){r.innerHTML=responder(sp)}
async function run(t){
 const r=document.getElementById("askr"),meu=++seq;r.hidden=false;
 const regras=()=>{const sp=interpretar(t);
  if(sp&&sp.modo==="nao_entendi"){r.innerHTML='<div class="asub">Entendi que há uma condição de negação ("não", "sem"), mas não consegui ler os dois períodos. Tente: "quantos corretores tiveram vendas mês passado e não têm este mês?" (com os dois períodos explícitos).</div>';return}
  if(!sp||(!sp.ent&&metrica(norm(t))===null&&!periodo(norm(t))&&!/\b(total|quanto|quantas|quantos)\b/.test(norm(t)))){r.innerHTML='<div class="asub">Não consegui entender essa pergunta. Tente algo como as sugestões acima: diga a métrica (vendas, visitas, agenciamentos...), o período (últimos 7 dias, este mês, setembro...) e, se quiser, por corretor, equipe ou loja.</div>';return}
  mostrar(sp,r)};
 try{
  if(ENDPOINT&&C.askToken){
   r.innerHTML='<div class="asub">Interpretando a pergunta...</div>';let v2;
   try{v2=await viaIA(t)}catch(e){if(meu!==seq)return;regras();r.insertAdjacentHTML("beforeend",'<div class="amut">Sem resposta da IA ('+esc(e.message||e)+"): usei a interpretação por regras.</div>");return}
   if(meu!==seq)return;
   if(v2&&v2.comparar&&v2.entidade&&!["conjunto","variacao"].includes(v2.modo)&&/\b(nao|sem|nenhum\w*|nunca)\b/.test(norm(t))){v2.modo="conjunto";v2.conjunto=v2.conjunto||"so_no_periodo"}
   let sp;try{sp=v2ToSp(v2)}catch(e){regras();r.insertAdjacentHTML("beforeend",'<div class="amut">A IA devolveu uma consulta inválida ('+esc(e.message)+"): usei a interpretação por regras.</div>");return}
   if(sp.recusa){const rg=interpretar(t);if(rg&&rg.modo!=="nao_entendi"&&rg.ent&&ENT[rg.ent].im){mostrar(rg,r);return}r.innerHTML='<div class="asub">'+esc(sp.recusa)+"</div>";return}
   mostrar(sp,r);restamNota(r);return}
  regras()}
 catch(e){console.error(e);r.innerHTML='<div class="asub">Não consegui calcular essa pergunta ('+esc(e.message||e)+").</div>"}}
function start(){
 ui();let n=0;const t=setInterval(()=>{if(window.__cuboInfo&&window.__cuboInfo.rows){clearInterval(t);C=window.__cuboInfo;{const tb=document.getElementById("tab-ask");if(tb&&ENDPOINT&&C.askToken)tb.hidden=false}ULT=dIdx(+C.ultimo.slice(0,4),+C.ultimo.slice(5,7)-1,+C.ultimo.slice(8,10));
  const i=document.getElementById("askq"),b=document.getElementById("askb");if(i){i.disabled=false;b.disabled=false;i.placeholder="Ex.: quantos corretores aumentaram vendas nos últimos 7 dias?"}}else if(++n>1200)clearInterval(t)},150)}
window.__ask={interpretar,calcular,responder,v2ToSp,init:()=>C};
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",start);else start();
})();
