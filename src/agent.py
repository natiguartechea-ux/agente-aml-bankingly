"""
Agente de triage AML.

Lo que decide el modelo: interpretar la alerta + contexto del cliente,
redactar evidencia y justificación, y recomendar UNA acción entre
{cerrar, escalar_sar, pedir_info, bloquear_cuenta}.

Lo que el modelo NO puede hacer: ejecutar nada. Su única "tool" disponible
(proponer_resolucion_alerta) no tiene efectos secundarios, solo devuelve
datos que después pasan por src/gate.py.

Modo --mock: heurística simple basada en reglas, para poder correr y probar
todo el flujo (incluyendo evals) sin necesitar ANTHROPIC_API_KEY. Útil para
demo rápida y para CI. El modo real usa la API de Claude con tool use.
"""
import os
import json
from src.models import PROPUESTA_SCHEMA


def construir_contexto(alerta: dict, cliente: dict) -> str:
    return f"""
Sos un analista de investigación AML junior. Tu trabajo es armar un caso de
investigación para una alerta, NO resolverla vos mismo — un analista humano
tomará la decisión final en base a tu propuesta.

DATOS DEL CLIENTE:
{json.dumps(cliente, indent=2, ensure_ascii=False)}

ALERTA DISPARADA:
- Regla: {alerta['regla_disparada']}
- Descripción: {alerta['descripcion_regla']}

TRANSACCIONES RELEVANTES:
{json.dumps(alerta['transacciones'], indent=2, ensure_ascii=False)}

Analizá si la actividad es coherente con el perfil declarado del cliente y su
historial. Si la evidencia es clara, proponé cerrar o escalar_sar. Si falta
información para decidir con confianza razonable, proponé pedir_info en vez
de forzar una decisión. Si la evidencia es de alta gravedad — por ejemplo un
patrón de estructuración reincidente (el cliente ya tiene alertas previas
por el mismo tipo de patrón) u otra señal de riesgo inminente que amerite
congelar la cuenta mientras avanza la investigación — proponé
bloquear_cuenta en vez de escalar_sar; es una recomendación más severa, no
un reemplazo del reporte. Fundamentá con evidencia concreta, no opiniones
genéricas. Usá la tool proponer_resolucion_alerta para tu respuesta.
""".strip()


def llamar_agente_real(alerta: dict, cliente: dict) -> dict:
    import anthropic

    client = anthropic.Anthropic()  # usa ANTHROPIC_API_KEY del entorno
    contexto = construir_contexto(alerta, cliente)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        tools=[PROPUESTA_SCHEMA],
        tool_choice={"type": "tool", "name": "proponer_resolucion_alerta"},
        messages=[{"role": "user", "content": contexto}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "proponer_resolucion_alerta":
            return block.input

    raise RuntimeError("El modelo no devolvió una propuesta estructurada (revisar prompt/API).")


def llamar_agente_mock(alerta: dict, cliente: dict) -> dict:
    """
    Heurística simple, solo para poder demostrar el flujo end-to-end y correr
    evals sin API key. Deliberadamente simple: no es el "agente real", es un
    doble de prueba.
    """
    evidencia = [f"Regla disparada: {alerta['descripcion_regla']}"]
    monto_max = max(t["monto_usd"] for t in alerta["transacciones"])
    n_tx = len(alerta["transacciones"])

    ingreso_declarado = 0
    for tok in cliente["perfil_declarado"].split():
        if tok.isdigit():
            ingreso_declarado = int(tok)

    ratio = monto_max / ingreso_declarado if ingreso_declarado else 999
    evidencia.append(f"Monto máximo de transacción USD {monto_max} vs. ingreso/facturación declarado ~{ingreso_declarado}")

    if alerta["regla_disparada"] == "estructuracion" and cliente["alertas_previas"] >= 2:
        accion, confianza = "bloquear_cuenta", 0.9
        evidencia.append(
            f"Patrón de estructuración reincidente: cliente ya acumula {cliente['alertas_previas']} "
            f"alertas previas con el mismo patrón de fraccionamiento — alta gravedad, amerita bloqueo "
            f"preventivo de cuenta además de reporte"
        )
    elif alerta["regla_disparada"] == "estructuracion":
        accion, confianza = "escalar_sar", 0.85
        evidencia.append(f"{n_tx} transacciones justo debajo de umbral de reporte en ventana corta")
    elif cliente["alertas_previas"] >= 2 and ratio > 5:
        accion, confianza = "escalar_sar", 0.7
        evidencia.append(f"Cliente con {cliente['alertas_previas']} alertas previas y monto muy por encima de su perfil")
    elif ratio > 3 and cliente["antiguedad_meses"] < 12:
        accion, confianza = "pedir_info", 0.55
        evidencia.append("Monto atípico en cliente relativamente nuevo, sin evidencia suficiente para decidir")
    elif alerta["regla_disparada"] == "velocity" and ratio < 2:
        accion, confianza = "cerrar", 0.75
        evidencia.append("Montos individuales bajos, coherentes con perfil, sin señales adicionales de riesgo")
    else:
        accion, confianza = "pedir_info", 0.5
        evidencia.append("Evidencia mixta, no concluyente con la heurística mock")

    return {
        "accion_propuesta": accion,
        "confianza": confianza,
        "evidencia": evidencia,
        "justificacion": f"[MOCK] Basado en regla '{alerta['regla_disparada']}' y ratio monto/perfil ~{ratio:.1f}x.",
        "factores_de_riesgo_identificados": [
            f"antigüedad_cliente_meses={cliente['antiguedad_meses']}",
            f"alertas_previas={cliente['alertas_previas']}",
        ],
    }


def proponer(alerta: dict, cliente: dict, modo: str = "mock") -> dict:
    if modo == "real":
        return llamar_agente_real(alerta, cliente)
    return llamar_agente_mock(alerta, cliente)
