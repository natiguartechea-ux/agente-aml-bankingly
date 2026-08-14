# PRD — Agente de triage AML (Bankingly)
**Technical Product Manager — Ejercicio técnico**

---

## 1. El caso: elección, justificación y alternativas descartadas

### Problema

Las instituciones financieras de LATAM generan volúmenes altos de alertas AML por transacciones (estructuración, montos atípicos, patrones de velocity) que un analista de cumplimiento revisa una por una: contexto del cliente, historial transaccional, reglas que dispararon la alerta, y decisión de cerrar, escalar o pedir más info. El cuello de botella no es la detección (la resuelven las reglas/motores existentes) — es la **investigación y triage manual**: lento, inconsistente entre analistas, y generador de backlog que en algunos bancos se mide en semanas. Eso implica riesgo regulatorio directo (SLAs de reporte a UIF) y costo operativo (headcount de compliance escalando linealmente con volumen transaccional).

### Por qué este caso primero

| Dimensión | Evaluación |
|---|---|
| **Impacto** | Alto y medible: tiempo de investigación por alerta, % de alertas con backlog vencido, consistencia entre analistas. |
| **Esfuerzo** | Acotado: no requiere integrarse a rieles de pago ni tocar dinero real; consume datos que ya existen (transacciones, KYC básico, alertas) y propone una recomendación. No requiere cambios en el motor de reglas existente. |
| **Riesgo regulatorio** | Es el punto donde el approval gate por código importa más: el agente nunca cierra una alerta ni dispara un reporte por sí solo, siempre recomienda con evidencia y el analista aprueba. Defendible ante un regulador desde el día uno. |

### Alternativas descartadas

- **Aprobación de crédito**: mayor superficie de riesgo (dinero se mueve), requiere modelos de score financiero más complejos, más conservador como primer caso.
- **Verificación KYC**: es más un problema de extracción/verificación documental (OCR, matching de identidad) que de razonamiento — menos rico para demostrar el harness de decisión con aprobación humana.
- **Cobranza temprana**: menor riesgo regulatorio, pero también menor impacto/urgencia ejecutiva — más fácil de vender como "nice to have" que como apuesta estratégica.

---

## 2. Usuarios

- **Primario:** Analista de cumplimiento/AML — revisa alertas día a día, aprueba/rechaza/edita las recomendaciones del agente.
- **Secundario:** Oficial de cumplimiento (Compliance Officer) — supervisa métricas de backlog y consistencia, consume reportes, no opera el agente directamente.
- **No usuario en esta versión:** cliente final del banco (el agente es 100% interno).

---

## 3. Alcance de esta versión (v1)

**Entra:**
- Ingesta de una alerta AML simulada (transacción o patrón que disparó reglas existentes).
- El agente arma un caso: junta contexto del cliente, identifica la regla disparada, genera resumen de investigación + recomendación (cerrar / escalar a SAR / pedir info / bloquear cuenta) con evidencia. `bloquear_cuenta` es la recomendación reservada para casos de alta gravedad (ej. estructuración reincidente), donde además de reportar conviene congelar la cuenta preventivamente mientras avanza la investigación.
- El analista revisa y aprueba/rechaza/edita antes de cualquier efecto.
- Log auditable de cada decisión: recomendación del agente, decisión del humano, si hubo diferencia.

**No entra (roadmap futuro):**
- Integración real a UIF/organismos regulatorios.
- Motor de detección de nuevas reglas (se consumen alertas ya generadas).
- Multi-jurisdicción regulatoria (una jurisdicción de referencia en v1).
- Aprendizaje continuo del agente en base a decisiones del analista (v2).

---

## 4. Requisitos priorizados (MoSCoW)

- **Must:** aprobación humana obligatoria por código antes de cualquier efecto; trazabilidad de cada recomendación con evidencia; al menos 2-3 tipos de alerta simulados.
- **Should:** métricas de tiempo ahorrado estimado vs. proceso manual; casos difíciles donde el agente deba pedir info en vez de forzar una decisión.
- **Could:** dashboard simple de backlog/consistencia para el compliance officer.
- **Won't (v1):** integración real, multi-jurisdicción.

---

## 5. Criterios de aceptación

- Ninguna alerta se cierra ni se marca para reporte sin acción explícita del analista, garantizado en código (no en el prompt).
- El agente siempre devuelve evidencia trazable a datos concretos, no conclusiones sin sustento.
- Al menos un caso del set de evals donde el agente recomienda mal o pide escalar en falso, con análisis del porqué.

---

## 6. Cierre de producto

### Visión a 12 meses

El agente de triage AML se convierte en la capa estándar de investigación asistida para instituciones financieras LATAM en Bankingly: reduce el tiempo de investigación por alerta, mejora la consistencia de decisiones entre analistas, y da trazabilidad completa auditable para reguladores. Se ofrece como módulo dentro de la suite de Bankingly, configurable por jurisdicción, sin reemplazar al analista.

### Roadmap en 3 etapas

