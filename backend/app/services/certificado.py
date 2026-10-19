from datetime import date
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def fecha_larga(d: date) -> str:
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def antiguedad(desde: date, hasta: date) -> str:
    anios = hasta.year - desde.year
    meses = hasta.month - desde.month
    if hasta.day < desde.day:
        meses -= 1
    if meses < 0:
        anios -= 1
        meses += 12
    partes = []
    if anios:
        partes.append(f"{anios} {'año' if anios == 1 else 'años'}")
    if meses:
        partes.append(f"{meses} {'mes' if meses == 1 else 'meses'}")
    return " y ".join(partes) if partes else "menos de un mes"


def generar(nombre: str, rut: str, cargo: str, area: str, ingreso: date,
            tipo_contrato: str | None, hoy: date) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    ancho, alto = A4

    c.setFillColorRGB(0.231, 0.286, 0.341)
    c.rect(0, alto - 3.2 * cm, ancho, 3.2 * cm, stroke=0, fill=1)
    c.setFillColorRGB(1, 0.478, 0.341)
    c.circle(2.2 * cm, alto - 1.6 * cm, 0.35 * cm, stroke=0, fill=1)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Times-Roman", 22)
    c.drawString(3 * cm, alto - 1.9 * cm, "AquaChile")

    c.setFillColorRGB(0.1, 0.13, 0.17)
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(ancho / 2, alto - 6 * cm, "CERTIFICADO DE ANTIGÜEDAD")

    texto = [
        "Recursos Humanos de AquaChile certifica que",
        f"{nombre}, RUT {rut},",
        f"se desempeña como {cargo} en el área de {area},",
        f"con fecha de ingreso el {fecha_larga(ingreso)}.",
        "",
        f"A la fecha cuenta con una antigüedad de {antiguedad(ingreso, hoy)}"
        + (f", con contrato {tipo_contrato}." if tipo_contrato else "."),
        "",
        "Se extiende el presente certificado a solicitud de la persona interesada",
        "para los fines que estime convenientes.",
    ]
    y = alto - 8.5 * cm
    c.setFont("Helvetica", 12)
    for linea in texto:
        c.drawString(3 * cm, y, linea)
        y -= 0.8 * cm

    c.setFont("Helvetica", 10)
    c.drawString(3 * cm, 5 * cm, f"Emitido el {fecha_larga(hoy)}.")
    c.line(3 * cm, 3.6 * cm, 9 * cm, 3.6 * cm)
    c.drawString(3 * cm, 3.1 * cm, "Recursos Humanos · AquaChile")
    c.showPage()
    c.save()
    return buf.getvalue()
