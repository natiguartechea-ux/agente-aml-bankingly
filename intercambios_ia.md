# Intercambios con IA — registro requerido

Este archivo debe reemplazarse con tus intercambios REALES, copiados tal
cual (no resumidos), de la herramienta que uses (Claude Code, Claude.ai,
Codex, etc.) mientras construiste este prototipo.

Se piden como mínimo 3 momentos:

## (a) El prompt que produjo la pieza más importante del prototipo

[Pegar acá, tal cual, el prompt + respuesta que generó el gate de
aprobación (src/gate.py) o el schema de la propuesta (src/models.py) —
son las piezas que garantizan el control por código.]

## (b) Un intercambio donde el modelo devolvió algo incorrecto y cómo lo detectaste

[Ejemplo real de este build: si le pedís a una IA que te arme el gate,
un error típico es que proponga darle al modelo una tool con un flag
`requiere_aprobacion=true` en vez de no darle ninguna tool con efectos.
Documentá el intercambio real donde pasó algo así, y cómo lo detectaste
al revisar el código — no alcanza con decir "lo revisé", mostrá el
razonamiento.]

## (c) El momento en que cambiaste de enfoque porque la herramienta te llevaba a un lugar equivocado

[Pegar acá un intercambio real donde tuviste que redirigir — por ejemplo
si la IA te sugirió guardar el estado solo en memoria y vos decidiste
pasar a SQLite por la necesidad de auditoría persistente (ver ADR 3 del
README), o si te sugirió una accuracy de evals sin umbral definido de
antemano y tuviste que pedirle que lo definiera antes de medir.]

---

**Nota:** no incluyas conversaciones ajenas al ejercicio. Si tu herramienta
exporta la sesión completa, podés adjuntarla sin editar en vez de esto.
