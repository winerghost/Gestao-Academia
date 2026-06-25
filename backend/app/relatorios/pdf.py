import io
from datetime import date
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

AZUL = colors.HexColor("#1a56db")
AZUL_CLARO = colors.HexColor("#e8f0fe")
CINZA = colors.HexColor("#f3f4f6")
TEXTO = colors.HexColor("#111827")


def gerar_pdf(titulo: str, headers: list, rows: list) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle(
        "titulo", parent=styles["Title"], textColor=AZUL, fontSize=16
    )
    subtitulo_style = ParagraphStyle(
        "subtitulo", parent=styles["Normal"], textColor=colors.grey, fontSize=9
    )

    elementos = [
        Paragraph(titulo, titulo_style),
        Paragraph(f"Gerado em {date.today().strftime('%d/%m/%Y')}", subtitulo_style),
        Spacer(1, 0.5 * cm),
    ]

    data = [headers] + [[str(v) for v in row] for row in rows]

    tabela = Table(data, repeatRows=1)

    estilo = TableStyle([
        # Cabeçalho
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        # Corpo
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("TEXTCOLOR", (0, 1), (-1, -1), TEXTO),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        # Grade
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ])

    # Linhas alternadas
    for i in range(1, len(data)):
        cor = CINZA if i % 2 == 0 else colors.white
        estilo.add("BACKGROUND", (0, i), (-1, i), cor)

    tabela.setStyle(estilo)
    elementos.append(tabela)

    doc.build(elementos)
    buffer.seek(0)
    return buffer
