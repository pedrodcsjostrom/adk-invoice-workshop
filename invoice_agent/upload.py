"""The upload page, and the analyze endpoint it sends one document at a time to.

The deployed service no longer serves ADK's REST API or its developer UI, so
this module is the whole of what an attendee opens (ADR-0001). The page at `/`
is a file picker and a results table; a multipart POST to `/analyze` carries one
document, whose bytes are driven through the agent with an ADK `Runner` and come
back as JSON. See ADR-0002 for why the page talks to an endpoint of ours rather
than to ADK's own HTTP surface.

Two things this module deliberately does not do. It does not save anything: the
agent's `save_invoice_record` tool files the record, which is why an analysed
invoice appears on the records page, and this endpoint only reports what the
tool said it did. And it does not decide whether the invoice adds up — per
CONTEXT.md the store decides `validation_passed`, so that answer is read back
off the tool's response rather than recomputed here.
"""

import json

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import HTMLResponse
from google.adk.runners import InMemoryRunner
from google.genai import types

from invoice_agent.agent import root_agent

router = APIRouter()

APP_NAME = "invoice-agent"
USER_ID = "attendee"

# The limits, named here and nowhere else. Issue #60 renders the upload page
# from this module and interpolates these three into its browser script, so the
# page and the server cannot drift apart about what is acceptable. That is why
# they are plain JSON-shaped values: a list and two numbers interpolate into
# JavaScript unchanged.
#
# The count cap is only ever enforced in the browser. A batch is picked on the
# page and sent one document per request, so the server never sees one to count
# (ADR-0003). It lives here anyway because it is the same kind of promise.
ALLOWED_MEDIA_TYPES = ["application/pdf", "image/png", "image/jpeg"]
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
MAX_BATCH_DOCUMENTS = 20

# The message the document rides in on. The agent is told what it is looking at
# in prose; the bytes go beside it as an inline data part, which is the shape
# both the document guard and the archiver already look for.
PROMPT = "Analyse this invoice."

# The tool the trace summary counts, and what it says when there is nothing to
# count. Issue #59: the summary exists so the re-read is visible on a deployed
# service, where there is no developer UI trace to open, and the re-read is
# only ever a second call to this one tool.
CHECK_TOOL = "check_invoice_arithmetic"
NO_CHECK_SUMMARY = "the arithmetic check never ran"


# --- the upload page -----------------------------------------------------------
#
# Issue #60. Markup, styles and script are strings in Python, exactly as the
# records page has them: no build step, no package manifest, no static asset
# directory, and so no node toolchain anywhere near the image (ADR-0001). Large
# type and few elements because this is read off a projector from the back of a
# room of sixty.

STYLE = """\
body { font: 20px/1.5 system-ui, sans-serif; margin: 2rem auto; max-width: 76rem;
       color: #111; }
h1 { font-size: 2rem; margin-bottom: 0.25rem; }
p.lede { color: #444; margin-top: 0; }
a { color: #0b5cad; }
.picker { margin: 1.5rem 0 0.5rem; }
input[type=file] { font: inherit; }
button { font: inherit; font-weight: 600; padding: 0.5rem 1.5rem; margin-left: 1rem;
         cursor: pointer; }
button[disabled] { cursor: default; opacity: 0.5; }
p.chosen { color: #444; }
p.notice { color: #b3261e; font-weight: 600; }
table { border-collapse: collapse; width: 100%; margin-top: 1rem; }
th, td { text-align: left; padding: 0.5rem 0.6rem; border-bottom: 1px solid #ccc; }
th { font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.04em; color: #444; }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
.pass { color: #1a7f37; font-weight: 600; }
.fail { color: #b3261e; font-weight: 600; }
tr.failed td { background: #fdecea; color: #b3261e; font-weight: 600; }
"""

# One row per finished document, and the same eight facts the attendee is asked
# to check against the paper in front of them. "Adds up" is the store's answer
# and "Trace" is the one line that makes the re-read visible (issue #59).
COLUMNS = (
    "Document", "Supplier", "Invoice", "Date", "Lines", "Total", "Adds up", "Trace"
)

