import json

import pytest

from invoice_agent import store


@pytest.fixture(autouse=True)
def local_backend(tmp_path, monkeypatch):
    """Every test here runs the laptop backend, in a directory of its own."""
    monkeypatch.delenv("FIRESTORE_DATABASE", raising=False)
    monkeypatch.delenv("INVOICE_BUCKET", raising=False)
    monkeypatch.setattr(store, "LOCAL_PATH", str(tmp_path / "records.jsonl"))
    monkeypatch.setattr(store, "LOCAL_ARCHIVE", str(tmp_path / "archive"))


def record(invoice_number="INV-1", total=100.0):
    return {
        "supplier_name": "Ridgeway Supplies",
        "supplier_id": "SUP-001",
        "invoice_number": invoice_number,
        "invoice_date": "2026-01-05",
        "currency": "EUR",
        "line_items": [],
        "total": total,
    }


def test_the_store_stamps_the_metadata_the_model_does_not_own():
    store.save(record(), validation_passed=False, source_uri="gs://bucket/x.pdf")
    stored = store.read_all()[0]
    assert stored["validation_passed"] is False
    assert stored["source_uri"] == "gs://bucket/x.pdf"
    assert stored["extracted_at"].endswith("+00:00")


def test_a_failing_invoice_is_still_saved():
    document_id = store.save(record(total=12671.0), validation_passed=False)
    assert document_id
    assert len(store.read_all()) == 1


def test_records_come_back_newest_first():
    store.save(record("INV-1"), validation_passed=True)
    store.save(record("INV-2"), validation_passed=True)
    assert [r["invoice_number"] for r in store.read_all()] == ["INV-2", "INV-1"]


def test_an_empty_store_is_not_an_error():
    assert store.read_all() == []


def test_every_record_carries_an_id_the_page_can_key_on():
    store.save(record(), validation_passed=True)
    assert store.read_all()[0]["id"]


def test_the_archive_keeps_the_bytes_and_the_extension():
    uri = store.archive_source(b"%PDF-1.4 fake", "application/pdf", "ridgeway.PDF")
    assert uri.startswith("file://")
    path = uri[len("file://") :]
    assert path.endswith(".pdf")
    with open(path, "rb") as handle:
        assert handle.read() == b"%PDF-1.4 fake"


def test_the_archive_falls_back_to_the_mime_type_when_there_is_no_filename():
    assert store.archive_source(b"x", "image/png", None).endswith(".png")
    assert store.archive_source(b"x", "application/weird", None).endswith(".bin")


def test_the_local_file_stays_readable_by_hand():
    store.save(record(), validation_passed=True)
    with open(store.LOCAL_PATH, encoding="utf-8") as handle:
        assert json.loads(handle.readline())["invoice_number"] == "INV-1"


def test_the_backend_switches_on_the_firestore_database_variable(monkeypatch):
    assert store.cloud() is False
    monkeypatch.setenv("FIRESTORE_DATABASE", "invoices")
    assert store.cloud() is True
