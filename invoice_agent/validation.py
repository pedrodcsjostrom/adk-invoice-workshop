"""Arithmetic validation: does the invoice add up?

One chain of checks. Each line's quantity times unit price must equal its
printed amount, and the line amounts must sum to the printed total. Two numbers
agree when they are within one cent of each other, so ordinary supplier
rounding passes and the rigged invoice's 1,400.00 gap does not.

The result is facts only. It names the lines that disagree and the two numbers
that disagree, and says nothing about what to do next — the recovery belongs to
the agent's instruction, not to the tool.
"""

from invoice_agent.models import LineItem

CENT = 2


def agrees(expected: float, stated: float) -> bool:
    """Do two money amounts agree to within one cent?"""
    return round(abs(expected - stated), CENT) <= 0.01


def check(line_items: list[LineItem], total: float) -> dict:
    """Validate line arithmetic and the total. Never raises."""
    line_errors = []
    for index, line in enumerate(line_items):
        expected = round(line.quantity * line.unit_price, CENT)
        stated = round(line.amount, CENT)
        if not agrees(expected, stated):
            line_errors.append(
                {
                    "index": index,
                    "description": line.description,
                    "expected": expected,
                    "stated": stated,
                }
            )

    line_sum = round(sum(round(line.amount, CENT) for line in line_items), CENT)
    stated_total = round(total, CENT)
    total_error = None
    if not agrees(line_sum, stated_total):
        total_error = {
            "expected": line_sum,
            "stated": stated_total,
            "difference": round(stated_total - line_sum, CENT),
        }

    return {
        "ok": not line_errors and total_error is None,
        "line_errors": line_errors,
        "total_error": total_error,
    }
