"""The analyze endpoint, driven the way the upload page drives it: over HTTP.

Everything here goes through the application with FastAPI's test client, which
is the one seam these tests use. The runner, the agent, the document guard, the
tools and the store are all the real ones; only the model is faked, following
the `RecordingModel` pattern in `tests/test_guards.py` and extending it so it
can emit a tool call and so it reports what it was able to see.
"""

import json
from typing import AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from invoice_agent import agent, store, upload
from invoice_agent.guards import NO_DOCUMENT_MESSAGE
from server import app

DOCUMENT = b"%PDF-1.4 northwind"


class FilingModel(BaseLlm):
    """A model that checks the arithmetic, files one record and answers with it.

    The real agent in miniature: it calls `check_invoice_arithmetic` — once, or
    twice when `checks` says so, which is the re-read — then asks for
    `save_invoice_record`, then returns the record as the answer. The tools it
    calls are the real ones, so the trace summary issue #59 asks for is read off
    a real sequence of events rather than a stub.

    The supplier name is the display name of every document the request
    carried, so a test can see over HTTP what this model was shown. `lines`,
    `line_amount` and `total` are what make an invoice rigged: nine lines of
    thirty against a printed total of thirty is an invoice short of its own
    lines.

    `total_on_re_read` is the reading the model comes back with after a failed
    check. It exists so the two checks of a re-read say different things, which
    is the only way to prove the summary reports the second one rather than the
    first (issue #59).
    """

    model: str = "filing"
    calls: int = 0
    total: float = 30.0
    total_on_re_read: float | None = None
    lines: int = 1
    line_amount: float = 30.0
    checks: int = 1
    explodes: bool = False

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        self.calls += 1
        if self.explodes:
            raise RuntimeError("the model fell over")
        checked = _responses_to(llm_request, "check_invoice_arithmetic")
        total = self.total
        if checked and self.total_on_re_read is not None:
            total = self.total_on_re_read
        record = {
            "supplier_name": " and ".join(_documents_shown(llm_request)),
            "supplier_id": "SUP-001",
            "invoice_number": "INV-1042",
            "invoice_date": "2026-01-05",
            "currency": "EUR",
            "line_items": [
                {
                    "description": "Widget",
                    "quantity": 1,
                    "unit_price": self.line_amount,
                    "amount": self.line_amount,
                }
            ]
            * self.lines,
            "total": total,
        }
        if checked < self.checks:
            part = types.Part(
                function_call=types.FunctionCall(
                    name="check_invoice_arithmetic",
                    args={
                        "line_items": record["line_items"],
                        "total": record["total"],
                    },
                )
            )
        elif _responses_to(llm_request, "save_invoice_record"):
            part = types.Part(text=json.dumps(record))
        else:
            part = types.Part(
                function_call=types.FunctionCall(
                    name="save_invoice_record", args={"record": record}
                )
            )
        yield LlmResponse(content=types.Content(role="model", parts=[part]))


def _documents_shown(llm_request: LlmRequest) -> list[str]:
    """The display name of every document anywhere in the request."""
    return [
        part.inline_data.display_name
        for content in llm_request.contents or []
        for part in content.parts or []
        if part.inline_data is not None and part.inline_data.data
    ]


def _responses_to(llm_request: LlmRequest, tool: str) -> int:
    """How many times that tool has already answered in this run."""
    return sum(
        1
        for content in llm_request.contents or []
        for part in content.parts or []
        if part.function_response is not None and part.function_response.name == tool
    )


@pytest.fixture
def model(tmp_path, monkeypatch):
    """The real application, with a temp store and a fake model behind it.

    The store reads its paths into module constants at import, so a temp
    location has to be set on the module rather than in the environment.
    """
    monkeypatch.delenv("FIRESTORE_DATABASE", raising=False)
    monkeypatch.delenv("INVOICE_BUCKET", raising=False)
    monkeypatch.setattr(store, "LOCAL_PATH", str(tmp_path / "records.jsonl"))
    monkeypatch.setattr(store, "LOCAL_ARCHIVE", str(tmp_path / "archive"))

    fake = FilingModel()
    monkeypatch.setattr(agent.root_agent, "model", fake)
    return fake


