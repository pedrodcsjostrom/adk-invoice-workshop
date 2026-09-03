"""The three tools the agent is given.

Docstrings here are prompt text: the model reads them to decide when to call
each tool and what to pass. Keep them short, imperative and honest about what
the tool does not do.
"""

from google.adk.tools.tool_context import ToolContext

from invoice_agent import registry, store, validation
from invoice_agent.models import InvoiceRecord, LineItem


def lookup_supplier(supplier_name: str) -> dict:
    """Look up a supplier in the company supplier registry.

    Call this once, with the supplier name exactly as printed on the invoice.
    The registry matches common aliases and legal suffixes for you.

    Args:
        supplier_name: The supplier name exactly as printed on the invoice.
    """
    entry = registry.find(supplier_name)
    if entry is None:
        return {
            "found": False,
            "searched_for": supplier_name,
            "suggestion": registry.nearest(supplier_name),
        }
    return {
        "found": True,
        "supplier_id": entry["supplier_id"],
        "name": entry["name"],
        "country": entry["country"],
        "currency": entry["currency"],
        "status": entry["status"],
    }


# ===== FILL-IN 1 of 2 — invoice_agent/tools.py — check_invoice_arithmetic =====
#
# Write the arithmetic tool. The signature is given; the docstring and the body
# are yours.
#
# The docstring is the point. It is prompt text, not documentation: the model
# reads it to decide when to call this tool and what to pass. Say what the tool
# checks, say what it does not do, and give it an `Args:` section — ADK feeds
# that to the model as the parameter descriptions.
#
# The body is one line. `validation.check(line_items, total)` is already
# written and already imported.
#
# Check yourself:  uv run pytest tests/test_gap_arithmetic.py    (~5 seconds)
#
# Behind? One command:  cp solutions/tools.py invoice_agent/tools.py


def check_invoice_arithmetic(line_items: list[LineItem], total: float) -> dict:
    """Check that the invoice adds up, to the cent.

    Verifies that every line's quantity times unit price equals its printed
    amount, and that the line amounts sum to the printed total. Pass the numbers
    exactly as you read them off the document. Reports what disagrees; it does
    not correct anything.

    Args:
        line_items: Every charge line you read off the invoice.
        total: The total as printed on the invoice.
    """
    return validation.check(line_items, total)


# ===== END FILL-IN 1 ==========================================================


def save_invoice_record(record: InvoiceRecord, tool_context: ToolContext) -> dict:
    """Save the finished invoice record to the invoice store.

    Call this once, last, after the arithmetic check and the supplier lookup.
    The store runs its own arithmetic check and files the record either way, so
    an invoice that does not add up is still saved, flagged as failing.

    Args:
        record: The completed invoice record.
    """
    result = validation.check(record.line_items, record.total)
    source_uri = _archive_uploaded_document(tool_context)
    document_id = store.save(record.model_dump(mode="json"), result["ok"], source_uri)
    return {
        "saved": True,
        "document_id": document_id,
        "validation_passed": result["ok"],
        "source_uri": source_uri,
    }


def _archive_uploaded_document(tool_context: ToolContext) -> str | None:
    """Copy the document this turn was given into the archive, if there was one.

    The upload never reaches the tool as an argument — it reaches the model as
    inline bytes on the user's message — so the tool reads it back off the
    context. Archiving is best effort: a stored record with no original beats a
    failed save, and the room should not see a stack trace because a bucket
    was missing.
    """
    content = getattr(tool_context, "user_content", None)
    for part in getattr(content, "parts", None) or []:
        blob = getattr(part, "inline_data", None)
        if blob is None or not blob.data:
            continue
        try:
            return store.archive_source(
                blob.data, blob.mime_type or "application/octet-stream", blob.display_name
            )
        except Exception as error:  # noqa: BLE001 - never fail the save
            print(f"[archive] skipped: {error}")
            return None
    return None
