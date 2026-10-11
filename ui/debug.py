"""Depuración visual del layout, activable desde la UI (interruptor «Bordes» en la barra superior) o con ?layout_debug=1.

Con el interruptor activo:
- rosa continuo = isla · azul discontinuo = columna/lista con scroll propio · gris punteado = columna de Streamlit;
- rojo = texto desbordado o cortado, o controles que se solapan (se marcan solos, cada segundo);
- ámbar discontinuo = un contenedor que scrollea por dentro (solo debería ocurrir en la lista de la cola);
- un contador abajo a la derecha resume: overflow · solapes · scrolls internos · scroll de página · tamaño de ventana.
Los contornos no cambian tamaños ni posiciones. Al apagarlo se elimina todo (estilo, contador, marcas y temporizador).
"""
import json

import streamlit as st

_CSS = """
[class*="st-key-isla"] { outline:2px solid #ff2d95 !important; outline-offset:-2px; }
[class*="st-key-col_"], [class*="st-key-lista_"] { outline:2px dashed #00a3ff !important; outline-offset:-3px; }
[data-testid="stColumn"] { outline:1px dotted #8a8a8a !important; outline-offset:-1px; }
[data-dbg="overflow"], [data-dbg="solape"] { outline:3px solid #ff0000 !important; outline-offset:-1px; background-color:rgba(255,0,0,.16) !important; }
[data-dbg="scroll"] { outline:3px dashed #ffb000 !important; outline-offset:-3px; }
#dbg-badge { position:fixed; right:8px; bottom:8px; z-index:2147483647; background:#111; color:#fff; font:12px/1.4 ui-monospace,Menlo,monospace;
  padding:6px 10px; border-radius:8px; opacity:.94; pointer-events:none; max-width:460px; white-space:pre-wrap; }
"""

_JS = """<!doctype html><meta charset="utf-8"><script>
(function () {
  var on = __ON__, P = window.parent, D = P.document;
  function limpiar() {
    var s = D.getElementById('dbg-style'); if (s) s.remove();
    var b = D.getElementById('dbg-badge'); if (b) b.remove();
    if (P.__dbgT) { P.clearInterval(P.__dbgT); P.__dbgT = null; }
    D.querySelectorAll('[data-dbg]').forEach(function (e) { e.removeAttribute('data-dbg'); });
  }
  try { limpiar(); } catch (e) { return; }
  if (!on) return;
  var st = D.createElement('style'); st.id = 'dbg-style'; st.textContent = __CSS__; D.head.appendChild(st);
  var badge = D.createElement('div'); badge.id = 'dbg-badge'; D.body.appendChild(badge);
  function visible(e) { var b = e.getBoundingClientRect(), c = P.getComputedStyle(e); return b.width > 1 && b.height > 1 && c.visibility !== 'hidden' && c.display !== 'none'; }
  function escanear() {
    var main = D.querySelector('[data-testid="stMain"]'); if (!main) return;
    D.querySelectorAll('[data-dbg]').forEach(function (e) { e.removeAttribute('data-dbg'); });
    var overflow = 0, solapes = 0, internos = 0, detalle = [];
    // texto desbordado o cortado
    main.querySelectorAll('p, span, div, button, a, label, summary').forEach(function (e) {
      if (!visible(e) || e.closest('iframe') || e.closest('[data-testid="stDataFrame"]') || e.closest('[role="grid"]') || e.closest('[data-baseweb="popover"]')) return;
      var c = P.getComputedStyle(e);
      if (c.textOverflow === 'ellipsis' || /(auto|scroll)/.test(c.overflowX) || c.webkitLineClamp !== 'none' && c.webkitLineClamp) return;
      if (e.scrollWidth > e.clientWidth + 1 && e.children.length < 6 && e.textContent.trim()) { e.setAttribute('data-dbg', 'overflow'); overflow++; detalle.push('ovf: ' + e.textContent.trim().slice(0, 24)); }
    });
    // contenedores con scroll interno
    D.querySelectorAll('[class*="st-key-col_"], [class*="st-key-lista_"], [role="tabpanel"]').forEach(function (e) {
      if (visible(e) && e.scrollHeight > e.clientHeight + 1) { if (!e.hasAttribute('data-dbg')) e.setAttribute('data-dbg', 'scroll'); if (!/st-key-lista_/.test(e.className)) { internos++; detalle.push('scroll: +' + (e.scrollHeight - e.clientHeight) + 'px ' + (String(e.className).match(/st-key-[\\w-]+/) || [''])[0].replace('st-key-', '')); } }
    });
    // controles solapados
    var cand = Array.prototype.filter.call(main.querySelectorAll('button, a, input, textarea, [role="tab"], [data-baseweb="select"]'), function (e) {
      var b = e.getBoundingClientRect(); return visible(e) && b.bottom > 0 && b.top < P.innerHeight; });
    for (var i = 0; i < cand.length; i++) for (var j = i + 1; j < cand.length; j++) {
      var a = cand[i], b2 = cand[j]; if (a.contains(b2) || b2.contains(a)) continue;
      var A = a.getBoundingClientRect(), B = b2.getBoundingClientRect();
      if (Math.min(A.right, B.right) - Math.max(A.left, B.left) > 2 && Math.min(A.bottom, B.bottom) - Math.max(A.top, B.top) > 2) {
        a.setAttribute('data-dbg', 'solape'); b2.setAttribute('data-dbg', 'solape'); solapes++; detalle.push('solape: ' + a.textContent.trim().slice(0, 12) + ' × ' + b2.textContent.trim().slice(0, 12)); }
    }
    var pagina = main.scrollHeight > main.clientHeight + 1 || D.documentElement.scrollHeight > D.documentElement.clientHeight + 1;
    badge.textContent = 'overflow ' + overflow + ' · solapes ' + solapes + ' · scroll interno ' + internos + ' · página ' + (pagina ? 'SCROLL' : 'ok') +
      '\\n' + P.innerWidth + '×' + P.innerHeight + (detalle.length ? '\\n' + detalle.slice(0, 5).join('\\n') : '');
    badge.style.background = (overflow || solapes || pagina) ? '#b00020' : '#111';
  }
  escanear(); P.__dbgT = P.setInterval(escanear, 1000);
})();
</script>"""


def activo() -> bool:
    return bool(st.session_state.get("debug_bordes")) or st.query_params.get("layout_debug") == "1"


def html(on: bool) -> str:
    """Documento del iframe invisible que enciende/apaga la depuración. El CSS viaja como literal JSON (sin posibilidad de cerrar el script)."""
    css = json.dumps(_CSS).replace("<", "\\u003c")
    return _JS.replace("__ON__", "true" if on else "false").replace("__CSS__", css)


def interruptor() -> None:
    st.toggle("Bordes", key="debug_bordes", help="Herramienta de diseño: dibuja los límites de islas y columnas y marca en rojo texto desbordado y controles solapados.")


def inyectar() -> None:
    st.iframe(html(activo()), height=1)
