# Agente de AML — Prototipo (Bankingly)

Agente interno que asiste a un analista de cumplimiento en la investigación
de alertas AML: arma el caso, propone una resolución, y
**nunca ejecuta nada por sí solo**. Toda acción con efectos requiere
aprobación explícita de un humano.

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
- `--no-interactivo` corre el flujo y muestra la propuesta sin pedir input.
- `--demo-bypass` intenta forzar la ejecución de una acción sin aprobación humana.

## Evals

```bash
python3 evals/run_evals.py mock
# o
python3 evals/run_evals.py real
```

Criterio de Go/No-Go en
`evals/run_evals.py`.

## Arquitectura del agente

**Qué decide el modelo:**
- Interpretar la alerta y el contexto del cliente.
- Redactar evidencia concreta y justificación.
- Recomendar UNA acción entre `cerrar` / `escalar_sar` / `pedir_info` /
  `bloquear_cuenta`. `bloquear_cuenta` es para
  casos de alta gravedad, donde además
  de reportar conviene congelar la cuenta de forma preventiva.

**Qué garantiza el código:**
1. **Superficie de acción nula.** El modelo solo tiene disponible la tool
   `proponer_resolucion_alerta` (`src/models.py`), que no tiene ningún efecto
   secundario. No existe ninguna función
   `cerrar_alerta()` o `marcar_sar()` expuesta al modelo. Aunque el modelo
   "quisiera" ejecutar algo, no tiene como hacerlo.
2. **Validación de la propuesta antes de mostrarla al humano**
   (`src/gate.py::validar_propuesta`): rechaza acciones fuera de lo 
   permitido, evidencia insuficiente, o confianza fuera de rango.
3. **Único punto de ejecución de efectos** (`src/gate.py::ejecutar_decision`):
   es la única función de todo el sistema que puede mover una alerta a
   estado `resuelta`. Exige un `decision` explícito (`aprobada` /
   `rechazada` / `editada`) que en el flujo (`src/cli.py`) solo puede
   originarse de un input humano por consola. 
4. **Auditoría completa** (`src/storage.py`): cada propuesta del agente y
   cada decisión humana queda loggeada con timestamp, separadas en tablas
   distintas.

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

## Registro de decisiones

**ADR 1 — Tool use estructurado sobre function-calling con flag de aprobación**
- Decisión: el modelo devuelve JSON vía tool use forzado (`tool_choice`), sin
  ninguna tool que ejecute efectos.
- Alternativa considerada: darle al modelo una tool `resolver_alerta()` con
  un parámetro `requiere_aprobacion=true`.
- Tradeoff: la alternativa es más "flexible" para el modelo, pero depende de
  que el modelo respete el flag. 

**ADR 2 — Modo mock además del modo real**
- Decisión: agregar una heurística simple (`agent.py::llamar_agente_mock`)
  para poder correr todo el flujo y los evals sin `ANTHROPIC_API_KEY`.
- Alternativa considerada: solo modo real con la API.
- Tradeoff: el modo mock no es representativo de la calidad de razonamiento
  real del agente.

**ADR 3 — SQLite en vez de estado en memoria**
- Decisión: persistir alertas/propuestas/decisiones en SQLite local.
- Alternativa considerada: dict en memoria.
- Tradeoff: SQLite agrega una dependencia mínima a
  cambio de auditoría persistente.

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
