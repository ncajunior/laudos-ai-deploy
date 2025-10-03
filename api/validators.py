import os
import psycopg2
import psycopg2.extras
from typing import Dict, Any

DB = os.getenv('DATABASE_URL')


def _connect():
    if not DB:
        raise RuntimeError('DATABASE_URL not set')
    return psycopg2.connect(DB)


def check_centroid_exists_and_within_muni(tombamento: int) -> Dict[str, Any]:
    """Check centroid validity and whether it's within the municipality polygon.

    Returns dict with keys: centroid_present (bool), within_municipio (bool)
    """
    q = """
    SELECT
      (i.geom IS NOT NULL) as centroid_present,
      ST_Within(i.geom, m.geom) as within_municipio
    FROM imoveis.vw_imoveisvist i
    CROSS JOIN map."area-aguiabranca" m
    WHERE i.tombamento = %s
    LIMIT 1
    """
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(q, (tombamento,))
            row = cur.fetchone()
            if not row:
                return {"centroid_present": False, "within_municipio": False}
            return {"centroid_present": bool(row[0]), "within_municipio": bool(row[1])}
    finally:
        conn.close()


def check_required_fields(tombamento: int) -> Dict[str, Any]:
    """Check presence of required fields (master, tipobem, tipoimovel, descricao, qtdfotos)

    Returns a dict with field statuses.
    """
    q = """
    SELECT master, tipobem, tipoimovel, descricao, qtdfotos
    FROM imoveis.vw_imoveisvist
    WHERE tombamento = %s
    LIMIT 1
    """
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(q, (tombamento,))
            row = cur.fetchone()
            if not row:
                return {"found": False}
            master, tipobem, tipoimovel, descricao, qtdfotos = row
            return {
                "found": True,
                "master_ok": bool(master and master != 0),
                "tipobem_ok": (tipobem == '002'),
                "tipoimovel_ok": (tipoimovel in ('B', 'T')),
                "descricao_ok": bool(descricao and descricao.strip()),
                "qtdfotos_ok": (qtdfotos is not None and qtdfotos > 0),
            }
    finally:
        conn.close()


def record_validation_log(tombamento: int, results: Dict[str, Any]):
    """Insert a validation log row into a table validation_log (create table if not exists).
    This is lightweight: will attempt to create the table if missing.
    """
    create_q = """
    CREATE TABLE IF NOT EXISTS imoveis.validation_log (
      id SERIAL PRIMARY KEY,
      tombamento bigint,
      result jsonb,
      created_at timestamptz DEFAULT now()
    );
    """
    insert_q = "INSERT INTO imoveis.validation_log (tombamento, result) VALUES (%s, %s)"

    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(create_q)
            cur.execute(insert_q, (tombamento, psycopg2.extras.Json(results)))
            conn.commit()
    finally:
        conn.close()
