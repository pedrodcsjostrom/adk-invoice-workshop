"""The records page: everything the agent has filed, one table, no JavaScript.

Server-rendered on purpose. The page reads Firestore through the Cloud Run
service's own identity, so there is nothing to sign into and no browser
credential to explain in a room of sixty people. If you can reach the agent, you
can read the records.
"""

from html import escape

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from invoice_agent import store

router = APIRouter()

STYLE = """\
body { font: 15px/1.5 system-ui, sans-serif; margin: 2rem auto; max-width: 70rem; }
h1 { font-size: 1.4rem; margin-bottom: 0.25rem; }
p.lede { color: #555; margin-top: 0; }
table { border-collapse: collapse; width: 100%; }
th, td { text-align: left; padding: 0.45rem 0.6rem; border-bottom: 1px solid #e3e3e3; }
th { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.04em; color: #555; }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
.pass { color: #1a7f37; }
.fail { color: #b3261e; font-weight: 600; }
.source { color: #666; font-size: 0.8rem; word-break: break-all; }
.empty { color: #666; padding: 2rem 0; }
"""

COLUMNS = ("Filed", "Supplier", "Invoice", "Date", "Lines", "Total", "Adds up", "Source")


@router.get("/records", response_class=HTMLResponse)
def records_page() -> str:
    """Every stored invoice record, newest first."""
    return render(store.read_all())


def render(records: list[dict]) -> str:
    """The whole page. Kept in one function so attendees can read it in one go."""
    if records:
        body = (
            "<table><thead><tr>"
            + "".join(f"<th>{column}</th>" for column in COLUMNS)
            + "</tr></thead><tbody>"
            + "".join(_row(record) for record in records)
            + "</tbody></table>"
        )
    else:
        body = (
            "<p class='empty'>No invoices filed yet. Analyse one in the agent UI, "
            "then reload this page.</p>"
        )

    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<title>Invoice records</title>"
        f"<style>{STYLE}</style></head><body>"
        "<h1>Invoice records</h1>"
        f"<p class='lede'>{len(records)} filed by the agent, newest first.</p>"
        f"{body}</body></html>"
    )


def _row(record: dict) -> str:
    passed = record.get("validation_passed")
    supplier = escape(str(record.get("supplier_name") or "—"))
    supplier_id = record.get("supplier_id")
    tag = escape(str(supplier_id)) if supplier_id else "unresolved"
    supplier = f"{supplier} <span class='source'>{tag}</span>"

    cells = [
        f"<td>{escape(str(record.get('extracted_at', ''))[:19].replace('T', ' '))}</td>",
        f"<td>{supplier}</td>",
        f"<td>{escape(str(record.get('invoice_number', '')))}</td>",
        f"<td>{escape(str(record.get('invoice_date', '')))}</td>",
        f"<td class='num'>{len(record.get('line_items') or [])}</td>",
        f"<td class='num'>{_money(record)}</td>",
        (
            "<td class='pass'>yes</td>"
            if passed
            else "<td class='fail'>no</td>"
        ),
        f"<td class='source'>{escape(str(record.get('source_uri') or '—'))}</td>",
    ]
    return "<tr>" + "".join(cells) + "</tr>"


def _money(record: dict) -> str:
    total = record.get("total")
    if total is None:
        return "—"
    return f"{total:,.2f}&nbsp;{escape(str(record.get('currency') or ''))}"