@pytest.fixture
def client(model):
    with TestClient(app) as started:
        yield started


def _post(client, name="northwind.pdf", data=DOCUMENT, media_type="application/pdf"):
    return client.post("/analyze", files={"file": (name, data, media_type)})


def test_one_document_comes_back_as_one_record(client):
    body = _post(client).json()

    assert body["record"]["invoice_number"] == "INV-1042"
    assert body["record"]["total"] == 30.0
    assert body["validation_passed"] is True
    assert body["source_uri"].startswith("file://")
    assert body["message"] is None


def test_an_invoice_that_does_not_add_up_is_reported_as_failing(client, model):
    model.total = 240.0

    assert _post(client).json()["validation_passed"] is False


def test_the_filed_record_appears_on_the_records_page(client):
    filed = _post(client).json()

    page = client.get("/records").text

    assert "INV-1042" in page
    assert filed["source_uri"] in page


def test_each_request_runs_in_a_fresh_session(client, model):
    _post(client, name="first.pdf")

    second = _post(client, name="second.pdf").json()

    # The supplier name is every document the model was shown, so a document
    # carried over from the previous request would be named here.
    assert second["record"]["supplier_name"] == "second.pdf"
    # Three model calls a run: the arithmetic check, the save, the answer.
    assert model.calls == 6


def test_a_turn_with_no_document_bytes_is_still_refused(client, model):
    body = _post(client, data=b"").json()

    assert body["record"] is None
    assert body["message"] == NO_DOCUMENT_MESSAGE
    assert model.calls == 0


def test_the_uploaded_original_is_archived_as_uploaded(client):
    source_uri = _post(client).json()["source_uri"]

    path = source_uri.removeprefix("file://")
    assert open(path, "rb").read() == DOCUMENT
    assert path.endswith(".pdf")


# --- the limits, and failures that stay readable -------------------------------
#
# Issue #58. The claim these pin is that a document the agent cannot read costs
# nothing: the refusal happens before the run, which the fake model's call count
# is the only honest way to show. The limits themselves are read off the upload
# module, so a change to the constant moves the test with it rather than leaving
# a second copy of the number here to disagree with the first.


@pytest.mark.parametrize("media_type", upload.ALLOWED_MEDIA_TYPES)
def test_every_allowed_media_type_is_analysed(client, media_type):
    body = _post(client, media_type=media_type).json()

    assert body["record"]["invoice_number"] == "INV-1042"
    assert body["message"] is None


def test_a_media_type_off_the_allowlist_is_refused_before_the_model(client, model):
    response = _post(
        client, name="notes.txt", data=b"not an invoice", media_type="text/plain"
    )

    assert response.status_code == 200
    assert response.json()["record"] is None
    assert "PDF, PNG or JPEG" in response.json()["message"]
    assert model.calls == 0


def test_a_document_over_the_size_cap_is_refused_before_the_model(client, model):
    oversized = b"%" * (upload.MAX_DOCUMENT_BYTES + 1)

    response = _post(client, data=oversized)

    assert response.status_code == 200
    assert response.json()["record"] is None
    megabytes = upload.MAX_DOCUMENT_BYTES // (1024 * 1024)
    assert f"larger than {megabytes} MB" in response.json()["message"]
    assert model.calls == 0


def test_a_document_at_the_size_cap_is_still_analysed(client):
    at_the_cap = DOCUMENT + b" " * (upload.MAX_DOCUMENT_BYTES - len(DOCUMENT))

    assert _post(client, data=at_the_cap).json()["record"] is not None


def test_a_request_carrying_no_file_is_refused(client, model):
    response = client.post("/analyze")

    assert response.status_code == 200
    assert response.json()["record"] is None
    assert "No document arrived" in response.json()["message"]
    assert model.calls == 0


def test_a_run_that_raises_comes_back_as_a_readable_failure(client, model):
    model.explodes = True

    response = _post(client)

    # A red row, not a 500 and not a stack trace: the same keys a successful
    # result has, so the page renders it without special-casing.
    assert response.status_code == 200
    body = response.json()
    assert body.keys() == {
        "record", "validation_passed", "source_uri", "trace_summary", "message"
    }
    assert body["record"] is None
    assert "the model fell over" in body["message"]


