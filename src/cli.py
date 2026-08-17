"""
CLI del prototipo. Corre el flujo completo:

  alerta simulada -> agente propone (JSON) -> gate valida -> cola de
  aprobación -> analista humano decide (input real por consola) -> gate
  ejecuta el efecto -> log auditable


"""
import argparse
import json
from pathlib import Path

from src import storage, agent, gate

DATA_DIR = Path(__file__).parent.parent / "data"


def cargar_datos():
    clientes = {c["cliente_id"]: c for c in json.loads((DATA_DIR / "clientes.json").read_text())}
    alertas = json.loads((DATA_DIR / "alertas.json").read_text())
    return clientes, alertas


def imprimir_propuesta(alerta_id: str, propuesta: dict):
    print(f"\n{'='*60}\nALERTA {alerta_id} — PROPUESTA DEL AGENTE\n{'='*60}")
    print(f"Acción propuesta: {propuesta['accion_propuesta']}  (confianza: {propuesta['confianza']:.2f})")
    print(f"Justificación: {propuesta['justificacion']}")
    print("Evidencia:")
    for e in propuesta["evidencia"]:
        print(f"  - {e}")
    print("Factores de riesgo:")
    for f in propuesta["factores_de_riesgo_identificados"]:
        print(f"  - {f}")
    print(f"{'='*60}")
    print("*** Esta acción NO se ha ejecutado. Requiere aprobación humana. ***\n")


def flujo_alerta(alerta: dict, clientes: dict, modo: str, interactivo: bool, demo_bypass: bool):
    storage.upsert_alerta(alerta)
    cliente = clientes[alerta["cliente_id"]]

    propuesta = agent.proponer(alerta, cliente, modo=modo)
    gate.encolar_propuesta(alerta["alerta_id"], propuesta, modo=modo)
    imprimir_propuesta(alerta["alerta_id"], propuesta)

    if demo_bypass:
        # Demuestra explícitamente que no existe un camino de código para esto:
        # gate.ejecutar_decision() exige un `decision` humano válido, no hay
        # función alguna que el agente pueda invocar para saltear este paso.
        print("[DEMO] Intentando ejecutar la acción propuesta SIN pasar por aprobación humana...")
        try:
            gate.ejecutar_decision(
                alerta_id=alerta["alerta_id"],
                decision="__bypass_intentado__",  # valor inválido a propósito
                accion_final=propuesta["accion_propuesta"],
                accion_propuesta_original=propuesta["accion_propuesta"],
                analista="__agente__",
            )
        except ValueError as e:
            print(f"[DEMO] Bloqueado por el gate de código: {e}\n")
        return

    if not interactivo:
        return propuesta

    while True:
        resp = input("Analista: ¿aprobar / rechazar / editar? [a/r/e]: ").strip().lower()
        if resp in ("a", "r", "e"):
            break
        print(f"Opción inválida: '{resp}'. Ingresá 'a' (aprobar), 'r' (rechazar) o 'e' (editar).")

    if resp == "a":
        gate.ejecutar_decision(
            alerta["alerta_id"], "aprobada", propuesta["accion_propuesta"],
            propuesta["accion_propuesta"], analista="analista_demo",
        )
    elif resp == "r":
        motivo = input("Motivo de rechazo: ")
        gate.ejecutar_decision(
            alerta["alerta_id"], "rechazada", "sin_accion",
            propuesta["accion_propuesta"], analista="analista_demo", comentario=motivo,
        )
    elif resp == "e":
        nueva_accion = input(
            "Acción final que decide el analista [cerrar/escalar_sar/pedir_info/bloquear_cuenta]: "
        ).strip()
        gate.ejecutar_decision(
            alerta["alerta_id"], "editada", nueva_accion,
            propuesta["accion_propuesta"], analista="analista_demo",
        )
    return propuesta


def main():
    parser = argparse.ArgumentParser(description="Prototipo agente triage AML")
    parser.add_argument("--modo", choices=["mock", "real"], default="mock",
                         help="mock = heurística sin API key; real = Claude API")
    parser.add_argument("--alerta", help="Procesar solo un alerta_id específico")
    parser.add_argument("--no-interactivo", action="store_true", help="No pide input, solo muestra la propuesta")
    parser.add_argument("--demo-bypass", action="store_true",
                         help="Demuestra que un intento de ejecutar sin aprobación es bloqueado por el código")
    args = parser.parse_args()

    storage.init_db()
    clientes, alertas = cargar_datos()

    if args.alerta:
        alertas = [a for a in alertas if a["alerta_id"] == args.alerta]

    for alerta in alertas:
        flujo_alerta(alerta, clientes, modo=args.modo, interactivo=not args.no_interactivo,
                     demo_bypass=args.demo_bypass)


if __name__ == "__main__":
    main()
