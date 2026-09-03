"""Generate the sample invoice PDFs the end-to-end slice is smoke-tested with.

Two files:
  sample_invoice.pdf  — a small, correct invoice
  big_invoice.pdf     — the same invoice padded with a high-resolution image to
                        roughly 10 MB, to probe the developer UI upload ceiling
"""

import os
import random
import sys

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples")

VENDOR = "Northwind Supplies"
INVOICE_NUMBER = "INV-2026-0412"
INVOICE_DATE = "2026-08-14"
CURRENCY = "EUR"
LINES = [
    ("A4 copier paper, 80gsm, box of 5 reams", 12, 24.50),
    ("Whiteboard markers, assorted, pack of 10", 8, 11.20),
    ("Desk lamp, LED, adjustable arm", 3, 46.00),
    ("Ergonomic keyboard tray", 2, 89.95),
]


def draw_invoice(c: canvas.Canvas) -> None:
    c.setFont("Helvetica-Bold", 20)
    c.drawString(20 * mm, 275 * mm, VENDOR)
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, 268 * mm, "14 Harbour Road, Rotterdam, Netherlands")
    c.drawString(20 * mm, 263 * mm, "VAT NL8241 9932 B01")

    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * mm, 248 * mm, "INVOICE")
    c.setFont("Helvetica", 11)
    c.drawString(20 * mm, 240 * mm, f"Invoice number: {INVOICE_NUMBER}")
    c.drawString(20 * mm, 234 * mm, f"Invoice date: {INVOICE_DATE}")
    c.drawString(20 * mm, 228 * mm, "Payment terms: net 30")
    c.drawString(120 * mm, 240 * mm, "Bill to:")
    c.drawString(120 * mm, 234 * mm, "Meridian Analytics BV")
    c.drawString(120 * mm, 228 * mm, "Amsterdam, Netherlands")

    y = 210 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(20 * mm, y, "Description")
    c.drawRightString(130 * mm, y, "Qty")
    c.drawRightString(155 * mm, y, "Unit price")
    c.drawRightString(190 * mm, y, "Amount")
    c.line(20 * mm, y - 2 * mm, 190 * mm, y - 2 * mm)

    c.setFont("Helvetica", 10)
    total = 0.0
    for description, qty, unit in LINES:
        y -= 9 * mm
        amount = round(qty * unit, 2)
        total += amount
        c.drawString(20 * mm, y, description)
        c.drawRightString(130 * mm, y, str(qty))
        c.drawRightString(155 * mm, y, f"{unit:,.2f}")
        c.drawRightString(190 * mm, y, f"{amount:,.2f}")

    y -= 12 * mm
    c.line(120 * mm, y + 5 * mm, 190 * mm, y + 5 * mm)
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(155 * mm, y, f"Total ({CURRENCY})")
    c.drawRightString(190 * mm, y, f"{total:,.2f}")


def write_small(path: str) -> None:
    c = canvas.Canvas(path, pagesize=A4)
    draw_invoice(c)
    c.showPage()
    c.save()


def write_big(path: str, target_bytes: int = 10 * 1024 * 1024) -> None:
    """Same invoice, then noise-image pages until the file clears the target."""
    from PIL import Image

    rng = random.Random(7)
    size = 1200

    # Each page needs its own image: reportlab embeds a repeated image once, so
    # reusing one noise page leaves the file stuck at a few MB.
    c = canvas.Canvas(path, pagesize=A4)
    draw_invoice(c)
    c.showPage()
    per_page = 5_400_000  # measured: a 1200px noise page embeds at ~5.4 MB
    for _ in range(max(1, -(-target_bytes // per_page))):
        noise = Image.frombytes("RGB", (size, size), rng.randbytes(size * size * 3))
        c.drawImage(ImageReader(noise), 0, 0, width=A4[0], height=A4[1])
        c.showPage()
    c.save()


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    small = os.path.join(OUT_DIR, "sample_invoice.pdf")
    write_small(small)
    print(f"{small}  {os.path.getsize(small):,} bytes")

    if "--big" in sys.argv:
        big = os.path.join(OUT_DIR, "big_invoice.pdf")
        write_big(big)
        print(f"{big}  {os.path.getsize(big):,} bytes")


if __name__ == "__main__":
    main()