SCRIPT = """\
const picker = document.getElementById('picker');
const send = document.getElementById('send');
const chosen = document.getElementById('chosen');
const notice = document.getElementById('notice');
const rows = document.getElementById('rows');

// The batch, held in the browser and nowhere else. The page sends one request
// per document, in order, one at a time, and appends a row as each response
// lands; nothing on the server knows a batch exists (ADR-0003). That sequencing
// is also what supplies progress, since driving the agent server-side would
// give up streaming (ADR-0002).
let batch = [];

picker.addEventListener('change', () => {
  batch = Array.from(picker.files);
  notice.textContent = '';
  if (batch.length > MAX_DOCUMENTS) {
    // Refused before a single request goes out, so nobody can start a run that
    // costs more than they meant to spend by selecting a folder.
    notice.textContent = 'That is ' + batch.length + ' documents. Pick at most '
      + MAX_DOCUMENTS + ' at a time.';
    batch = [];
  }
  chosen.textContent = batch.length
    ? batch.length + ' picked: ' + batch.map(file => file.name).join(', ')
    : 'Nothing picked yet.';
  send.disabled = batch.length === 0;
});

send.addEventListener('click', async () => {
  send.disabled = true;
  picker.disabled = true;
  for (const file of batch) {
    const reason = refusal(file);
    if (reason) {
      // Rejected here, with no request sent at all: a document the agent was
      // never going to be able to read should not cost a wait.
      addRow(file.name, null, reason);
      continue;
    }
    try {
      const body = new FormData();
      body.append('file', file);
      const response = await fetch('/analyze', { method: 'POST', body: body });
      const result = await response.json();
      // A refused or failed document comes back 200 with a null record and a
      // sentence, so one bad document is one red row and the batch carries on.
      addRow(file.name, result, result.record ? null : result.message);
    } catch (error) {
      addRow(file.name, null, 'The request never reached the agent: ' + error);
    }
  }
  picker.disabled = false;
  picker.value = '';
  batch = [];
  chosen.textContent = 'Nothing picked yet.';
});

function refusal(file) {
  if (!ALLOWED_MEDIA_TYPES.includes(file.type)) {
    return (file.type || 'That file') + ' is not something the agent can read. '
      + 'Upload a ' + ALLOWED_NAMES + '.';
  }
  if (file.size > MAX_DOCUMENT_BYTES) {
    return 'That document is larger than ' + MAX_MEGABYTES
      + ' MB, so it was not sent.';
  }
  return null;
}

function addRow(name, result, failure) {
  const row = document.createElement('tr');
  cell(row, name);
  if (failure || !result) {
    row.className = 'failed';
    cell(row, failure || 'The agent filed nothing.').colSpan = 7;
  } else {
    const record = result.record;
    cell(row, record.supplier_name || '-');
    cell(row, record.invoice_number || '-');
    cell(row, record.invoice_date || '-');
    cell(row, (record.line_items || []).length, 'num');
    cell(row, money(record), 'num');
    cell(row, result.validation_passed ? 'yes' : 'no',
         result.validation_passed ? 'pass' : 'fail');
    cell(row, result.trace_summary || '');
  }
  rows.appendChild(row);
}

function cell(row, value, className) {
  const td = document.createElement('td');
  // textContent and never innerHTML: everything on a row came back from the
  // model, and the records page escapes it server-side for the same reason.
  td.textContent = value;
  if (className) { td.className = className; }
  row.appendChild(td);
  return td;
}

function money(record) {
  if (record.total === null || record.total === undefined) { return '-'; }
  const amount = Number(record.total).toLocaleString(undefined, {
    minimumFractionDigits: 2, maximumFractionDigits: 2
  });
  return amount + ' ' + (record.currency || '');
}
"""


@router.get("/", response_class=HTMLResponse)
def upload_page() -> str:
    """The page at the root of the service: a file picker and a results table."""
    return render()


def render() -> str:
    """The whole page. Kept in one function so attendees can read it in one go."""
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>Invoice upload</title>"
        f"<style>{STYLE}</style></head><body>"
        "<h1>Invoice upload</h1>"
        f"<p class='lede'>Pick up to {MAX_BATCH_DOCUMENTS} invoice documents "
        f"({_media_type_names()}, {_megabytes()} MB each) and send them to the "
        "agent one at a time. "
        "<a href='/records'>See everything filed so far</a>.</p>"
        "<div class='picker'>"
        f"<input type='file' id='picker' multiple accept='{_accept()}'>"
        "<button id='send' disabled>Analyse</button>"
        "</div>"
        "<p class='chosen' id='chosen'>Nothing picked yet.</p>"
        "<p class='notice' id='notice'></p>"
        "<table><thead><tr>"
        + "".join(f"<th>{column}</th>" for column in COLUMNS)
        + "</tr></thead><tbody id='rows'></tbody></table>"
        f"<script>{_limits()}{SCRIPT}</script>"
        "</body></html>"
    )


