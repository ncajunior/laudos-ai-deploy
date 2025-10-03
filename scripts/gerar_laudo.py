import psycopg2, openai, os, requests, hashlib, qrcode
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from PyPDF2 import PdfMerger

DB = os.getenv('DATABASE_URL') or os.getenv('DB_FALLBACK')
openai.api_key = os.getenv("OPENAI_API_KEY")

def gerar_laudo(tombamento: int) -> str:
    """
    Gerador de laudo placeholder:
    - Busca dados no banco (não implementado aqui se DB não estiver configurado)
    - Gera PDF simples com informação mínima
    - Retorna caminho do PDF gerado
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from datetime import datetime
    import os

    outdir = os.getenv('LAUDOS_DIR', '/app/laudos')
    os.makedirs(outdir, exist_ok=True)
    now = datetime.now().strftime('%Y-%m-%d')
    pdf_path = os.path.join(outdir, f'laudo_{tombamento}_{now}.pdf')

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    story = []
    story.append(Paragraph('Prefeitura - Laudo de Vistoria (placeholder)', styles['Title']))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f'Tombamento: {tombamento}', styles['Normal']))
    story.append(Paragraph(f'Data: {now}', styles['Normal']))
    story.append(Spacer(1, 12))
    story.append(Paragraph('Este é um laudo gerado automaticamente (conteúdo de exemplo).', styles['Normal']))
    doc.build(story)
    return pdf_path

if __name__ == "__main__":
    import sys
    path = gerar_laudo(int(sys.argv[1]))
    # imprimir o caminho do PDF para que o caller (subprocess) capture
    print(path)
