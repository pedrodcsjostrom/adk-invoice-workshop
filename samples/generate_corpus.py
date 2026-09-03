#!/usr/bin/env python3
"""Generate the synthetic invoice corpus used by the workshop demo.

Everything here is invented. No real supplier, address, tax id or bank detail
appears in the output. Run it with uv, which pulls the two rendering
dependencies into a throwaway environment:

    uv run --with reportlab --with pillow samples/generate_corpus.py

Output lands in samples/invoices/. See samples/invoices/README.md for what each
file is meant to exercise.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

OUT = Path(__file__).resolve().parent / "invoices"
DEJAVU = Path("/usr/share/fonts/truetype/dejavu")
PAGE_W, PAGE_H = A4
MARGIN = 20 * 2.83465  # 20mm in points

INK = HexColor("#1a1a1a")
MUTED = HexColor("#666666")
RULE = HexColor("#bbbbbb")


def register_fonts() -> None:
    pdfmetrics.registerFont(TTFont("Body", str(DEJAVU / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("Body-Bold", str(DEJAVU / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("Serif", str(DEJAVU / "DejaVuSerif.ttf")))
    pdfmetrics.registerFont(TTFont("Serif-Bold", str(DEJAVU / "DejaVuSerif-Bold.ttf")))


@dataclass
class Line:
    description: str
    quantity: float
    unit_price: float

    @property
    def amount(self) -> float:
        return round(self.quantity * self.unit_price, 2)


@dataclass
class Invoice:
    filename: str
    supplier_printed: str
    supplier_address: list[str]
    invoice_number: str
    invoice_date: str
    currency: str
    lines: list[Line]
    style: str = "classic"
    total_override: float | None = None
    accent: str = "#2f5d7c"
    labels: dict[str, str] = field(default_factory=dict)
    footer: str = ""
    buyer: list[str] = field(
        default_factory=lambda: [
            "Ardent Studios Ltd",
            "14 Fenwick Row",
            "Manchester M2 4BQ",
            "United Kingdom",
        ]
    )

    @property
    def computed_total(self) -> float:
        return round(sum(line.amount for line in self.lines), 2)

    @property
    def stated_total(self) -> float:
        return self.total_override if self.total_override is not None else self.computed_total


EN = {
    "invoice": "INVOICE",
    "number": "Invoice number",
    "date": "Invoice date",
    "billto": "Bill to",
    "description": "Description",
    "qty": "Qty",
    "unit": "Unit price",
    "amount": "Amount",
    "total": "Total due",
    "currency": "Currency",
    "page": "Page",
    "continued": "continued overleaf",
}

ES = {
    "invoice": "FACTURA",
    "number": "Número de factura",
    "date": "Fecha de factura",
    "billto": "Facturar a",
    "description": "Descripción",
    "qty": "Cant.",
    "unit": "Precio unitario",
    "amount": "Importe",
    "total": "Total a pagar",
    "currency": "Moneda",
    "page": "Página",
    "continued": "continúa al dorso",
}


def money(value: float) -> str:
    return f"{value:,.2f}"


# --------------------------------------------------------------------------
# PDF rendering
# --------------------------------------------------------------------------


def draw_header(c: canvas.Canvas, inv: Invoice, labels: dict[str, str]) -> float:
    """Draw the supplier block and invoice meta. Returns the next free y."""
    y = PAGE_H - MARGIN
    accent = HexColor(inv.accent)

    if inv.style == "modern":
        c.setFillColor(accent)
        c.rect(0, PAGE_H - MARGIN * 0.9, PAGE_W, MARGIN * 0.9, stroke=0, fill=1)
        c.setFillColor(HexColor("#ffffff"))
        c.setFont("Body-Bold", 15)
        c.drawString(MARGIN, PAGE_H - MARGIN * 0.62, inv.supplier_printed)
        y = PAGE_H - MARGIN * 1.6
        c.setFillColor(MUTED)
        c.setFont("Body", 8.5)
        for part in inv.supplier_address:
            c.drawString(MARGIN, y, part)
            y -= 11
    else:
        body = "Serif" if inv.style == "serif" else "Body"
        c.setFillColor(accent)
        c.setFont(f"{body}-Bold", 16)
        c.drawString(MARGIN, y, inv.supplier_printed)
        y -= 16
        c.setFillColor(MUTED)
        c.setFont(body, 8.5)
        for part in inv.supplier_address:
            c.drawString(MARGIN, y, part)
            y -= 11

    body = "Serif" if inv.style == "serif" else "Body"
    right = PAGE_W - MARGIN
    c.setFillColor(INK)
    c.setFont(f"{body}-Bold", 20)
    c.drawRightString(right, PAGE_H - MARGIN - (14 if inv.style == "modern" else 2), labels["invoice"])

    meta_y = PAGE_H - MARGIN - (40 if inv.style == "modern" else 28)
    c.setFont(body, 9)
    for key, value in (
        (labels["number"], inv.invoice_number),
        (labels["date"], inv.invoice_date),
        (labels["currency"], inv.currency),
    ):
        c.setFillColor(MUTED)
        c.drawRightString(right - 90, meta_y, f"{key}")
        c.setFillColor(INK)
        c.drawRightString(right, meta_y, value)
        meta_y -= 13

    y = min(y, meta_y) - 22
    c.setFillColor(MUTED)
    c.setFont(body, 8)
    c.drawString(MARGIN, y, labels["billto"].upper())
    y -= 12
    c.setFillColor(INK)
    c.setFont(body, 9)
    for part in inv.buyer:
        c.drawString(MARGIN, y, part)
        y -= 11
    return y - 18


def table_columns() -> tuple[float, float, float, float]:
    right = PAGE_W - MARGIN
    return MARGIN, right - 200, right - 110, right


def draw_table_head(c: canvas.Canvas, inv: Invoice, y: float, labels: dict[str, str]) -> float:
    body = "Serif" if inv.style == "serif" else "Body"
    x_desc, x_qty, x_unit, x_amt = table_columns()
    c.setFillColor(MUTED)
    c.setFont(f"{body}-Bold", 8.5)
    c.drawString(x_desc, y, labels["description"].upper())
    c.drawRightString(x_qty, y, labels["qty"].upper())
    c.drawRightString(x_unit, y, labels["unit"].upper())
    c.drawRightString(x_amt, y, labels["amount"].upper())
    y -= 6
    c.setStrokeColor(RULE)
    c.setLineWidth(0.6)
    c.line(MARGIN, y, PAGE_W - MARGIN, y)
    return y - 14


def draw_line(c: canvas.Canvas, inv: Invoice, line: Line, y: float) -> float:
    body = "Serif" if inv.style == "serif" else "Body"
    x_desc, x_qty, x_unit, x_amt = table_columns()
    c.setFillColor(INK)
    c.setFont(body, 9)
    c.drawString(x_desc, y, line.description)
    qty = f"{line.quantity:g}"
    c.drawRightString(x_qty, y, qty)
    c.drawRightString(x_unit, y, money(line.unit_price))
    c.drawRightString(x_amt, y, money(line.amount))
    return y - 15


def draw_total(c: canvas.Canvas, inv: Invoice, y: float, labels: dict[str, str]) -> float:
    body = "Serif" if inv.style == "serif" else "Body"
    _, _, x_unit, x_amt = table_columns()
    y -= 4
    c.setStrokeColor(RULE)
    c.line(x_unit - 60, y, PAGE_W - MARGIN, y)
    y -= 16
    c.setFillColor(INK)
    c.setFont(f"{body}-Bold", 11)
    c.drawRightString(x_unit, y, labels["total"])
    c.drawRightString(x_amt, y, f"{inv.currency} {money(inv.stated_total)}")
    return y - 20


def draw_footer(c: canvas.Canvas, inv: Invoice, text: str) -> None:
    body = "Serif" if inv.style == "serif" else "Body"
    c.setFillColor(MUTED)
    c.setFont(body, 7.5)
    c.drawString(MARGIN, MARGIN * 0.6, text)


def render_single_page(inv: Invoice, labels: dict[str, str] | None = None) -> None:
    labels = labels or EN
    c = canvas.Canvas(str(OUT / inv.filename), pagesize=A4)
    c.setTitle(inv.invoice_number)
    y = draw_header(c, inv, labels)
    y = draw_table_head(c, inv, y, labels)
    for line in inv.lines:
        y = draw_line(c, inv, line, y)
    draw_total(c, inv, y, labels)
    draw_footer(c, inv, inv.footer)
    c.showPage()
    c.save()


def render_prose_charge(inv: Invoice, labels: dict[str, str] | None = None) -> None:
    """The last charge appears only as a sentence in the terms, never as a row.

    Nothing here is hard to see — the sentence is ordinary body text in the
    same ink as everything else. What makes it missable is that reading the
    table is a complete-looking answer, so a first pass stops there. Going
    back after the arithmetic fails is what finds it, which is exactly the
    recovery the workshop wants on screen.
    """
    labels = labels or EN
    c = canvas.Canvas(str(OUT / inv.filename), pagesize=A4)
    c.setTitle(inv.invoice_number)
    y = draw_header(c, inv, labels)
    y = draw_table_head(c, inv, y, labels)
    for line in inv.lines[:-1]:
        y = draw_line(c, inv, line, y)
    y = draw_total(c, inv, y, labels)

    charge = inv.lines[-1]
    y -= 24
    c.setFillColor(INK)
    c.setFont("Body-Bold", 9)
    c.drawString(MARGIN, y, "Terms and conditions")
    y -= 16
    c.setFillColor(MUTED)
    c.setFont("Body", 8.5)
    for text in [
        "1. Payment is due 30 days from the invoice date. Goods remain our property until paid for.",
        "2. Claims for shortage or damage must be made in writing within 5 working days of delivery.",
        f"3. {charge.description}: {charge.quantity:g} at {inv.currency} {money(charge.unit_price)},",
        f"   {inv.currency} {money(charge.amount)} in total. This charge is levied on this invoice and",
        f"   is included in the {labels['total'].lower()} shown above.",
        "4. Returns are accepted within 14 days in original packaging, carriage paid by the buyer.",
    ]:
        c.drawString(MARGIN, y, text)
        y -= 12

    draw_footer(c, inv, inv.footer)
    c.showPage()
    c.save()


def render_credit_line(inv: Invoice, labels: dict[str, str] | None = None) -> None:
    """One row is a credit, printed the way accounting departments print them.

    The amount shows as a positive number with a trailing CR rather than a
    minus sign. Nothing is hidden: every character is plainly legible. The trap
    is a reading one — take the row at its printed sign and the invoice is out
    by twice the credit.
    """
    labels = labels or EN
    c = canvas.Canvas(str(OUT / inv.filename), pagesize=A4)
    c.setTitle(inv.invoice_number)
    y = draw_header(c, inv, labels)
    y = draw_table_head(c, inv, y, labels)

    x_desc, x_qty, x_unit, x_amt = table_columns()
    for line in inv.lines:
        if line.amount >= 0:
            y = draw_line(c, inv, line, y)
            continue
        c.setFillColor(INK)
        c.setFont("Body", 9)
        c.drawString(x_desc, y, line.description)
        c.drawRightString(x_qty, y, f"{line.quantity:g}")
        c.drawRightString(x_unit, y, money(abs(line.unit_price)))
        c.drawRightString(x_amt, y, f"{money(abs(line.amount))} CR")
        y -= 16

    draw_total(c, inv, y, labels)
    draw_footer(c, inv, inv.footer)
    c.showPage()
    c.save()


def render_multipage(inv: Invoice, per_page: int, labels: dict[str, str] | None = None) -> None:
    """Line items run across several pages; the total appears only on the last."""
    labels = labels or EN
    c = canvas.Canvas(str(OUT / inv.filename), pagesize=A4)
    c.setTitle(inv.invoice_number)
    chunks = [inv.lines[i : i + per_page] for i in range(0, len(inv.lines), per_page)]
    for page_no, chunk in enumerate(chunks, start=1):
        last = page_no == len(chunks)
        if page_no == 1:
            y = draw_header(c, inv, labels)
        else:
            y = PAGE_H - MARGIN
            c.setFillColor(MUTED)
            c.setFont("Body", 8.5)
            c.drawString(MARGIN, y, f"{inv.supplier_printed} — {labels['number']} {inv.invoice_number}")
            y -= 24
        y = draw_table_head(c, inv, y, labels)
        for line in chunk:
            y = draw_line(c, inv, line, y)
        if last:
            draw_total(c, inv, y, labels)
        footer = f"{labels['page']} {page_no}/{len(chunks)}"
        if not last:
            footer += f" — {labels['continued']}"
        draw_footer(c, inv, footer if last else f"{footer}   {inv.footer}")
        c.showPage()
    c.save()


def render_missable_line(inv: Invoice, labels: dict[str, str] | None = None) -> None:
    """A trap layout: the last line item sits below the table rule, in the
    small print, formatted like a note rather than a row. It is a real line
    item and the stated total only reconciles when it is counted."""
    labels = labels or EN
    c = canvas.Canvas(str(OUT / inv.filename), pagesize=A4)
    c.setTitle(inv.invoice_number)
    y = draw_header(c, inv, labels)
    y = draw_table_head(c, inv, y, labels)
    for line in inv.lines[:-1]:
        y = draw_line(c, inv, line, y)

    hidden = inv.lines[-1]
    y -= 4
    c.setStrokeColor(RULE)
    c.line(MARGIN, y, PAGE_W - MARGIN, y)
    y -= 26

    x_desc, x_qty, x_unit, x_amt = table_columns()
    c.setFillColor(MUTED)
    c.setFont("Body", 7.5)
    note = f"Additional charge — {hidden.description}"
    assert pdfmetrics.stringWidth(note, "Body", 7.5) < x_qty - x_desc - 30, note
    c.drawString(x_desc, y, note)
    c.drawString(x_desc, y - 10, "Billed with this invoice and included in the total below.")
    c.drawRightString(x_qty, y, f"{hidden.quantity:g}")
    c.drawRightString(x_unit, y, money(hidden.unit_price))
    c.drawRightString(x_amt, y, money(hidden.amount))
    y -= 20

    draw_total(c, inv, y, labels)
    draw_footer(c, inv, inv.footer)
    c.showPage()
    c.save()


# --------------------------------------------------------------------------
# The scanned / photographed image
# --------------------------------------------------------------------------


def render_scan(inv: Invoice, filename: str) -> None:
    """Draw an invoice with Pillow, then rough it up so it reads as a phone
    photo: warm paper, uneven lighting, a slight rotation, grain and JPEG loss."""
    w, h = 1654, 2339  # A4 at 200 dpi
    img = Image.new("RGB", (w, h), (252, 250, 245))
    d = ImageDraw.Draw(img)

    def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
        return ImageFont.truetype(str(DEJAVU / name), size)

    m = 140
    y = m
    d.text((m, y), inv.supplier_printed, font=font(44, True), fill=(30, 30, 40))
    d.text((w - m - 320, y - 6), "INVOICE", font=font(52, True), fill=(30, 30, 40))
    y += 58
    for part in inv.supplier_address:
        d.text((m, y), part, font=font(24), fill=(90, 90, 90))
        y += 32

    meta_y = m + 70
    for key, value in (
        ("Invoice number", inv.invoice_number),
        ("Invoice date", inv.invoice_date),
        ("Currency", inv.currency),
    ):
        d.text((w - m - 460, meta_y), key, font=font(24), fill=(120, 120, 120))
        d.text((w - m - 200, meta_y), value, font=font(24), fill=(40, 40, 40))
        meta_y += 36

    y = max(y, meta_y) + 50
    d.text((m, y), "BILL TO", font=font(22), fill=(120, 120, 120))
    y += 34
    for part in inv.buyer:
        d.text((m, y), part, font=font(24), fill=(40, 40, 40))
        y += 32

    y += 50
    x_qty, x_unit, x_amt = w - m - 540, w - m - 300, w - m
    d.text((m, y), "DESCRIPTION", font=font(22, True), fill=(120, 120, 120))
    d.text((x_qty, y), "QTY", font=font(22, True), fill=(120, 120, 120), anchor="ra")
    d.text((x_unit, y), "UNIT PRICE", font=font(22, True), fill=(120, 120, 120), anchor="ra")
    d.text((x_amt, y), "AMOUNT", font=font(22, True), fill=(120, 120, 120), anchor="ra")
    y += 34
    d.line((m, y, w - m, y), fill=(180, 180, 180), width=2)
    y += 26

    for line in inv.lines:
        d.text((m, y), line.description, font=font(26), fill=(30, 30, 30))
        d.text((x_qty, y), f"{line.quantity:g}", font=font(26), fill=(30, 30, 30), anchor="ra")
        d.text((x_unit, y), money(line.unit_price), font=font(26), fill=(30, 30, 30), anchor="ra")
        d.text((x_amt, y), money(line.amount), font=font(26), fill=(30, 30, 30), anchor="ra")
        y += 42

    y += 14
    d.line((x_unit - 220, y, w - m, y), fill=(180, 180, 180), width=2)
    y += 30
    d.text((x_unit, y), "Total due", font=font(30, True), fill=(20, 20, 20), anchor="ra")
    d.text((x_amt, y), f"{inv.currency} {money(inv.stated_total)}", font=font(30, True), fill=(20, 20, 20), anchor="ra")
    y += 80
    d.text((m, y), inv.footer, font=font(20), fill=(130, 130, 130))

    # Roughen: uneven lighting, rotation, grain, soft focus, JPEG loss.
    rnd = random.Random(7)
    shade = Image.new("L", (w, h), 255)
    sd = ImageDraw.Draw(shade)
    sd.ellipse((-w // 2, -h // 3, int(w * 1.2), int(h * 0.9)), fill=255)
    for i in range(30):
        band = int(h * 0.62) + i * int(h * 0.012)
        if band < h:
            sd.rectangle((0, band, w, h), fill=max(230, 255 - i))
    shade = shade.filter(ImageFilter.GaussianBlur(180))
    img = Image.composite(img, Image.new("RGB", (w, h), (150, 146, 138)), shade)

    grain = Image.new("L", (w, h))
    grain.putdata([rnd.gauss(128, 7) for _ in range(w * h)])
    img = Image.blend(img, Image.merge("RGB", (grain, grain, grain)), 0.06)

    img = img.rotate(-1.4, resample=Image.BICUBIC, expand=True, fillcolor=(46, 44, 42))
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    img.save(OUT / filename, "JPEG", quality=62)


# --------------------------------------------------------------------------
# The corpus
# --------------------------------------------------------------------------


def build() -> list[tuple[str, Invoice]]:
    invoices: list[tuple[str, Invoice]] = []

    clean_northwind = Invoice(
        filename="01-northwind-clean.pdf",
        supplier_printed="Northwind Paper Supplies AB",
        supplier_address=["Kungsgatan 44", "111 35 Stockholm", "Sweden", "Org. no 556123-4567"],
        invoice_number="NW-2026-0412",
        invoice_date="2026-01-14",
        currency="SEK",
        accent="#2f5d7c",
        footer="Payment terms 30 days net. Bankgiro 123-4567.",
        lines=[
            Line("A4 copy paper, 80 gsm, box of 5 reams", 12, 289.00),
            Line("A3 copy paper, 100 gsm, box of 5 reams", 4, 512.50),
            Line("Recycled envelopes C4, pack of 250", 6, 174.90),
            Line("Delivery, Stockholm inner city", 1, 350.00),
        ],
    )
    invoices.append(("classic", clean_northwind))

    clean_brightline = Invoice(
        filename="02-brightline-clean.pdf",
        supplier_printed="Brightline Office Interiors",
        supplier_address=["Keizersgracht 210", "1016 DX Amsterdam", "Netherlands", "VAT NL812345678B01"],
        invoice_number="BOI/2026/0087",
        invoice_date="2026-02-03",
        currency="EUR",
        style="modern",
        accent="#1f6f5c",
        footer="Prices are tax inclusive. Please quote the invoice number on payment.",
        lines=[
            Line("Height-adjustable desk, 160x80, oak", 8, 649.00),
            Line("Task chair, mesh back, lumbar support", 8, 312.75),
            Line("Assembly and installation, per hour", 6, 78.00),
        ],
    )
    invoices.append(("modern", clean_brightline))

    clean_cascade = Invoice(
        filename="03-cascade-clean.pdf",
        supplier_printed="Cascade Cloud Services Inc.",
        supplier_address=["1200 Harbor Way, Suite 400", "Seattle, WA 98104", "United States"],
        invoice_number="CCS-88214",
        invoice_date="2026-02-28",
        currency="USD",
        style="serif",
        accent="#4a3f6b",
        footer="Billed monthly in arrears. Questions: billing@cascadecloud.example",
        lines=[
            Line("Managed Postgres, 4 vCPU cluster, monthly", 3, 420.00),
            Line("Object storage, per TB-month", 18.5, 21.40),
            Line("Egress bandwidth, per TB", 7.25, 68.00),
            Line("Support plan, business tier", 1, 750.00),
            Line("Dedicated onboarding session", 2, 195.00),
        ],
    )
    invoices.append(("serif", clean_cascade))

    # The centrepiece. Line arithmetic is internally correct, but the stated
    # total is 1,400.00 above the sum of the lines. Irreconcilable by design.
    rigged = Invoice(
        filename="04-halden-rigged-total.pdf",
        supplier_printed="Halden Industrial Fasteners AS",
        supplier_address=["Storgata 17", "1767 Halden", "Norway", "Org. nr 987 654 321 MVA"],
        invoice_number="HIF-2026-1155",
        invoice_date="2026-03-09",
        currency="NOK",
        accent="#8a4b2a",
        footer="Payment terms 14 days net. Late payment interest 9.25% per annum.",
        lines=[
            Line("Hex bolt M10x60, galvanised, box of 100", 24, 189.00),
            Line("Hex nut M10, galvanised, box of 250", 18, 96.50),
            Line("Washer M10, stainless, box of 500", 10, 142.00),
            Line("Threaded rod M12, 1 m, box of 10", 6, 388.00),
            Line("Freight, pallet delivery", 1, 1250.00),
        ],
    )
    rigged.total_override = round(rigged.computed_total + 1400.00, 2)
    invoices.append(("rigged-total", rigged))

    # The recoverable variant: the last line item is rendered below the table
    # rule as small print, so a first pass tends to miss it and the total does
    # not reconcile. Re-reading the document finds it and the sum then matches.
    missable = Invoice(
        filename="05-vertex-missable-line.pdf",
        supplier_printed="Vertex Packaging Group Ltd",
        supplier_address=["Unit 9, Barton Trade Park", "Sheffield S9 1XH", "United Kingdom"],
        invoice_number="VPG-046-2026",
        invoice_date="2026-03-17",
        currency="GBP",
        accent="#2f5d7c",
        footer="Pallet deposits are refunded on return of undamaged pallets.",
        lines=[
            Line("Double-wall carton 600x400x400, bundle of 20", 35, 42.60),
            Line("Polythene void fill, 500 m roll", 9, 88.00),
            Line("Printed packing tape, 66 m, box of 36", 4, 61.25),
            Line("Pallet deposit, standard euro pallet", 12, 18.50),
        ],
    )
    invoices.append(("missable", missable))

    multipage_lines = [
        Line(f"Pallet freight, {city} depot, week {wk:02d}", qty, price)
        for city, wk, qty, price in [
            ("Hamburg", 2, 3, 412.00), ("Bremen", 2, 1, 388.50), ("Hannover", 3, 4, 401.25),
            ("Leipzig", 3, 2, 455.00), ("Dresden", 4, 1, 470.75), ("Nürnberg", 4, 5, 398.00),
            ("Stuttgart", 5, 2, 434.60), ("München", 5, 3, 449.90), ("Köln", 6, 6, 377.40),
            ("Düsseldorf", 6, 2, 383.15), ("Essen", 7, 4, 369.80), ("Dortmund", 7, 1, 372.00),
            ("Frankfurt", 8, 5, 418.30), ("Mainz", 8, 2, 402.45), ("Kassel", 9, 3, 391.70),
            ("Erfurt", 9, 1, 407.05), ("Magdeburg", 10, 2, 425.90), ("Rostock", 10, 4, 462.35),
            ("Kiel", 11, 1, 478.20), ("Lübeck", 11, 3, 441.55), ("Osnabrück", 12, 2, 386.90),
            ("Münster", 12, 5, 379.25),
        ]
    ]
    multipage_lines.append(Line("Fuel surcharge, quarter 1, 4.5% of freight", 1, 1897.44))
    multipage = Invoice(
        filename="06-meridian-multipage.pdf",
        supplier_printed="Meridian Logistics Partners GmbH",
        supplier_address=["Hafenstraße 88", "20359 Hamburg", "Germany", "USt-IdNr DE123456789"],
        invoice_number="MLP-2026-Q1-0033",
        invoice_date="2026-04-02",
        currency="EUR",
        accent="#3a5a40",
        footer="Consolidated quarterly statement. Payment terms 30 days net.",
        lines=multipage_lines,
    )
    invoices.append(("multipage", multipage))

    scan = Invoice(
        filename="07-tallgrass-scan.jpg",
        supplier_printed="Tallgrass Print & Signage",
        supplier_address=["4102 W Prairie Ave", "Lincoln, NE 68522", "United States"],
        invoice_number="TG-5591",
        invoice_date="2026-02-19",
        currency="USD",
        footer="Thank you for your business. Payment due on receipt.",
        lines=[
            Line("Foam board sign, 24x36, full colour", 15, 38.50),
            Line("Vinyl banner, 3x8 ft, hemmed and grommeted", 4, 96.00),
            Line("Roll-up banner stand with print", 2, 214.75),
            Line("Setup and artwork proofing", 1, 125.00),
        ],
    )
    invoices.append(("scan", scan))

    # Spanish layout. Tax is folded into the unit prices and there is no
    # separate IVA line, because the record schema has no tax field and a
    # stray tax row would fail validation for the wrong reason.
    spanish = Invoice(
        filename="08-almendra-spanish.pdf",
        supplier_printed="Almendra Suministros Industriales S.L.",
        supplier_address=["Calle Mayor 118, 2ºB", "28013 Madrid", "España", "CIF B-87654321"],
        invoice_number="FRA-2026-00291",
        invoice_date="2026-03-24",
        currency="EUR",
        accent="#8c2f39",
        footer="Importes con IVA incluido. Forma de pago: transferencia a 30 días.",
        buyer=["Ardent Studios Ltd", "Sucursal en España", "Calle Balmes 45", "08007 Barcelona"],
        lines=[
            Line("Guantes de nitrilo, talla L, caja de 100", 30, 14.85),
            Line("Gafas de protección, policarbonato", 24, 9.40),
            Line("Casco de seguridad, blanco, EN 397", 18, 22.30),
            Line("Botas de seguridad S3, par", 12, 68.95),
            Line("Portes y embalaje", 1, 45.00),
        ],
    )
    invoices.append(("spanish", spanish))

    # Supplier that is deliberately absent from data/vendor_registry.json, so
    # the lookup misses and the record saves with a null supplier_id.
    unknown = Invoice(
        filename="09-unknown-supplier.pdf",
        supplier_printed="Fairhaven Instrument Repair",
        supplier_address=["27 Dock Lane", "Bristol BS1 6TE", "United Kingdom"],
        invoice_number="FIR-2026-0074",
        invoice_date="2026-04-11",
        currency="GBP",
        style="modern",
        accent="#4a4a4a",
        footer="First-time supplier. Remittance advice to accounts@fairhaven.example",
        lines=[
            Line("Calibration, bench multimeter", 5, 145.00),
            Line("Replacement probe set", 3, 62.40),
            Line("Collection and return courier", 1, 38.00),
        ],
    )
    invoices.append(("unknown", unknown))

    # The workshop centrepiece. The table's three rows look like the whole
    # invoice, but a fourth charge is stated in the terms as a sentence and is
    # inside the total. Read the table alone and you are short 480.00; read the
    # terms and the invoice reconciles exactly.
    prose = Invoice(
        filename="10-ridgeway-terms-charge.pdf",
        supplier_printed="Ridgeway Facilities Management",
        supplier_address=["Kestrel House, 4 Gantry Way", "Leeds LS11 5RT", "United Kingdom"],
        invoice_number="RFM-2026-0918",
        invoice_date="2026-03-30",
        currency="GBP",
        accent="#3d6b4f",
        footer="Registered in England 04482201. All charges are stated inclusive of tax.",
        lines=[
            Line("Monthly cleaning contract, Fenwick Row office", 1, 2480.00),
            Line("Window cleaning, external, quarterly visit", 2, 315.00),
            Line("Consumables restock, washroom and kitchen", 6, 74.50),
            Line("Out-of-hours callout surcharge", 4, 120.00),
        ],
    )
    invoices.append(("prose-charge", prose))

    # A credit row printed as "620.00 CR" rather than with a minus sign. Take
    # the sign as printed and the invoice is out by twice the credit; read the
    # CR and it reconciles. The failure is a reading of accounting convention,
    # not a failure to see the characters.
    credit = Invoice(
        filename="11-kestrel-credit-line.pdf",
        supplier_printed="Kestrel Analytics LLC",
        supplier_address=["2200 Harbor Steps, Suite 610", "Seattle, WA 98101", "United States"],
        invoice_number="KA-2026-0331",
        invoice_date="2026-03-31",
        currency="USD",
        accent="#4a3f7a",
        footer="Credits are applied against the current invoice and are not refundable in cash.",
        lines=[
            Line("Data pipeline support retainer, March", 1, 3200.00),
            Line("Ad-hoc analyst hours, March", 12, 145.00),
            Line("Dashboard licence seats, monthly", 8, 62.50),
            Line("Credit, March service level rebate", 1, -620.00),
        ],
    )
    invoices.append(("credit-line", credit))

    return invoices


NOTES = {
    "01-northwind-clean.pdf": "Clean single page. Registry hit on an alias. Validation passes.",
    "02-brightline-clean.pdf": "Clean single page, different visual template. Registry hit on an alias.",
    "03-cascade-clean.pdf": "Clean single page, serif template, fractional quantities. Registry hit on an alias.",
    "04-halden-rigged-total.pdf": "The rigged invoice. Line arithmetic is correct, the stated total is 1,400.00 too high. Irreconcilable from the document alone.",
    "05-vertex-missable-line.pdf": "Recoverable variant. The pallet deposit line sits below the table rule in small print; miss it and the total does not reconcile, re-read and it does.",
    "06-meridian-multipage.pdf": "Three pages, 23 line items, total only on the last page.",
    "07-tallgrass-scan.jpg": "Photographed page rather than a PDF: rotated, grainy, unevenly lit, JPEG artifacts.",
    "08-almendra-spanish.pdf": "Spanish layout and labels. Tax is inside the unit prices, no separate IVA row.",
    "09-unknown-supplier.pdf": "Supplier absent from the vendor registry. Lookup misses and the record saves with a null supplier_id.",
    "11-kestrel-credit-line.pdf": "A credit row printed as \"620.00 CR\" instead of a negative number. Read the sign as printed and the invoice is out by 1,240.00; read the CR and it reconciles.",
    "10-ridgeway-terms-charge.pdf": "The workshop centrepiece. A fourth charge of 480.00 is stated as a sentence in the terms rather than as a table row, and is inside the total. The table alone comes up 480.00 short; the terms reconcile it exactly.",
}


def write_expectations(invoices: list[tuple[str, Invoice]]) -> None:
    import json

    payload = [
        {
            "file": inv.filename,
            "purpose": NOTES[inv.filename],
            "supplier_printed": inv.supplier_printed,
            "invoice_number": inv.invoice_number,
            "invoice_date": inv.invoice_date,
            "currency": inv.currency,
            "line_count": len(inv.lines),
            "line_sum": inv.computed_total,
            "stated_total": inv.stated_total,
            "validation_passes": inv.stated_total == inv.computed_total,
        }
        for _, inv in invoices
    ]
    (OUT / "expected.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def main() -> None:
    register_fonts()
    OUT.mkdir(parents=True, exist_ok=True)
    invoices = build()
    write_expectations(invoices)
    for kind, inv in invoices:
        if kind == "multipage":
            render_multipage(inv, per_page=10)
        elif kind == "missable":
            render_missable_line(inv)
        elif kind == "prose-charge":
            render_prose_charge(inv)
        elif kind == "credit-line":
            render_credit_line(inv)
        elif kind == "scan":
            render_scan(inv, inv.filename)
        elif kind == "spanish":
            render_single_page(inv, ES)
        else:
            render_single_page(inv)
        gap = round(inv.stated_total - inv.computed_total, 2)
        flag = "  <-- RIGGED" if gap else ""
        print(
            f"{inv.filename:32} lines={len(inv.lines):3d} "
            f"sum={money(inv.computed_total):>12} stated={money(inv.stated_total):>12}{flag}"
        )


if __name__ == "__main__":
    main()