def _limits() -> str:
    """The three limits, handed to the browser script from the constants above.

    Interpolated rather than restated so the page and the server cannot disagree
    about what is acceptable: change a constant and both halves move. The names
    are worked out here too, so there is one place that turns a media type into
    something an attendee reads.
    """
    return (
        f"const ALLOWED_MEDIA_TYPES = {json.dumps(ALLOWED_MEDIA_TYPES)};\n"
        f"const ALLOWED_NAMES = {json.dumps(_media_type_names())};\n"
        f"const MAX_DOCUMENT_BYTES = {MAX_DOCUMENT_BYTES};\n"
        f"const MAX_MEGABYTES = {_megabytes()};\n"
        f"const MAX_DOCUMENTS = {MAX_BATCH_DOCUMENTS};\n"
    )


def _accept() -> str:
    """What the file picker offers, so the wrong type is hard to pick at all."""
    return ",".join(ALLOWED_MEDIA_TYPES)


def _media_type_names() -> str:
    """`a PDF, PNG or JPEG`, read off the allowlist rather than written out."""
    names = [media_type.split("/")[-1].upper() for media_type in ALLOWED_MEDIA_TYPES]
    return ", ".join(names[:-1]) + f" or {names[-1]}"


def _megabytes() -> int:
    return MAX_DOCUMENT_BYTES // (1024 * 1024)


@router.post("/analyze")
async def analyze(file: UploadFile | None = File(None)) -> dict:
    """Run the agent over one uploaded document and report what it filed.

    One document per request, even when the upload page is working through a
    batch: the batch is sequenced in the browser and the agent never sees one.
    See ADR-0003.

    Every way this request can end — a refusal, a run that raised, a filed
    record — comes back as 200 carrying the same result shape, never an HTTP
    error status. ADR-0003 says one bad document must fail one row rather than
    the batch, and the page can only honour that if a refused document looks
    like a finished one with a message on it. Give it a 4xx and the browser
    loop has to special-case transport failures to draw its red row, which is
    the one thing issue #58 exists to prevent.
    """
    data = await file.read() if file is not None else b""

    refusal = _refusal(file, data)
    if refusal is not None:
        return _failed(refusal)

    try:
        return await run_one(data, file.content_type, file.filename)
    except Exception as error:
        # Anything the run throws — a missing credential, a model that fell
        # over, a tool that raised — becomes a sentence the attendee can read
        # instead of a stack trace and a 500.
        return _failed(f"The agent could not finish this document: {error}")


def _refusal(file: UploadFile | None, data: bytes) -> str | None:
    """Why this document cannot be run, or None to go ahead.

    Asked before the run, so a document the agent was never going to be able to
    read costs no model call at all. Note that a file carrying no bytes is not
    refused here: that turn belongs to the document guard, which is the rule
    the workshop is about, and it refuses without a model call too.
    """
    if file is None:
        return "No document arrived. Pick an invoice file and send it again."

    if file.content_type not in ALLOWED_MEDIA_TYPES:
        return (
            f"{file.content_type or 'That file'} is not something the agent can "
            f"read. Upload a {_media_type_names()}."
        )

    if len(data) > MAX_DOCUMENT_BYTES:
        return f"That document is larger than {_megabytes()} MB, so it was not sent."

    return None


def _failed(message: str) -> dict:
    """A result the page renders as a red row, shaped like a successful one."""
    return {
        "record": None,
        "validation_passed": None,
        "source_uri": None,
        # A refused document never reached the agent, so there is nothing to
        # count and the sentence says so rather than going missing. Issue #59
        # asks for a summary on every response, including these.
        "trace_summary": NO_CHECK_SUMMARY,
        "message": message,
    }


async def run_one(data: bytes, mime_type: str | None, filename: str | None) -> dict:
    """Drive one document through the agent and shape the answer for the page."""
    events = await _drive(_message(data, mime_type, filename))
    saved = _save_response(events)
    answer = _final_text(events)
    record = _record(answer)

    return {
        "record": record,
        # Both come from the tool rather than from the model: the store ran the
        # arithmetic and the archiver knows where the original went.
        "validation_passed": saved.get("validation_passed"),
        "source_uri": saved.get("source_uri"),
        "trace_summary": _trace_summary(events),
        # What the agent said when it filed nothing — today that is the
        # document guard's refusal, and it is where #58 puts failure reasons.
        "message": None if record else answer,
    }


