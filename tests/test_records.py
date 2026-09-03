from invoice_agent import records


def record(**overrides):
    base = {
        "id": "abc123",
        "supplier_name": "Ridgeway Supplies",
        "supplier_id": "SUP-001",
        "invoice_number": "INV-1042",
        "invoice_date": "2026-01-05",
        "currency": "EUR",
        "line_items": [{"description": "Widget"}, {"description": "Delivery"}],
        "total": 11271.0,
        "extracted_at": "2026-01-06T09:14:22.123456+00:00",
        "source_uri": "gs://invoice-agent-proj/2026-01-06/abc.pdf",
        "validation_passed": True,
    }
    return {**base, **overrides}


def test_the_empty_page_tells_you_what_to_do_next():
    page = records.render([])
    assert "No invoices filed yet" in page
    assert "<table" not in page


def test_a_record_shows_the_numbers_that_matter():
    page = records.render([record()])
    assert "Ridgeway Supplies" in page
    assert "INV-1042" in page
    assert "11,271.00" in page
    assert "gs://invoice-agent-proj/2026-01-06/abc.pdf" in page
    assert ">2</td>" in page  # line count


def test_a_failing_invoice_is_visibly_flagged():
    passed = records.render([record()])
    failed = records.render([record(validation_passed=False)])
    assert "class='pass'>yes" in passed
    assert "class='fail'>no" in failed


def test_an_unresolved_supplier_says_so_rather_than_showing_a_blank():
    page = records.render([record(supplier_id=None)])
    assert "unresolved" in page


def test_a_supplier_name_cannot_inject_markup():
    page = records.render([record(supplier_name="<script>alert(1)</script>")])
    assert "<script>" not in page
    assert "&lt;script&gt;" in page


def test_the_page_survives_a_record_missing_fields():
    page = records.render([{"id": "x"}])
    assert "<table" in page
