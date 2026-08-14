"""
Persistencia simple en SQLite. Guarda:
- el estado de cada alerta (pendiente_agente / pendiente_aprobacion / resuelta)
- cada propuesta que generó el agente
- cada decisión humana, con timestamp, para auditoría

Esto es lo que en la sesión en vivo se muestra como "trazabilidad completa":
cualquier efecto ejecutado es reconstruible desde acá.
"""
import sqlite3
import json
import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "aml_agent.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS alertas (
            alerta_id TEXT PRIMARY KEY,
            estado TEXT NOT NULL DEFAULT 'pendiente_agente',
            cliente_id TEXT NOT NULL,
            regla_disparada TEXT NOT NULL,
            raw_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS propuestas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alerta_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            accion_propuesta TEXT NOT NULL,
            confianza REAL NOT NULL,
            evidencia_json TEXT NOT NULL,
            justificacion TEXT NOT NULL,
            factores_json TEXT NOT NULL,
            modo TEXT NOT NULL,
            FOREIGN KEY (alerta_id) REFERENCES alertas(alerta_id)
        );

        CREATE TABLE IF NOT EXISTS decisiones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alerta_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            decision TEXT NOT NULL,
            accion_final TEXT NOT NULL,
            accion_propuesta_original TEXT NOT NULL,
            editado INTEGER NOT NULL,
            analista TEXT NOT NULL,
            comentario TEXT,
            FOREIGN KEY (alerta_id) REFERENCES alertas(alerta_id)
        );
        """
    )
    conn.commit()
    conn.close()


def upsert_alerta(alerta: dict):
    conn = get_conn()
    conn.execute(
        "INSERT INTO alertas (alerta_id, cliente_id, regla_disparada, raw_json) "
        "VALUES (?, ?, ?, ?) ON CONFLICT(alerta_id) DO NOTHING",
        (alerta["alerta_id"], alerta["cliente_id"], alerta["regla_disparada"], json.dumps(alerta)),
    )
    conn.commit()
    conn.close()


def guardar_propuesta(alerta_id: str, propuesta: dict, modo: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO propuestas (alerta_id, timestamp, accion_propuesta, confianza, "
        "evidencia_json, justificacion, factores_json, modo) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            alerta_id,
            datetime.datetime.utcnow().isoformat(),
            propuesta["accion_propuesta"],
            propuesta["confianza"],
            json.dumps(propuesta["evidencia"]),
            propuesta["justificacion"],
            json.dumps(propuesta["factores_de_riesgo_identificados"]),
            modo,
        ),
    )
    conn.execute(
        "UPDATE alertas SET estado = 'pendiente_aprobacion' WHERE alerta_id = ?",
        (alerta_id,),
    )
    conn.commit()
    conn.close()


def registrar_decision(alerta_id: str, decision: str, accion_final: str, accion_propuesta_original: str,
                        analista: str = "analista_demo", comentario: str = ""):
    """
    Este es el ÚNICO punto del sistema con permiso de escribir un estado
    'resuelto'. El agente no puede llegar acá directamente.
    """
    if decision not in {"aprobada", "rechazada", "editada"}:
        raise ValueError(f"decisión inválida: {decision}")

    conn = get_conn()
    conn.execute(
        "INSERT INTO decisiones (alerta_id, timestamp, decision, accion_final, "
        "accion_propuesta_original, editado, analista, comentario) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            alerta_id,
            datetime.datetime.utcnow().isoformat(),
            decision,
            accion_final,
            accion_propuesta_original,
            1 if decision == "editada" else 0,
            analista,
            comentario,
        ),
    )
    conn.execute("UPDATE alertas SET estado = 'resuelta' WHERE alerta_id = ?", (alerta_id,))
    conn.commit()
    conn.close()


def audit_log(alerta_id: str = None) -> list[dict]:
    conn = get_conn()
    q = "SELECT * FROM decisiones"
    params = ()
    if alerta_id:
        q += " WHERE alerta_id = ?"
        params = (alerta_id,)
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]
