import json
import os

import pytest

from invoice_agent import registry
from invoice_agent.tools import lookup_supplier

EXPECTED_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "samples",
    "invoices",
    "expected.json",
)
with open(EXPECTED_PATH, encoding="utf-8") as handle:
    EXPECTED = json.load(handle)


@pytest.mark.parametrize(
    "printed",
    [e["supplier_printed"] for e in EXPECTED if e["file"] != "09-unknown-supplier.pdf"],
)
def test_every_corpus_supplier_resolves_as_printed(printed):
    # The model extracts the name as printed, suffix and all. That string is
    # what the registry has to match, so the corpus is the test data.
    assert registry.find(printed) is not None


def test_the_unknown_supplier_misses():
    result = lookup_supplier("Fairhaven Instrument Repair")
    assert result["found"] is False
    assert result["searched_for"] == "Fairhaven Instrument Repair"


def test_a_hit_carries_the_status_through():
    result = lookup_supplier("Sablefield Catering Ltd")
    assert result["found"] is True
    assert result["supplier_id"] == "SUP-0007"
    assert result["status"] == "on_hold"


def test_matching_ignores_case_punctuation_and_legal_suffix():
    for spelling in [
        "HALDEN INDUSTRIAL FASTENERS AS",
        "halden industrial fasteners",
        "Halden Industrial Fasteners, A.S.",
    ]:
        assert registry.find(spelling)["supplier_id"] == "SUP-0004"
