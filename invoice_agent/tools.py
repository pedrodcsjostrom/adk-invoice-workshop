"""The three tools the agent is given.

Docstrings here are prompt text: the model reads them to decide when to call
each tool and what to pass. Keep them short, imperative and honest about what
the tool does not do.
"""

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


def save_invoice_record(record: InvoiceRecord) -> dict:
    """Save the finished invoice record to the invoice store.

    Call this once, last, after the arithmetic check and the supplier lookup.
    The store runs its own arithmetic check and files the record either way, so
    an invoice that does not add up is still saved, flagged as failing.

    Args:
        record: The completed invoice record.
    """
    result = validation.check(record.line_items, record.total)
    document_id = store.save(record.model_dump(mode="json"), result["ok"])
    return {
        "saved": True,
        "document_id": document_id,
        "validation_passed": result["ok"],
    }
