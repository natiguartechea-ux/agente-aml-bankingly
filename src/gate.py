"""
Gate de aprobación humana.

Regla de diseño del ejercicio: "toda acción con efectos debe ser propuesta
por el agente y aprobada por el analista humano antes de ejecutarse, con ese
control garantizado por el código, no por el prompt".

Cómo se garantiza acá:
  1. El modelo (src/agent.py) SOLO tiene acceso a la tool
     `proponer_resolucion_alerta`, que no tiene ningún efecto. No existe ninguna tool `cerrar_alerta()` ni `marcar_sar()`
     expuesta al modelo.
  2. validar_propuesta() rechaza cualquier propuesta que no cumpla el schema
     mínimo ANTES de que el analista la
     vea. 
  3. ejecutar_decision() es la ÚNICA función de todo el sistema que puede
     mutar el estado de una alerta a 'resuelta'. Requiere un `decision`
     explícito que en el flujo real solo puede originarse en la interacción
     con el analista humano (src/cli.py). El agente no puede invocarla.
"""
from src import storage


class PropuestaInvalida(Exception):
    pass


def validar_propuesta(propuesta: dict) -> None:
    from src.models import ACCIONES_VALIDAS

    if propuesta.get("accion_propuesta") not in ACCIONES_VALIDAS:
        raise PropuestaInvalida(f"acción propuesta inválida: {propuesta.get('accion_propuesta')}")

    evidencia = propuesta.get("evidencia") or []
    if len(evidencia) < 2:
        raise PropuestaInvalida("la propuesta debe incluir al menos 2 items de evidencia concreta")

    confianza = propuesta.get("confianza")
    if not isinstance(confianza, (int, float)) or not (0.0 <= confianza <= 1.0):
        raise PropuestaInvalida("confianza debe ser un número entre 0.0 y 1.0")

    if not propuesta.get("justificacion", "").strip():
        raise PropuestaInvalida("falta justificación")


def encolar_propuesta(alerta_id: str, propuesta: dict, modo: str = "real") -> None:
    """Valida y deja la propuesta en estado 'pendiente_aprobacion'. No ejecuta nada."""
    validar_propuesta(propuesta)
    storage.guardar_propuesta(alerta_id, propuesta, modo)


def ejecutar_decision(alerta_id: str, decision: str, accion_final: str,
                       accion_propuesta_original: str, analista: str, comentario: str = "") -> None:
    """
    Único punto de ejecución de efectos reales. Se llama exclusivamente desde
    el flujo de interacción humana (cli.py), nunca desde agent.py.
    """
    if decision not in {"aprobada", "rechazada", "editada"}:
        raise ValueError("decisión debe ser aprobada, rechazada o editada")
    storage.registrar_decision(alerta_id, decision, accion_final, accion_propuesta_original, analista, comentario)
    print(f"[GATE] Efecto ejecutado sobre {alerta_id}: acción final = '{accion_final}' "
          f"(decisión humana: {decision}, analista: {analista})")
