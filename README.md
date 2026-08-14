# Agente de triage AML — Prototipo (Bankingly, ejercicio técnico)

Agente interno que asiste a un analista de cumplimiento en la investigación
de alertas AML: arma el caso, propone una resolución con evidencia, y
**nunca ejecuta nada por sí solo**. Toda acción con efectos requiere
aprobación explícita de un humano, garantizada por código.

## Setup

```bash
cd agente-aml
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Modo mock: no requiere API key, corre la heurística de prueba
python3 -m src.cli --modo mock

# Modo real: requiere ANTHROPIC_API_KEY en el entorno
export ANTHROPIC_API_KEY=sk-ant-...
python3 -m src.cli --modo real
```

Flags útiles:
- `--alerta A-003` procesa una sola alerta.
- `--no-interactivo` corre el flujo y muestra la propuesta sin pedir input (útil para debug rápido).
- `--demo-bypass` intenta forzar la ejecución de una acción sin aprobación humana, para mostrar en la sesión en vivo que el gate de código lo bloquea (ver punto 2 de los criterios de evaluación).

## Evals

```bash
python3 evals/run_evals.py mock
# o
python3 evals/run_evals.py real
```

Métrica, umbral y criterio de Go/No-Go documentados como docstring en
`evals/run_evals.py`, definidos antes de correr las mediciones.

## Arquitectura del agente

**Qué decide el modelo:**
- Interpretar la alerta y el contexto del cliente (perfil declarado, historial, transacciones).
- Redactar evidencia concreta y una justificación en lenguaje natural.
- Recomendar UNA acción entre `cerrar` / `escalar_sar` / `pedir_info` /
  `bloquear_cuenta`, con un nivel de confianza. `bloquear_cuenta` es para
  casos de alta gravedad (p. ej. estructuración reincidente) donde además
  de reportar conviene congelar la cuenta de forma preventiva.

**Qué garantiza el código (no el prompt):**
1. **Superficie de acción nula.** El modelo solo tiene disponible la tool
   `proponer_resolucion_alerta` (`src/models.py`), que no tiene ningún efecto
   secundario — es puramente estructura de datos. No existe ninguna función
   `cerrar_alerta()` o `marcar_sar()` expuesta al modelo. Aunque el modelo
   "quisiera" ejecutar algo, no tiene con qué.
2. **Validación de la propuesta antes de mostrarla al humano**
   (`src/gate.py::validar_propuesta`): rechaza acciones fuera del enum
   permitido, evidencia insuficiente (<2 items), o confianza fuera de rango.
3. **Único punto de ejecución de efectos** (`src/gate.py::ejecutar_decision`):
   es la única función de todo el sistema que puede mover una alerta a
   estado `resuelta`. Exige un `decision` explícito (`aprobada` /
   `rechazada` / `editada`) que en el flujo real (`src/cli.py`) solo puede
   originarse de un input humano por consola. El agente no tiene ninguna
   referencia a esta función.
4. **Auditoría completa** (`src/storage.py`): cada propuesta del agente y
   cada decisión humana queda loggeada con timestamp, separadas en tablas
   distintas — se puede reconstruir cualquier resolución y ver si hubo
   edición respecto a lo que el agente propuso.

```
Alerta simulada → Agente (LLM) → Propuesta JSON (sin efectos)
                                        ↓
                        Gate: valida schema + evidencia mínima
                                        ↓
                          Cola "pendiente_aprobacion"
                                        ↓
              Analista humano: Aprobar / Rechazar / Editar (input real)
                                        ↓
              gate.ejecutar_decision() → único punto de efecto real
                                        ↓
                              Log auditable (SQLite)
```

## Registro de decisiones (ADR breve)

**ADR 1 — Tool use estructurado sobre function-calling con flag de aprobación**
- Decisión: el modelo devuelve JSON vía tool use forzado (`tool_choice`), sin
  ninguna tool que ejecute efectos.
- Alternativa considerada: darle al modelo una tool `resolver_alerta()` con
  un parámetro `requiere_aprobacion=true`.
- Tradeoff: la alternativa es más "flexible" para el modelo, pero depende de
  que el modelo respete el flag — es un control por prompt/convención, no
  por código. Se descartó por ser más frágil justo en el punto que el
  ejercicio pide garantizar por código.

**ADR 2 — Modo mock además del modo real**
- Decisión: agregar una heurística simple (`agent.py::llamar_agente_mock`)
  para poder correr todo el flujo y los evals sin `ANTHROPIC_API_KEY`.
- Alternativa considerada: solo modo real con la API.
- Tradeoff: el modo mock no es representativo de la calidad de razonamiento
  real del agente (es deliberadamente simple), pero permite reproducibilidad
  total del repo sin depender de una key, y sirve como baseline para
  comparar contra el modo real en la sesión en vivo.

**ADR 3 — SQLite en vez de estado en memoria**
- Decisión: persistir alertas/propuestas/decisiones en SQLite local.
- Alternativa considerada: dict en memoria, más simple para un ejercicio de 8hs.
- Tradeoff: SQLite agrega una dependencia mínima (stdlib, sin costo real) a
  cambio de auditoría persistente entre corridas — importante porque el
  ejercicio pide explícitamente trazabilidad de decisiones, y un dict en
  memoria no sobrevive a reiniciar el proceso.

## Estructura del repo

```
agente-aml/
├── README.md              (este archivo)
├── requirements.txt
├── data/
│   ├── clientes.json       datos simulados de clientes
│   └── alertas.json        alertas simuladas, incluye casos difíciles marcados
├── src/
│   ├── models.py            schema de la propuesta del agente (el "contrato")
│   ├── agent.py              construcción de contexto + llamada al modelo (real/mock)
│   ├── gate.py                validación + único punto de ejecución de efectos
│   ├── storage.py           SQLite: estado, propuestas, decisiones (audit log)
│   └── cli.py                 flujo end-to-end interactivo
├── evals/
│   └── run_evals.py         métrica, umbral, Go/No-Go, análisis de fallos
└── intercambios_ia.md      (completar con tus 3 intercambios reales — ver plantilla)
```
