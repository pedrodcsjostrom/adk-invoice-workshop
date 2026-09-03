"""Run the agent over one invoice repeatedly and report what it did each time.

Tuning the failure-then-retry moment needs the tool-call sequence, not just the
final answer: a run that reaches the right total on the first read is a
different event on stage from one that fails, looks again, and recovers.

    uv run python scripts/trials.py 05-vertex-missable-line.pdf --runs 10

Judged against samples/invoices/expected.json. Each run gets its own records
file so repeated trials do not pile up in the real one.
"""

import argparse
import asyncio
import json
import mimetypes
import os
import sys
import tempfile
import time

from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
INVOICES = os.path.join(ROOT, "samples", "invoices")
sys.path.insert(0, ROOT)

load_dotenv(os.path.join(ROOT, "invoice_agent", ".env"))
os.environ["INVOICE_RECORDS_PATH"] = os.path.join(
    tempfile.mkdtemp(prefix="invoice-trials-"), "records.jsonl"
)

from google.adk.runners import InMemoryRunner  # noqa: E402
from google.genai import types  # noqa: E402

from invoice_agent import registry  # noqa: E402
from invoice_agent.agent import root_agent  # noqa: E402
from invoice_agent.models import InvoiceRecord  # noqa: E402


def expected_for(filename: str) -> dict:
    with open(os.path.join(INVOICES, "expected.json"), encoding="utf-8") as handle:
        for entry in json.load(handle):
            if entry["file"] == filename:
                return entry
    raise SystemExit(f"no expected.json entry for {filename}")


async def one_run(path: str) -> dict:
    """One invocation. Returns the tool trace and the parsed record."""
    data = open(path, "rb").read()
    mime = mimetypes.guess_type(path)[0] or "application/pdf"

    runner = InMemoryRunner(agent=root_agent, app_name="invoice_trials")
    session = await runner.session_service.create_session(
        app_name="invoice_trials", user_id="trials"
    )
    message = types.Content(
        role="user",
        parts=[
            types.Part(text="Process this invoice."),
            types.Part(inline_data=types.Blob(mime_type=mime, data=data)),
        ],
    )

    calls: list[str] = []
    checks: list[dict] = []
    final_text = None
    started = time.monotonic()

    async for event in runner.run_async(
        user_id="trials", session_id=session.id, new_message=message
    ):
        for part in (event.content.parts if event.content else []) or []:
            if part.function_call:
                calls.append(part.function_call.name)
                if part.function_call.name == "check_invoice_arithmetic":
                    args = dict(part.function_call.args)
                    checks.append(
                        {
                            "lines": len(args.get("line_items") or []),
                            "total": args.get("total"),
                        }
                    )
            if part.function_response:
                response = part.function_response.response
                if part.function_response.name == "check_invoice_arithmetic":
                    checks[-1]["ok"] = response.get("ok")
                if part.function_response.name == "save_invoice_record":
                    checks.append({"saved_passed": response.get("validation_passed")})
            if part.text and event.is_final_response():
                final_text = part.text

    result = {
        "calls": calls,
        "checks": checks,
        "elapsed": time.monotonic() - started,
        "record": None,
        "error": None,
    }
    if final_text is None:
        result["error"] = "no final response"
        return result
    try:
        result["record"] = InvoiceRecord.model_validate_json(final_text)
    except Exception as exc:  # noqa: BLE001 — any parse failure is a failed run
        result["error"] = f"final response not a valid record: {exc}"
    return result


def judge(run: dict, expected: dict) -> tuple[bool, list[str]]:
    """Did this run end where the answer key says it should?"""
    problems = []
    if run["error"]:
        return False, [run["error"]]

    record = run["record"]
    line_sum = round(sum(round(item.amount, 2) for item in record.line_items), 2)
    if record.invoice_number != expected["invoice_number"]:
        problems.append(f"invoice_number {record.invoice_number!r}")
    if record.currency != expected["currency"]:
        problems.append(f"currency {record.currency!r}")
    if len(record.line_items) != expected["line_count"]:
        problems.append(f"{len(record.line_items)} lines, want {expected['line_count']}")
    if line_sum != expected["line_sum"]:
        problems.append(f"line sum {line_sum}, want {expected['line_sum']}")
    if round(record.total, 2) != expected["stated_total"]:
        problems.append(f"total {record.total}, want {expected['stated_total']}")
    # The supplier should resolve exactly when the registry knows the printed
    # name, so 09-unknown-supplier.pdf is expected to come back with a null id.
    known = registry.find(expected["supplier_printed"])
    want_id = known["supplier_id"] if known else None
    if record.supplier_id != want_id:
        problems.append(f"supplier_id {record.supplier_id!r}, want {want_id!r}")

    saved = [c for c in run["checks"] if "saved_passed" in c]
    if not saved:
        problems.append("never saved")
    elif saved[-1]["saved_passed"] is not expected["validation_passes"]:
        problems.append(f"saved validation_passed={saved[-1]['saved_passed']}")

    return not problems, problems


def describe(run: dict) -> str:
    """The shape of the run: how many checks, and did any of them fail."""
    checks = [c for c in run["checks"] if "ok" in c]
    if not checks:
        return "no check"
    shape = "->".join(f"{c['lines']}L/{c['total']}{'ok' if c['ok'] else 'FAIL'}" for c in checks)
    return shape


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("invoice", help="filename inside samples/invoices/")
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()

    path = os.path.join(INVOICES, args.invoice)
    expected = expected_for(args.invoice)

    print(f"invoice   {args.invoice} — {expected['purpose']}")
    print(f"model     {root_agent.model} @ {os.environ.get('GOOGLE_CLOUD_LOCATION')}")
    print(f"runs      {args.runs}\n")

    passes = 0
    recovered = 0
    for index in range(1, args.runs + 1):
        run = await one_run(path)
        ok, problems = judge(run, expected)
        passes += ok
        checks = [c for c in run["checks"] if "ok" in c]
        if len(checks) > 1 and not checks[0]["ok"] and checks[-1]["ok"]:
            recovered += 1
        verdict = "PASS" if ok else "FAIL " + "; ".join(problems)
        print(
            f"{index:>3}  {run['elapsed']:>5.1f}s  {len(checks)} check(s)  "
            f"{describe(run):<44} {verdict}"
        )

    print(f"\n{passes}/{args.runs} correct, {recovered} showed fail-then-recover")
    return 0 if passes == args.runs else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