def _message(data: bytes, mime_type: str | None, filename: str | None) -> types.Content:
    return types.Content(
        role="user",
        parts=[
            types.Part(text=PROMPT),
            types.Part(
                inline_data=types.Blob(
                    data=data,
                    mime_type=mime_type or "application/octet-stream",
                    display_name=filename,
                )
            ),
        ],
    )


async def _drive(message: types.Content) -> list:
    """One run, in a session of its own, and everything the run emitted.

    A new runner per request means a new in-memory session service per request,
    so there is no history for one invoice to leak into the next one's context.
    See ADR-0003.
    """
    runner = InMemoryRunner(agent=root_agent, app_name=APP_NAME)
    session = await runner.session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID
    )
    return [
        event
        async for event in runner.run_async(
            user_id=USER_ID, session_id=session.id, new_message=message
        )
    ]


def _save_response(events: list) -> dict:
    """What `save_invoice_record` reported, read back off the run's events."""
    for part in _parts_newest_first(events):
        response = part.function_response
        if response is not None and response.name == "save_invoice_record":
            return response.response or {}
    return {}


def _trace_summary(events: list) -> str:
    """How many times the arithmetic check ran, and what it said last.

    This is the deployed half's whole view of the run, and ADR-0001 keeps it
    that way: a sliver of the developer UI's trace, not a second one. So it is
    two facts off the events — a count of calls and the newest result — turned
    into one sentence a room of sixty can read off a projector. On the rigged
    invoice a completed instruction makes that sentence say "twice", which is
    the re-read, on screen, without a trace to open.
    """
    checks = 0
    result = None
    for part in _parts_newest_first(events):
        call = part.function_call
        if call is not None and call.name == CHECK_TOOL:
            checks += 1
        response = part.function_response
        if result is None and response is not None and response.name == CHECK_TOOL:
            # Parts come newest first, so the first one found is the last one
            # the agent saw.
            result = response.response or {}

    if checks == 0:
        # The document guard refuses a turn before any tool runs, and a model
        # that simply never called the tool ends up here too.
        return NO_CHECK_SUMMARY
    return f"{_times(checks)}, {_verdict(result, checks)}"


def _times(checks: int) -> str:
    words = {1: "checked once", 2: "checked twice"}
    return words.get(checks, f"checked {checks} times")


def _verdict(result: dict | None, checks: int) -> str:
    """What the last check said, in words and never in numbers of its own.

    The discrepancy is whatever `validation.check` already worked out: the
    total error carries the signed gap between the printed total and the lines,
    so a negative one is an invoice short of its own lines. When only the lines
    disagree there is no single number to name and the sentence says so.
    """
    if result is None:
        return "no answer came back"
    if result.get("ok"):
        return "adds up"

    # "still" only once there has been a re-read; on a first check there is
    # nothing for it to be still doing.
    still = "still " if checks > 1 else ""
    total_error = result.get("total_error")
    if total_error is None:
        return f"{still}does not add up"
    difference = total_error["difference"]
    # Signed the way `validation.check` computes it: the printed total minus
    # what the lines come to. The rigged invoice prints a total above its own
    # lines, so it reads "over", and an invoice whose total falls short of them
    # reads "short". Grouped like the records page's totals, because this is
    # read off a projector from the back of a room.
    direction = "short" if difference < 0 else "over"
    return f"{still}{direction} by {abs(difference):,.2f}"


def _final_text(events: list) -> str:
    """The agent's answer, which the `output_schema` makes JSON — usually."""
    for part in _parts_newest_first(events):
        if part.text:
            return part.text
    return ""


def _parts_newest_first(events: list):
    """Every part the run emitted, newest first."""
    for event in reversed(events):
        for part in (event.content.parts if event.content else []) or []:
            yield part


def _record(answer: str) -> dict | None:
    """The record the agent filed, or nothing when it did not file one.

    A turn the document guard refused ends in a sentence rather than in a
    record, so the answer is not always the JSON the `output_schema` promises.
    """
    try:
        return json.loads(answer)
    except ValueError:
        return None
