import os
try:
    import openai
except Exception:
    openai = None

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Image as RLImage
from reportlab.lib.units import cm
import hashlib
import qrcode
from PyPDF2 import PdfMerger

DB = os.getenv('DATABASE_URL') or os.getenv('DB_FALLBACK')
if openai is not None:
    openai.api_key = os.getenv('OPENAI_API_KEY')


def gerar_laudo(tombamento: int) -> str:
    """
    Gerador de laudo placeholder (copiado para dentro de api/ para disponível no container):
    """
    from datetime import datetime
    outdir = os.getenv('LAUDOS_DIR', '/app/laudos')
    os.makedirs(outdir, exist_ok=True)
    now = datetime.now().strftime('%Y-%m-%d')
    pdf_path = os.path.join(outdir, f'laudo_{tombamento}_{now}.pdf')

    # gerar descrição via OpenAI quando configurado
    descricao = 'Este é um laudo gerado automaticamente (conteúdo de exemplo).'
    if openai is not None and os.getenv('OPENAI_API_KEY'):
        try:
            prompt = f"""Você é um engenheiro civil. Gere um parágrafo técnico curto para um laudo de vistoria.
Tombamento: {tombamento}
"""
            # suporte para openai v1.x (OpenAI client) e compatibilidade com versão antiga
            try:
                # nova interface
                client = openai.OpenAI()
                res = client.chat.completions.create(
                    model='gpt-3.5-turbo',
                    messages=[{'role': 'user', 'content': prompt}],
                    max_tokens=300,
                )
                # novo formato: res.choices[0].message.content
                descricao = res.choices[0].message.content.strip()
            except AttributeError:
                # versão antiga (0.x)
                res = openai.ChatCompletion.create(
                    model='gpt-3.5-turbo',
                    messages=[{'role': 'user', 'content': prompt}],
                    max_tokens=300,
                )
                descricao = res.choices[0].message.content.strip()
        except Exception as e:
            # log simples para diagnosticar falha ao chamar OpenAI
            try:
                print('OpenAI call failed:', repr(e))
            except Exception:
                pass
            # fallback para texto fixo
            descricao = 'Descrição automática (fallback) - não foi possível chamar OpenAI.'

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    story = []
    story.append(Paragraph('Prefeitura - Laudo de Vistoria', styles['Title']))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f'Tombamento: {tombamento}', styles['Normal']))
    story.append(Paragraph(f'Data: {now}', styles['Normal']))
    story.append(Spacer(1, 12))
    story.append(Paragraph('1. Descrição Técnica', styles['Heading2']))
    story.append(Paragraph(descricao, styles['Normal']))
    story.append(Spacer(1, 12))

    # inserir foto se disponível
    imagens_dir = os.getenv('IMAGENS_DIR', '/app/imagens')
    foto_path = os.path.join(imagens_dir, f"{tombamento:0>15}001.png")
    if not os.path.exists(foto_path):
        # tentar formato sem padding
        alt = os.path.join(imagens_dir, f"{tombamento}001.png")
        if os.path.exists(alt):
            foto_path = alt
        else:
            foto_path = None

    if foto_path:
        try:
            # redimensiona via RLImage
            img = RLImage(foto_path, width=10*cm, height=8*cm)
            story.append(Paragraph('2. Fotos', styles['Heading2']))
            story.append(img)
            story.append(Spacer(1, 12))
        except Exception:
            pass

    doc.build(story)

    # assinar: gerar hash e QR, criar página com assinatura e mesclar
    with open(pdf_path, 'rb') as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()

    qr = qrcode.make(f"http://localhost/verificar?hash={file_hash}")
    qr_path = pdf_path.replace('.pdf', '_qr.png')
    qr.save(qr_path)

    sig_pdf = pdf_path.replace('.pdf', '_sig.pdf')
    # página de assinatura simples
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(sig_pdf, pagesize=A4)
    c.drawString(2*cm, 3*cm, f"Assinatura digital (SHA256): {file_hash}")
    c.drawImage(qr_path, 14*cm, 2*cm, width=3*cm, height=3*cm)
    c.save()

    signed_pdf = pdf_path.replace('.pdf', '_assinado.pdf')
    merger = PdfMerger()
    merger.append(pdf_path)
    merger.append(sig_pdf)
    merger.write(signed_pdf)
    merger.close()

    # cleanup temporários
    try:
        os.remove(sig_pdf)
        os.remove(qr_path)
    except Exception:
        pass

    return signed_pdf


if __name__ == '__main__':
    import sys
    path = gerar_laudo(int(sys.argv[1]))
    print(path)
