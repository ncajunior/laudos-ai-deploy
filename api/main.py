from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os, psycopg2, hashlib, qrcode, requests
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from PyPDF2 import PdfMerger
import importlib.util
import sys

# permitir importar o módulo scripts.gerar_laudo
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
try:
    from scripts.gerar_laudo import gerar_laudo as gerar_laudo_func
except Exception:
    gerar_laudo_func = None

app = FastAPI()
# Preferir variável de ambiente DATABASE_URL (formato libpq) para não deixar credenciais no código
DB = os.getenv('DATABASE_URL')
if not DB:
    # fallback local — não recomendado para produção
    DB = os.getenv('DB_FALLBACK', '')
    if not DB:
        # aviso em log simples (uvicorn logs mostrarão stdout)
        print('WARNING: DATABASE_URL not set. DB connections will fail if used.')
LAUDOS_DIR = os.getenv('LAUDOS_DIR', '/app/laudos')

@app.get("/health")
def health():
    return {"status": "up"}

@app.post("/api/atualiza_centroid")
def atualiza_centroid(req: dict):
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""UPDATE imoveis.imoveisvist
                           SET geom = ST_SetSRID(ST_MakePoint(%(lng)s, %(lat)s), 4326)
                           WHERE tombamento = %(tombamento)s""", req)
    return {"ok": True}

@app.post("/api/rollback")
def rollback():
    # endpoint disabled for safety. Previously executed shell commands which is a security risk.
    # Keep route for audit but forbid execution via HTTP. Use deploy pipeline or SSH for rollback.
    print('Rollback endpoint called but disabled for safety')
    from fastapi import Response
    return Response(status_code=403, content='Rollback via HTTP is disabled')


@app.get('/verificar')
def verificar(hash: str):
    # procura arquivos PDF na pasta de laudos e compara SHA256
    import hashlib
    for fn in os.listdir(LAUDOS_DIR):
        if not fn.lower().endswith('.pdf'):
            continue
        path = os.path.join(LAUDOS_DIR, fn)
        try:
            with open(path, 'rb') as f:
                h = hashlib.sha256(f.read()).hexdigest()
                if h == hash:
                    # extrai tombamento se seguir padrão laudo_<tombamento>_YYYY-MM-DD
                    parts = fn.split('_')
                    tomb = parts[1] if len(parts) > 1 else None
                    return {"valido": True, "tombamento": tomb, "filename": fn}
        except Exception:
            continue
    raise HTTPException(status_code=404, detail='Laudo não encontrado ou inválido')


@app.post('/api/gerar_laudo/{tombamento}')
def api_gerar_laudo(tombamento: int):
    """Gera um laudo PDF para o tombamento e retorna o caminho"""
    if gerar_laudo_func is None:
        # tentar chamar o script diretamente como fallback
        import subprocess, shlex
        # caminho absoluto dentro do container (projeto copiado para /app)
        script_path = '/app/scripts/gerar_laudo.py'
        cmd = f'python3 {shlex.quote(script_path)} {tombamento}'
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if proc.returncode != 0:
            raise HTTPException(status_code=500, detail=f'failed to run gerar_laudo: {proc.stderr}')
        # tentar recuperar o path impresso pelo script
        out = proc.stdout.strip()
        return {'ok': True, 'path': out}

    try:
        pdf_path = gerar_laudo_func(tombamento)
        return {'ok': True, 'path': pdf_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/validar/{tombamento}')
def api_validar(tombamento: int):
    """Runs a set of spatial and attribute validations for the given tombamento.
    Results are attempted to be recorded in imoveis.validation_log if database is available.
    """
    try:
        from . import validators
    except Exception:
        # fallback import for script context
        import validators

    results = {}
    try:
        results['centroid'] = validators.check_centroid_exists_and_within_muni(tombamento)
    except Exception as e:
        results['centroid_error'] = str(e)

    try:
        results['required_fields'] = validators.check_required_fields(tombamento)
    except Exception as e:
        results['required_fields_error'] = str(e)

    # try to record to DB; if DB isn't available, skip silently
    try:
        validators.record_validation_log(tombamento, results)
        results['logged'] = True
    except Exception as e:
        results['logged'] = False
        results['log_error'] = str(e)

    return {'ok': True, 'results': results}
