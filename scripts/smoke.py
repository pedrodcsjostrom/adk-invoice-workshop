"""Headless end-to-end smoke test for the invoice agent.

Sends a PDF to the agent as an inline part, the same shape the ADK developer UI
produces from a file upload, and prints every tool call plus the final JSON.

    uv run python scripts/smoke.py [path/to/invoice.pdf]

Environment comes from invoice_agent/.env, so the run matches `adk web`.
"""

import asyncio
import json
import os
import sys
import time

from dotenv import load_dotenv
from google.genai import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_PDF = os.path.join(ROOT, "samples", "sample_invoice.pdf")
sys.path.insert(0, ROOT)

load_dotenv(os.path.join(ROOT, "invoice_agent", ".env"))

from google.adk.runners import InMemoryRunner  # noqa: E402  (after load_dotenv)

from invoice_agent.agent import root_agent  # noqa: E402


async def run(pdf_path: str) -> int:
    pdf_bytes = open(pdf_path, "rb").read()
    print(f"model            {root_agent.model}")
    print(f"project          {os.environ.get('GOOGLE_CLOUD_PROJECT')}")
    print(f"location         {os.environ.get('GOOGLE_CLOUD_LOCATION')}")
    print(f"use_enterprise   {os.environ.get('GOOGLE_GENAI_USE_ENTERPRISE')}")
    print(f"pdf              {pdf_path} ({len(pdf_bytes):,} bytes)")
    print()

    runner = InMemoryRunner(agent=root_agent, app_name="invoice_analysis")
    session = await runner.session_service.create_session(
        app_name="invoice_analysis", user_id="smoke"
    )

    message = types.Content(
        role="user",
        parts=[
            types.Part(text="Extract the invoice record from this document."),
            types.Part(inline_data=types.Blob(mime_type="application/pdf", data=pdf_bytes)),
        ],
    )

    tool_calls: list[str] = []
    final_text: str | None = None
    started = time.monotonic()

    async for event in runner.run_async(
        user_id="smoke", session_id=session.id, new_message=message
    ):
        for part in (event.content.parts if event.content else []) or []:
            if part.function_call:
                tool_calls.append(part.function_call.name)
                print(f"[tool call]     {part.function_call.name}({dict(part.function_call.args)})")
            if part.function_response:
                print(f"[tool result]   {part.function_response.response}")
            if part.text and event.is_final_response():
                final_text = part.text

    elapsed = time.monotonic() - started
    print(f"\nelapsed          {elapsed:.1f}s")

    if final_text is None:
        print("FAIL: no final response")
        return 1

    print("\n--- final response ---")
    print(final_text)

    try:
        record = json.loads(final_text)
    except json.JSONDecodeError as exc:
        print(f"\nFAIL: final response is not JSON: {exc}")
        return 1

    from invoice_agent.agent import InvoiceRecord

    try:
        parsed = InvoiceRecord.model_validate(record)
    except Exception as exc:
        print(f"\nFAIL: JSON does not conform to InvoiceRecord: {exc}")
        return 1

    print("\n--- checks ---")
    print(f"tool called            {'PASS ' + tool_calls[0] if tool_calls else 'FAIL none'}")
    print(f"schema conforms        PASS ({len(parsed.line_items)} line items)")
    print(f"vendor_id resolved     {parsed.vendor_id or 'None'}")
    return 0 if tool_calls else 1


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PDF
    sys.exit(asyncio.run(run(path)))
