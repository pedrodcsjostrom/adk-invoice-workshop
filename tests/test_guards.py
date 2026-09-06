"""The no-document guard: the one rule that is code rather than prompt text.

A turn with a file path typed into the message box carries no bytes, and the
model will happily invent an invoice to match the words in the path. These
tests pin the two halves of the guard: bytes present means carry on, bytes
absent means refuse without ever reaching the model.
"""

import asyncio
from typing import AsyncGenerator

from google.adk.agents import LlmAgent
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.runners import InMemoryRunner
from google.genai import types

from invoice_agent import tools
from invoice_agent.guards import (
    NO_DOCUMENT_MESSAGE,
    first_document_part,
    require_attached_document,
)


class FakeCallbackContext:
    """Stands in for ADK's CallbackContext, of which only `user_content` is read."""

    def __init__(self, user_content):
        self.user_content = user_content


def _text(body: str) -> types.Part:
    return types.Part(text=body)


def _document(data: bytes = b"%PDF-1.4 fake") -> types.Part:
    return types.Part(
        inline_data=types.Blob(
            data=data, mime_type="application/pdf", display_name="invoice.pdf"
        )
    )


def _turn(*parts: types.Part) -> types.Content:
    return types.Content(role="user", parts=list(parts))


def _refusal_text(response) -> str:
    return response.content.parts[0].text


def test_a_turn_with_an_attachment_is_let_through():
    context = FakeCallbackContext(_turn(_text("here it is"), _document()))

    assert require_attached_document(context, llm_request=None) is None


def test_a_turn_with_only_a_pasted_path_is_refused():
    context = FakeCallbackContext(_turn(_text("samples/invoices/01-northwind-clean.pdf")))

    response = require_attached_document(context, llm_request=None)

    assert response is not None
    assert _refusal_text(response) == NO_DOCUMENT_MESSAGE


def test_the_refusal_names_the_attachment_button():
    context = FakeCallbackContext(_turn(_text("analyse the northwind invoice")))

    assert "attachment button" in _refusal_text(
        require_attached_document(context, llm_request=None)
    )


def test_an_empty_attachment_does_not_count_as_a_document():
    context = FakeCallbackContext(_turn(_document(data=b"")))

    assert require_attached_document(context, llm_request=None) is not None


def test_a_turn_with_no_content_at_all_is_refused():
    assert require_attached_document(FakeCallbackContext(None), llm_request=None) is not None


def test_first_document_part_skips_past_the_text():
    document = _document()

    assert first_document_part(_turn(_text("here it is"), document)) is document


def test_first_document_part_is_none_without_bytes():
    assert first_document_part(_turn(_text("no attachment"))) is None


# --- the guard driven through a real ADK turn ---------------------------------
#
# The tests above call the callback directly. These run it where it actually
# sits, with a model that counts its calls, which is the only way to prove the
# claim the guard is for: an unattached turn costs nothing, because no model
# call happens at all.


class RecordingModel(BaseLlm):
    """A model that answers "reached the model" and remembers that it was asked."""

    model: str = "recording"
    calls: int = 0

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        self.calls += 1
        yield LlmResponse(
            content=types.Content(role="model", parts=[_text("reached the model")])
        )


def _run_one_turn(*parts: types.Part) -> tuple[list[str], RecordingModel]:
    model = RecordingModel()
    agent = LlmAgent(
        name="guarded",
        model=model,
        instruction="unused",
        before_model_callback=require_attached_document,
    )
    runner = InMemoryRunner(agent=agent, app_name="guard-test")

    async def drive() -> list[str]:
        session = await runner.session_service.create_session(
            app_name="guard-test", user_id="u"
        )
        said = []
        async for event in runner.run_async(
            user_id="u", session_id=session.id, new_message=_turn(*parts)
        ):
            for part in (event.content.parts if event.content else []) or []:
                if part.text:
                    said.append(part.text)
        return said

    return asyncio.run(drive()), model


def test_an_unattached_turn_never_reaches_the_model():
    said, model = _run_one_turn(_text("samples/invoices/04-halden-rigged-total.pdf"))

    assert said == [NO_DOCUMENT_MESSAGE]
    assert model.calls == 0


def test_an_attached_turn_runs_exactly_as_before():
    said, model = _run_one_turn(_text("please file this"), _document())

    assert said == ["reached the model"]
    assert model.calls == 1


# --- the archiver reads the same part -----------------------------------------
#
# `_archive_uploaded_document` and the guard ask the same question of the same
# message, so they share `first_document_part`. These pin the archiver against
# that shared finder, since the persistence path has no other test that a real
# upload reaches the bucket and a pasted path does not.


def test_the_archiver_hands_the_attached_bytes_to_the_store(monkeypatch):
    seen = {}

    def fake_archive_source(data, mime_type, display_name):
        seen.update(data=data, mime_type=mime_type, display_name=display_name)
        return "gs://bucket/invoice.pdf"

    monkeypatch.setattr(tools.store, "archive_source", fake_archive_source)
    context = FakeCallbackContext(_turn(_text("here it is"), _document()))

    assert tools._archive_uploaded_document(context) == "gs://bucket/invoice.pdf"
    assert seen == {
        "data": b"%PDF-1.4 fake",
        "mime_type": "application/pdf",
        "display_name": "invoice.pdf",
    }


def test_the_archiver_returns_nothing_when_no_document_was_attached(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("the store was asked to archive a message with no bytes")

    monkeypatch.setattr(tools.store, "archive_source", refuse)
    context = FakeCallbackContext(_turn(_text("a pasted path")))

    assert tools._archive_uploaded_document(context) is None


def test_a_failed_archive_never_fails_the_save(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("bucket missing")

    monkeypatch.setattr(tools.store, "archive_source", fail)
    context = FakeCallbackContext(_turn(_document()))

    assert tools._archive_uploaded_document(context) is None
