function askPw(msg){return new Promise(ok=>{
const o=document.createElement("div");o.id="lgx";
let s=11;const r=()=>(s=(s*16807)%2147483647)/2147483647,A=[];
for(let i=0;i<9;i++){const w=44+r()*36,h=90+r()*150+(i==4?80:0),a=.06+r()*.07;A.push({w,h,a})}
let x=(640-A.reduce((t,q)=>t+q.w,0)-8*(A.length-1))/2,b="";
A.forEach((q,i)=>{b+=`<rect class="lgb" x="${x.toFixed(1)}" y="${300-q.h}" width="${q.w.toFixed(1)}" height="${q.h.toFixed(1)}" fill="rgba(255,255,255,${q.a.toFixed(3)})" stroke="rgba(255,255,255,.38)" stroke-width="1" style="animation-delay:${(.25+i*.34).toFixed(2)}s"/>`;x+=q.w+8});
o.innerHTML=`<style>
#lgx{position:fixed;inset:0;z-index:99;display:grid;grid-template-columns:1.15fr 1fr;background:#fbfbfd;font-family:Manrope,system-ui,sans-serif;color:#1b2142}
#lgx .lgv{position:relative;overflow:hidden;background:linear-gradient(160deg,#5a0f21 0%,#6e1428 38%,#2b377a 100%)}
#lgx .lgl{position:absolute;left:50%;top:16%;width:min(290px,60%);aspect-ratio:1312/972;margin-left:calc(min(290px,60%)/-2);background:url(login-logo.png) center/contain no-repeat;animation:lgf 1.3s .85s both}
#lgx svg{position:absolute;left:0;right:0;bottom:0;width:100%;height:44%}
#lgx .lgb{transform-box:fill-box;transform-origin:bottom;transform:scaleY(0);animation:lgu 1.2s cubic-bezier(.2,.7,.2,1) forwards}
#lgx .lgs{position:absolute;top:0;bottom:0;width:30%;left:0;background:linear-gradient(100deg,transparent,rgba(255,255,255,.07),transparent);animation:lgh 9s 3s infinite}
#lgx .lgr{position:relative;display:flex;flex-direction:column;justify-content:center;padding:0 12%}
#lgx h3{font:600 34px Sora,system-ui,sans-serif;margin:0 0 6px}
#lgx .lgp{margin:0 0 28px;color:#6b7090;font-size:14px;line-height:1.5}
#lgx label{font-size:12px;font-weight:600;color:#6b7090;margin-bottom:6px;display:block}
#lgx input{width:100%;height:48px;border:1px solid #dfe2ee;border-radius:12px;background:#fff;padding:0 14px;font:inherit;color:#1b2142;margin-bottom:16px;box-sizing:border-box;outline:0}
#lgx input:focus{border-color:#8a1f33;box-shadow:0 0 0 3px rgba(138,31,51,.12)}
#lgx button{width:100%;height:48px;border:0;border-radius:12px;background:#6e1428;color:#fff;font:600 14px Manrope,system-ui,sans-serif;cursor:pointer}
#lgx button:hover{background:#7d1830}
#lgx .lge{color:#b3342a;font-size:13px;margin:-4px 0 14px}
#lgx .lgf{position:absolute;left:0;right:0;bottom:22px;display:flex;align-items:center;justify-content:center;gap:8px;font-size:11px;font-weight:600;letter-spacing:.22em;color:#6b7090}
#lgx .lgf img{width:20px;height:20px;border-radius:5px}
@keyframes lgu{from{transform:scaleY(0)}to{transform:scaleY(1)}}
@keyframes lgf{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
@keyframes lgh{0%,70%{transform:translateX(-120%)}100%{transform:translateX(220%)}}
@media(max-width:820px){#lgx{grid-template-columns:1fr;grid-template-rows:42% 1fr}#lgx .lgl{width:165px;margin-left:-82px;top:18%}#lgx svg{height:40%}#lgx .lgr{justify-content:flex-start;padding:44px 28px 80px}}
@media(prefers-reduced-motion:reduce){#lgx *{animation-duration:.01s!important;animation-delay:0s!important}}
</style>
<div class="lgv"><div class="lgl"></div><svg viewBox="0 0 640 300" preserveAspectRatio="xMidYMax slice" aria-hidden="true">${b}</svg><div class="lgs"></div></div>
<form id="pwf" class="lgr"><h3>Bem-vindo</h3><p class="lgp">Digite a senha para acessar o dashboard.</p>${msg&&msg!=="Digite a senha para abrir."?`<div class="lge" role="alert">${msg}</div>`:""}<label for="pw">Senha</label><input id="pw" type="password" autocomplete="current-password"><button type="submit">Entrar</button><div class="lgf"><img src="apple-touch-icon.png" alt="">CREATIVEIMOB</div></form>`;
document.body.appendChild(o);document.getElementById("pw").focus();
document.getElementById("pwf").onsubmit=e=>{e.preventDefault();const v=document.getElementById("pw").value;o.remove();ok(v)}})}
