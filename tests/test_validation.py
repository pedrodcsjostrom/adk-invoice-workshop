from invoice_agent.models import LineItem
from invoice_agent.validation import check


def line(description="Widget", quantity=1.0, unit_price=100.0, amount=100.0):
    return LineItem(
        description=description, quantity=quantity, unit_price=unit_price, amount=amount
    )


def test_clean_invoice_passes():
    result = check([line(amount=100.0), line(quantity=2, amount=200.0)], 300.0)
    assert result["ok"] is True
    assert result["line_errors"] == []
    assert result["total_error"] is None


def test_supplier_rounding_within_a_cent_passes():
    # 3 x 33.335 is 100.005, printed as 100.01. One cent of tolerance, no more.
    result = check([line(quantity=3, unit_price=33.335, amount=100.01)], 100.01)
    assert result["ok"] is True


def test_the_rigged_total_is_reported_with_both_numbers():
    result = check([line(amount=11271.0)], 12671.0)
    assert result["ok"] is False
    assert result["total_error"] == {
        "expected": 11271.0,
        "stated": 12671.0,
        "difference": 1400.0,
    }


def test_a_bad_line_names_itself():
    result = check([line(), line(description="Freight", quantity=2, amount=150.0)], 250.0)
    assert result["line_errors"] == [
        {"index": 1, "description": "Freight", "expected": 200.0, "stated": 150.0}
    ]


def test_the_result_never_prescribes_a_fix():
    # The recovery belongs to the agent instruction, not to the tool.
    result = check([line(amount=11271.0)], 12671.0)
    assert set(result) == {"ok", "line_errors", "total_error"}
