"""
Set de evaluación.

Métrica definida ANTES de medir:
  - Accuracy simple: % de casos donde accion_propuesta == accion_esperada.
  - Se mide por separado accuracy en casos "facil" vs. "dificil", porque son
    tipos de error distintos.
  - Métrica secundaria, más importante que accuracy global: tasa de FALSOS
    NEGATIVOS EN ESCALAMIENTO, casos donde accion_esperada = escalar_sar y
    el agente propuso cerrar. Este es el error más caro del sistema, así que se reporta aparte.
  - Métrica secundaria adicional: tasa de FALSOS NEGATIVOS EN BLOQUEO —
    casos donde accion_esperada = bloquear_cuenta y el agente propuso otra
    cosa. 

Umbral definido ANTES de medir:
  - Accuracy >= 80% en casos "facil" para considerar el prototipo viable.
  - CERO falsos negativos en escalamiento (accion_esperada=escalar_sar,
    predicho=cerrar) tolerados en v1 — cualquier caso así es un fallo crítico
    a analizar.
  - CERO falsos negativos en bloqueo (accion_esperada=bloquear_cuenta,
    predicho≠bloquear_cuenta) tolerados en v1, con el mismo criterio.
  - Casos "dificil" se reportan pero NO cuentan para el umbral de Go/No-Go:
    son justamente los casos donde se espera fricción, y lo que importa ahí
    es el análisis de por qué falla, no el score.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src import agent

DATA_DIR = Path(__file__).parent.parent / "data"

UMBRAL_ACCURACY_FACIL = 0.80


def cargar_datos():
    clientes = {c["cliente_id"]: c for c in json.loads((DATA_DIR / "clientes.json").read_text())}
    alertas = json.loads((DATA_DIR / "alertas.json").read_text())
    return clientes, alertas


def correr_evals(modo="mock"):
    clientes, alertas = cargar_datos()
    resultados = []

    for alerta in alertas:
        cliente = clientes[alerta["cliente_id"]]
        propuesta = agent.proponer(alerta, cliente, modo=modo)
        correcto = propuesta["accion_propuesta"] == alerta["accion_esperada"]
        falso_negativo_escalamiento = (
            alerta["accion_esperada"] == "escalar_sar" and propuesta["accion_propuesta"] == "cerrar"
        )
        falso_negativo_bloqueo = (
            alerta["accion_esperada"] == "bloquear_cuenta" and propuesta["accion_propuesta"] != "bloquear_cuenta"
        )
        resultados.append({
            "alerta_id": alerta["alerta_id"],
            "dificultad": alerta["dificultad"],
            "esperado": alerta["accion_esperada"],
            "predicho": propuesta["accion_propuesta"],
            "confianza": propuesta["confianza"],
            "correcto": correcto,
            "falso_negativo_escalamiento": falso_negativo_escalamiento,
            "falso_negativo_bloqueo": falso_negativo_bloqueo,
            "nota_eval": alerta.get("nota_eval", ""),
        })
    return resultados


def reportar(resultados):
    print(f"\n{'='*70}\nRESULTADOS DE EVALS (modo={sys.argv[1] if len(sys.argv) > 1 else 'mock'})\n{'='*70}")
    print(f"{'ID':<8}{'Dificultad':<10}{'Esperado':<15}{'Predicho':<15}{'OK':<5}{'FN-escalam.':<12}")
    for r in resultados:
        print(f"{r['alerta_id']:<8}{r['dificultad']:<10}{r['esperado']:<15}{r['predicho']:<15}"
              f"{'✓' if r['correcto'] else '✗':<5}{'⚠️ SI' if r['falso_negativo_escalamiento'] else '-':<12}")

    faciles = [r for r in resultados if r["dificultad"] == "facil"]
    dificiles = [r for r in resultados if r["dificultad"] == "dificil"]

    acc_facil = sum(r["correcto"] for r in faciles) / len(faciles) if faciles else 0
    acc_dificil = sum(r["correcto"] for r in dificiles) / len(dificiles) if dificiles else 0
    fns = [r for r in resultados if r["falso_negativo_escalamiento"]]
    fns_bloqueo = [r for r in resultados if r["falso_negativo_bloqueo"]]

    print(f"\nAccuracy casos fáciles:   {acc_facil:.0%}  (umbral: {UMBRAL_ACCURACY_FACIL:.0%})")
    print(f"Accuracy casos difíciles: {acc_dificil:.0%}  (no cuenta para Go/No-Go, es informativo)")
    print(f"Falsos negativos en escalamiento: {len(fns)}  (umbral: 0 tolerados)")
    print(f"Falsos negativos en bloqueo:      {len(fns_bloqueo)}  (umbral: 0 tolerados)")

    if fns:
        print("\n--- Análisis de falsos negativos en escalamiento ---")
        for r in fns:
            print(f"  {r['alerta_id']}: {r['nota_eval']}")

    if fns_bloqueo:
        print("\n--- Análisis de falsos negativos en bloqueo ---")
        for r in fns_bloqueo:
            print(f"  {r['alerta_id']}: {r['nota_eval']}")

    print("\n--- Análisis de casos difíciles ---")
    for r in dificiles:
        estado = "OK" if r["correcto"] else "FALLA"
        print(f"  {r['alerta_id']} [{estado}]: {r['nota_eval']}")

    go = acc_facil >= UMBRAL_ACCURACY_FACIL and len(fns) == 0 and len(fns_bloqueo) == 0
    print(f"\n{'='*70}")
    print(f"GO / NO-GO (según criterios del PRD): {'GO' if go else 'NO-GO'}")
    print(f"{'='*70}\n")
    return go


if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else "mock"
    resultados = correr_evals(modo=modo)
    reportar(resultados)
