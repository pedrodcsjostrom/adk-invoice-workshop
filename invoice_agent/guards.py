"""Preconditions the agent is not trusted to enforce for itself.

Every turn this agent handles must carry a document. There is no useful
behaviour without one: handed a filename and no bytes, the model writes a
plausible invoice to match the words in the filename, and the trace that
follows has exactly the right shape — an honest arithmetic check over invented
numbers, a schema-conforming record, a save.

No wording in the instruction can stop that. Prompt text is influence; a
`before_model_callback` that returns content is enforcement, because ADK skips
the model call entirely when it does. So this one rule lives in code.

Deliberately narrow: it asks whether a document arrived, never whether the
document is any good.
"""

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

# User-facing, and said out loud during the workshop. It names the fix rather
# than the fault, because the fix is one button away and the fault is subtle.
NO_DOCUMENT_MESSAGE = (
    "No invoice reached me. Attach the document with the attachment button "
    "next to the message box, then send it again. A file path typed or pasted "
    "into the message is only text — I would have to invent the invoice to "
    "answer it."
)


def first_document_part(content: types.Content | None) -> types.Part | None:
    """The first part of a message carrying document bytes, if there is one.

    An upload never arrives as an argument. It rides on the user's message as
    inline bytes, which is why both the guard and the archiver start here.
    """
    for part in getattr(content, "parts", None) or []:
        blob = getattr(part, "inline_data", None)
        if blob is not None and blob.data:
            return part
    return None


def require_attached_document(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> LlmResponse | None:
    """Refuse a turn that carries no document, before the model is called.

    Returns None — carry on and call the model — whenever the turn has bytes on
    it. Otherwise returns the refusal, which ADK takes as the model's answer
    for this step, so the turn costs no tokens and can fabricate nothing.
    """
    if first_document_part(callback_context.user_content) is not None:
        return None

    return LlmResponse(
        content=types.Content(
            role="model", parts=[types.Part(text=NO_DOCUMENT_MESSAGE)]
        )
    )
