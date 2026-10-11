"""Next Best Action: recomendación determinista del siguiente paso. La herramienta nunca ejecuta la acción."""
from datetime import date

from . import contacto
from .db import CERRADOS

ROTULOS = {"email": "Enviar correo", "telefono": "Llamar", "whatsapp_or_copy": "WhatsApp o copiar mensaje", "manual_review": "Revisar a mano",
           "follow_up": "Dar seguimiento", "skip": "Saltar", "discard": "Descartar"}
FIT_MIN_ACCION = 50
_NOMBRES_GENERICOS = {"bodega", "taller", "ferreteria", "abarrotes", "comercializadora", "distribuidora", "transportes", "construcciones", "servicios"}


def _nombre_generico(nombre: str) -> bool:
    toks = [t for t in nombre.lower().split() if t not in ("de", "del", "la", "el", "los", "las", "y")]
    return len(toks) <= 1 and (not toks or toks[0] in _NOMBRES_GENERICOS)


def recommend_next_action(r: dict, fit_score: int, tiene_senal_web: bool, hoy: date | None = None) -> dict:
    hoy = hoy or date.today()
    estado = r.get("estado") or "nuevo"
    email = contacto.email_valido(r.get("correo_web") or "") or contacto.email_valido(r.get("correo") or "")
    tel = bool(contacto.telefono_mx(r.get("telefono") or "") or contacto.telefono_mx(r.get("whatsapp") or ""))
    alternativas = ["whatsapp_or_copy"] if tel else []

    def res(accion, razon, conf, alt=None):
        return {"action": accion, "reason": razon, "confidence": conf, "alternativas": alt if alt is not None else alternativas}

    if estado in CERRADOS:
        return res("skip", f"Prospecto cerrado ({estado}).", "alta", [])
    due = r.get("proximo_seguimiento") and str(r["proximo_seguimiento"]) <= hoy.isoformat()
    if estado == "contactado":
        if due:
            return res("follow_up", f"Seguimiento vencido (D+{ {1: 3, 2: 7, 3: 14}.get(int(r.get('toques') or 1), '?') }).", "alta")
        return res("skip", f"En secuencia; próximo seguimiento {r.get('proximo_seguimiento')}.", "alta", [])
    if estado in ("respondio", "respuesta_positiva", "reunion", "propuesta"):
        return res("manual_review", "Hay conversación abierta: contesta manualmente, sin mensajes automáticos.", "alta", [])

    if r.get("possible_chain"):
        return res("manual_review", f"Posible grupo/cadena ({r.get('group_reason') or 'sin motivo'}): valida si decide localmente.", "media")
    if r.get("giro") == "Otro":
        return res("manual_review", "SCIAN poco claro: confirma que el giro encaja.", "media")
    if _nombre_generico(r.get("nombre") or ""):
        return res("manual_review", "Nombre genérico: confirma que es la empresa correcta.", "baja")
    if not email and not tel:
        if fit_score >= FIT_MIN_ACCION:
            return res("manual_review", "Fit alto pero sin canal de contacto claro: búscalo en su sitio o redes.", "media", [])
        return res("skip", "Sin canal de contacto y fit bajo: datos insuficientes.", "media", [])
    if fit_score < FIT_MIN_ACCION:
        return res("skip", f"Fit {fit_score} por debajo de {FIT_MIN_ACCION}: no conviene gastar el contacto de hoy.", "media")
    if email:
        razon = "Email válido + fit alto" + (" + contexto web concreto" if tiene_senal_web else "")
        return res("email", razon, "alta" if tiene_senal_web else "media")
    return res("telefono", "Teléfono disponible, fit alto y sin email. La herramienta no llama por ti.", "media")