# --- the trace summary ---------------------------------------------------------
#
# Issue #59. The claim these pin is that the re-read is visible on a deployed
# service: the summary counts real calls to the real arithmetic tool, so an
# invoice checked twice says so. The sentences are asserted whole, because the
# whole sentence is what is read off a projector.


def test_a_clean_invoice_reports_one_check_that_passed(client):
    assert _post(client).json()["trace_summary"] == "checked once, adds up"


def test_a_rigged_invoice_checked_twice_reports_the_second_check(client, model):
    # Nine lines of thirty against a printed total of thirty: the invoice is
    # short of its own lines by 240.00, and the instruction's re-read means the
    # agent checks a second time before filing it.
    model.lines = 9
    model.checks = 2

    body = _post(client).json()

    assert body["trace_summary"] == "checked twice, still short by 240.00"
    assert body["validation_passed"] is False


def test_the_summary_reports_the_second_check_and_not_the_first(client, model):
    """The one thing that separates this from counting the calls.

    The re-read comes back with a different total, so the two checks disagree.
    A summary built from the first check would say "short by 240.00"; the one
    the page shows has to say what the agent believed the second time.
    """
    model.lines = 9
    model.checks = 2
    model.total_on_re_read = 300.0

    assert _post(client).json()["trace_summary"] == "checked twice, still over by 30.00"


def test_the_rigged_invoice_reads_the_way_the_kit_says_it_does(client, model):
    """The exact sentence the host narrates at 0:42, on the real numbers.

    `04-halden-rigged-total.pdf` prints 12,671.00 over five lines coming to
    11,271.00. Its gap is the one number the run of show, the speaker notes and
    the runbook all quote, so it is pinned here rather than left to be read off
    a projector for the first time in front of the room.
    """
    model.lines = 5
    model.line_amount = 2254.2
    model.total = 12671.0
    model.checks = 2

    assert (
        _post(client).json()["trace_summary"] == "checked twice, still over by 1,400.00"
    )


def test_a_first_check_that_fails_is_reported_without_the_re_read(client, model):
    model.lines = 9

    assert _post(client).json()["trace_summary"] == "checked once, short by 240.00"


def test_an_invoice_over_its_lines_is_reported_as_over(client, model):
    model.total = 270.0

    assert _post(client).json()["trace_summary"] == "checked once, over by 240.00"


def test_a_run_with_no_arithmetic_check_says_so(client, model):
    model.checks = 0

    assert _post(client).json()["trace_summary"] == upload.NO_CHECK_SUMMARY


def test_a_refused_document_still_carries_a_summary(client):
    refused = _post(client, name="notes.txt", media_type="text/plain").json()
    guarded = _post(client, data=b"").json()

    assert refused["trace_summary"] == upload.NO_CHECK_SUMMARY
    assert guarded["trace_summary"] == upload.NO_CHECK_SUMMARY


def test_the_summary_is_a_sentence_and_not_a_payload(client, model):
    model.lines = 9
    model.checks = 2

    summary = _post(client).json()["trace_summary"]

    # One line of plain language: no JSON, no event objects, no field names off
    # the tool's result leaking through.
    assert "\n" not in summary
    assert not any(token in summary for token in "{}[]\"")
    assert not any(
        name in summary
        for name in ("ok", "line_errors", "total_error", "function_call", "difference")
    )


# --- the upload page -----------------------------------------------------------
#
# Issue #60. The claim these pin is that the root of the service serves a page
# an attendee can use and that it carries the same limits the server enforces,
# read off the constants rather than written out a second time here. The browser
# batch loop is deliberately not tested: it would need a browser, and the spec
# for #55 says so.


def test_the_service_root_serves_the_upload_page(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Invoice upload" in response.text
    assert "<input type='file'" in response.text


def test_the_upload_page_links_to_the_records_page(client):
    assert "href='/records'" in client.get("/").text


def test_the_upload_page_carries_the_limits_the_server_enforces(client):
    page = client.get("/").text

    assert str(upload.MAX_BATCH_DOCUMENTS) in page
    assert str(upload.MAX_DOCUMENT_BYTES) in page
    for media_type in upload.ALLOWED_MEDIA_TYPES:
        assert media_type in page
