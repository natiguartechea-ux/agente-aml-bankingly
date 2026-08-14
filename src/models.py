"""
Modelos de datos del prototipo.

La pieza clave acá es PROPUESTA_SCHEMA: es el contrato estructurado que el
modelo debe respetar. El modelo NUNCA devuelve una función ejecutable,
siempre devuelve datos que pasan por el gate de código antes de convertirse
en un efecto real. Ver src/gate.py.
"""

ACCIONES_VALIDAS = {"cerrar", "escalar_sar", "pedir_info", "bloquear_cuenta"}

# Tool schema que se le pasa a la API de Claude (tool use / structured output).
# El modelo está forzado a devolver exactamente esta forma.
PROPUESTA_SCHEMA = {
    "name": "proponer_resolucion_alerta",
    "description": (
        "Propone una resolución para una alerta AML. Esto NO ejecuta ninguna "
        "acción sobre el sistema: solo registra una propuesta que un analista "
        "humano debe aprobar, rechazar o editar antes de que ocurra cualquier "
        "efecto."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "accion_propuesta": {
                "type": "string",
                "enum": list(ACCIONES_VALIDAS),
                "description": "cerrar = sin indicios suficientes; escalar_sar = evidencia de posible actividad sospechosa, debe reportarse; pedir_info = evidencia insuficiente para decidir, requiere más contexto antes de resolver; bloquear_cuenta = evidencia de alta gravedad (p. ej. patrón de estructuración reincidente, fraude en curso, riesgo inminente) que amerita congelar la cuenta de forma preventiva además de reportar",
            },
            "confianza": {
                "type": "number",
                "description": "Confianza del modelo en su propia recomendación, 0.0 a 1.0",
            },
            "evidencia": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Lista de hechos concretos del caso (no opiniones) que sustentan la recomendación. Mínimo 2 items.",
            },
            "justificacion": {
                "type": "string",
                "description": "Resumen breve de investigación en lenguaje natural para el analista",
            },
            "factores_de_riesgo_identificados": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Factores que aumentan o disminuyen el riesgo (perfil vs. transacción, antigüedad, alertas previas, etc.)",
            },
        },
        "required": ["accion_propuesta", "confianza", "evidencia", "justificacion", "factores_de_riesgo_identificados"],
    },
}
