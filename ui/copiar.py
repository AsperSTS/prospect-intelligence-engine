"""Fila de botones de un clic: copiar al portapapeles y abrir enlaces (Gmail/WhatsApp). Nunca envía nada por ti.

Un solo iframe por fila. Los textos viajan como JSON (con '<' escapado) y los botones se crean con textContent:
ningún texto externo se interpreta como HTML ni puede cerrar el <script>.
Los estados (hover, presionado, foco, deshabilitado) son los mismos que en el resto del panel (ver ui/theme.py).
"""
import json
from urllib.parse import urlparse

import streamlit as st

ESQUEMAS_OK = {"https", "http", "mailto"}

_HTML = """<!doctype html><meta charset="utf-8"><style>
:root{color-scheme:__SCHEME__; --txt2:#6E6E73; --txt:#1D1D1F; --relleno:#F2F2F7; --velo:rgba(0,0,0,.05); --velo2:rgba(0,0,0,.10); --acento:#0B63CE; --acento-txt:#0B63CE; --ok:#1B7F3B;}
__MODO__
*{box-sizing:border-box}
body{margin:0;font:600 14px/1.5 -apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",system-ui,sans-serif;color:var(--txt);background:transparent}
.f{display:flex;gap:8px;flex-wrap:wrap}
.l{align-self:center;flex:none;color:var(--txt2);font-size:12px;font-weight:600}
.b{flex:1 1 0;min-width:0;height:36px;padding:0 8px;border-radius:8px;border:1px solid transparent;background-color:var(--relleno);color:var(--txt);
   font:inherit;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;text-decoration:none;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
   transition:background-image .14s ease,transform .14s ease}
.b:hover{background-image:linear-gradient(var(--velo),var(--velo))}
.b:active{background-image:linear-gradient(var(--velo2),var(--velo2));transform:scale(.98)}
.b:focus-visible{outline:2px solid var(--acento-txt);outline-offset:2px}
.b.p{background-color:var(--acento);color:#fff} .b.p:hover{background-image:linear-gradient(rgba(0,0,0,.12),rgba(0,0,0,.12))} .b.p:active{background-image:linear-gradient(rgba(0,0,0,.24),rgba(0,0,0,.24))}
.b.ok{background-color:color-mix(in srgb,var(--ok) 16%,transparent);color:var(--ok)}
@media (max-width:340px){.l{display:none}}
@media (prefers-reduced-motion:reduce){.b{transition:none}.b:active{transform:none}}
</style><div class="f" id="f" role="group" aria-label="Copiar y abrir"></div><script>
const items=__ITEMS__, f=document.getElementById('f');
async function copiar(t){try{await navigator.clipboard.writeText(t);return true}catch(e){
  const a=document.createElement('textarea');a.value=t;a.style.position='fixed';a.style.opacity='0';document.body.appendChild(a);a.select();
  let ok=false;try{ok=document.execCommand('copy')}catch(_){} a.remove();return ok}}
for(const it of items){
  let el;
  if(it.etiqueta){el=document.createElement('span');el.className='l';el.textContent=it.etiqueta;f.appendChild(el);continue}
  if(it.url){el=document.createElement('a');el.href=it.url;el.target='_blank';el.rel='noopener noreferrer';}
  else{el=document.createElement('button');el.type='button';el.onclick=async()=>{const ok=await copiar(it.texto);
    const antes=it.label;el.textContent=ok?'Copiado':'No se pudo copiar';if(ok)el.classList.add('ok');setTimeout(()=>{el.textContent=antes;el.classList.remove('ok')},1400)}}
  el.className='b'+(it.primary?' p':'');el.textContent=it.label;if(it.titulo)el.title=it.titulo;f.appendChild(el)}
</script>"""

_OSC = "--txt:#F5F5F7;--txt2:#A1A1A6;--relleno:#2C2C2E;--velo:rgba(255,255,255,.07);--velo2:rgba(255,255,255,.13);--acento-txt:#64A8FF;--ok:#30D158;"
_MODO = {"light": "", "dark": ":root{" + _OSC + "}", "auto": "@media (prefers-color-scheme:dark){:root{" + _OSC + "}}"}


def _seguro(url: str) -> bool:
    return urlparse(url).scheme in ESQUEMAS_OK


def html(items: list[dict], modo: str = "auto") -> str:
    """items: {'etiqueta'} (texto fijo), {'label', 'texto'} para copiar o {'label', 'url'} para abrir; opcional 'primary' y 'titulo'. URLs con esquema no permitido se descartan."""
    limpios = [i for i in items if i.get("etiqueta") or i.get("texto") or (i.get("url") and _seguro(i["url"]))]
    datos = json.dumps(limpios, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    esquema = {"light": "light", "dark": "dark"}.get(modo, "light dark")   # debe coincidir con el de la página o el navegador pinta fondo opaco
    return _HTML.replace("__SCHEME__", esquema).replace("__MODO__", _MODO.get(modo, _MODO["auto"])).replace("__ITEMS__", datos)


def fila(items: list[dict], modo: str = "auto") -> None:
    st.iframe(html(items, modo), height=40)   # una sola fila de 40 px (+4); st.iframe "content" no baja de 150 px
