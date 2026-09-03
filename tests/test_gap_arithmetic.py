"""Fill-in one's five-second check.

This is the attendee's own feedback loop, not a repo health test: on a fresh
clone it FAILS, and it goes green the moment `check_invoice_arithmetic` is
written. Run it with

    uv run pytest tests/test_gap_arithmetic.py

It never talks to Vertex AI, Firestore or the network. A wrong tool signature
otherwise surfaces minutes later as a confusing model-side error, which is the
worst way to lose an attendee.
"""

import inspect

import pytest

from invoice_agent.models import LineItem


def _tool():
    from invoice_agent.tools import check_invoice_arithmetic

    return check_invoice_arithmetic


def test_the_tool_exists_and_is_written():
    """It is a function, and it is not still the stub."""
    tool = _tool()
    assert callable(tool)
    try:
        tool(line_items=[], total=0.0)
    except NotImplementedError:
        pytest.fail(
            "check_invoice_arithmetic is still the stub — write it in "
            "invoice_agent/tools.py, or run: cp solutions/tools.py invoice_agent/tools.py"
        )
    except TypeError as error:
        pytest.fail(f"check_invoice_arithmetic does not take the two named parameters: {error}")


def test_it_takes_the_two_named_parameters():
    """The model calls this tool by parameter name, so the names are the contract."""
    parameters = list(inspect.signature(_tool()).parameters)
    assert parameters == ["line_items", "total"], (
        f"expected parameters ['line_items', 'total'], found {parameters}"
    )


def test_the_docstring_is_prompt_text():
    """No docstring means the model is told nothing about when to call this."""
    docstring = inspect.getdoc(_tool()) or ""
    assert docstring.strip(), "check_invoice_arithmetic needs a docstring — the model reads it"
    assert "Args:" in docstring, (
        "the docstring needs an `Args:` section — ADK turns it into the "
        "parameter descriptions the model sees"
    )


def test_it_delegates_to_the_validator():
    """A mismatched invoice comes back flagged, with the gap named."""
    lines = [
        LineItem(description="Widgets", quantity=2, unit_price=100.0, amount=200.0),
        LineItem(description="Delivery", quantity=1, unit_price=50.0, amount=50.0),
    ]

    agreeing = _tool()(line_items=lines, total=250.0)
    assert agreeing["ok"] is True

    disagreeing = _tool()(line_items=lines, total=1650.0)
    assert disagreeing["ok"] is False
    assert disagreeing["total_error"]["expected"] == 250.0
    assert disagreeing["total_error"]["stated"] == 1650.0


def test_it_reports_rather_than_corrects():
    """The tool states facts. The recovery belongs to the instruction, not here."""
    lines = [LineItem(description="Widgets", quantity=2, unit_price=100.0, amount=999.0)]
    result = _tool()(line_items=lines, total=999.0)

    assert result["ok"] is False
    assert result["line_errors"][0]["expected"] == 200.0
    assert result["line_errors"][0]["stated"] == 999.0