1. **v1 (0-3 meses) — Triage asistido, una jurisdicción.** Agente arma casos y recomienda, analista aprueba. Éxito = tiempo de investigación por alerta y % de recomendaciones aceptadas sin edición.
2. **v2 (3-7 meses) — Aprendizaje del feedback + multi-jurisdicción.** El agente ajusta su razonamiento en base a ediciones/rechazos históricos (no autonomía nueva, mejor calidad). Se suman reglas de 2-3 países más.
3. **v3 (7-12 meses) — Reporte semi-asistido + dashboard.** El agente prepara el borrador de SAR para revisión humana (sigue sin enviarlo); visibilidad agregada para el compliance officer.

### Esqueleto de business case

- **Costo evitado:** horas de analista por alerta × volumen mensual × costo hora, vs. costo de licenciar/operar el módulo.
- **Riesgo evitado:** reducción de alertas vencidas fuera de SLA regulatorio.
- **Upsell:** módulo adicional dentro de contratos existentes, sin integración nueva de rieles de pago — ciclo de venta más corto.

### Riesgos

- **Regulatorio:** que algún regulador exija que el SAR sea generado 100% por un humano sin asistencia de IA en el razonamiento → mitigación: el agente siempre es "asistente", nunca autor del reporte final.
- **Calidad del modelo:** falsos negativos (recomendar cerrar algo que debía escalarse) son el error más caro → mitigación: el agente nunca cierra, solo recomienda; los evals priorizan medir este error específico.
- **Adopción:** analistas aprobando "en automático" sin leer la evidencia (rubber-stamping) → mitigación: mostrar siempre evidencia, no solo conclusión.

### Go/No-Go con criterios de reversión

- **Go** si en piloto: alto % de recomendaciones aceptadas sin edición mayor, 0 casos de acción ejecutada sin aprobación humana, y tiempo de investigación baja de forma medible.
- **No-Go / reversión** si: el agente muestra sesgo sistemático hacia cerrar alertas que debían escalarse, o si los analistas dejan de leer la evidencia y aprueban en automático → se vuelve a modo manual y se rediseña el UX de revisión antes de reintentar.

---

## 7. Resultado de evals (v1 del prototipo)

Corrida en modo `mock` (heurística de prueba, sin dependencia de API key — ver `evals/run_evals.py`):

| Alerta | Dificultad | Esperado | Predicho | OK | Nota |
|---|---|---|---|---|---|
| A-001 | fácil | cerrar | pedir_info | ✗ | monto atípico pero coherente con perfil (aguinaldo); la heurística mock no captura ese matiz |
| A-002 | fácil | escalar_sar | escalar_sar | ✓ | patrón clásico de structuring |
| A-003 | difícil | pedir_info | pedir_info | ✓ | evidencia ambigua, correctamente no resuelta por el agente |
| A-004 | difícil | escalar_sar | escalar_sar | ✓ | caso trampa (perfil de bajo riesgo aparente) resuelto correctamente |
| A-005 | fácil | cerrar | cerrar | ✓ | montos bajos coherentes con perfil |

**Resultado:** Accuracy en casos fáciles = 67% (umbral definido: 80%) → **NO-GO** con la heurística mock actual.

**Análisis del fallo (A-001):** el mock decide por ratio monto/ingreso sin distinguir el *origen* de la transacción (aguinaldo declarado por el empleador vs. origen no identificable). Es una limitación esperable de una heurística simple — el modo `real` (Claude API) tiene el contexto textual completo y debería poder capturar esa distinción; queda como primer punto a validar al correr evals en modo real antes de avanzar a producción.

**Nota:** se prioriza mostrar este resultado real (con su NO-GO) en vez de forzar 100% — el ejercicio explícitamente valora el análisis de errores por sobre el éxito en casos fáciles.

**Actualización — cuarta acción `bloquear_cuenta`:** se agregó un cuarto tipo
de acción para casos de alta gravedad (estructuración reincidente, cliente
con alertas previas repitiendo el mismo patrón), donde reportar no alcanza y
conviene congelar la cuenta de forma preventiva. Se sumó el caso A-006 al
set de evals (ver `data/alertas.json` / `data/clientes.json`) y una métrica
secundaria dedicada — falsos negativos en bloqueo — con el mismo criterio de
tolerancia cero que ya existía para escalamiento (ver
`evals/run_evals.py`). Corrida en modo `mock` con los 6 casos:
accuracy en fáciles = 75% (baja de 67% a 75% al sumar A-006, que la
heurística mock resuelve bien), 0 falsos negativos en escalamiento, 0 falsos
negativos en bloqueo. El NO-GO se mantiene por el mismo motivo ya
documentado (A-001, limitación conocida de la heurística mock, no del
enfoque).

---

## 8. Registro de decisiones ante ambigüedad (resumen — detalle completo en README.md del repo)

- **Tool use estructurado sin función ejecutable**, en vez de function-calling con flag de aprobación interno — el control queda garantizado por ausencia de superficie de acción, no por convención de prompt.
- **Modo mock adicional al modo real** — permite reproducibilidad total del repo sin depender de una API key, a costa de no ser representativo de la calidad real de razonamiento (por eso el NO-GO de la sección 7 se documenta explícitamente como limitación del mock, no del enfoque).
- **SQLite en vez de estado en memoria** — agrega una dependencia mínima a cambio de auditoría persistente entre corridas, requisito explícito del ejercicio.
